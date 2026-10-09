"""Estudio tipo Astra: decks de flashcards y quizzes/simulacros generados por
el LLM desde los documentos, con fallback determinista (cloze) para decks."""

from __future__ import annotations

import logging
import random
import re
from datetime import date

from sqlalchemy import func, select

from estudio.db import SessionLocal
from estudio.llm import chat, extraer_json
from estudio.models import Chunk, Deck, Documento, Flashcard, Pregunta, Quiz
from estudio.rag.grafo import entidades_en_texto
from estudio.rag.prompts import PROMPT_DECK, PROMPT_QUIZ
from estudio.rag.retrieval import Fragmento

log = logging.getLogger("estudio.estudio")


async def _fragmentos_aleatorios(
    db, documento_id: str | None, n: int, tema_id: str | None = None, prioridades: str = ""
) -> list[Fragmento]:
    """Muestrea chunks con texto real: prioriza documentos que NO son imágenes
    (el OCR de figuras da tarjetas pobres) y chunks con contenido suficiente.
    Filtra por tema cuando se indica; con `prioridades` (prefijos de ruta)
    muestrea preferentemente el CORE del tema."""
    base = select(Chunk.id, Chunk.texto, Chunk.pagina, Documento.ruta, Documento.tipo).join(
        Documento, Documento.id == Chunk.document_id
    )

    def _con_calidad(q):
        return q.where(Documento.tipo != "imagen", func.length(Chunk.texto) > 300)

    def _con_priors(q):
        prefs = [p.strip().rstrip("/") for p in (prioridades or "").split(",") if p.strip()]
        if not prefs:
            return q, False
        from sqlalchemy import or_

        return q.where(or_(*[Documento.ruta.startswith(p) for p in prefs])), True

    filas: list = []
    if documento_id:
        filas = (await db.execute(base.where(Chunk.document_id == documento_id))).fetchall()
    else:
        q = base
        if tema_id:
            q = q.where(Documento.tema_id == tema_id)
        q_priorizable = _con_calidad(q)
        q_priors, tiene = _con_priors(q_priorizable)
        if tiene:
            filas = (await db.execute(q_priors)).fetchall()
        if not filas:
            filas = (await db.execute(q_priorizable)).fetchall()
        if not filas:  # solo hay imágenes indexadas → usarlas
            filas = (await db.execute(q)).fetchall()
    if not filas:
        return []
    muestra = random.sample(filas, min(n, len(filas)))
    return [
        Fragmento(id=f[0], texto=f[1], pagina=f[2] or "", archivo=f[3], tipo=f[4] or "txt", titulo=f[3])
        for f in muestra
    ]


async def generar_deck(ctx: dict, deck_id: str, documento_id: str | None = None, n: int = 12) -> dict:
    async with SessionLocal() as db:
        deck = await db.get(Deck, deck_id)
        if not deck:
            return {"error": "deck no existe"}
        try:
            from estudio.models import Tema
            from estudio.rag.prompts import perfil_enfoque

            enfoque, prioridades = "", ""
            if deck.tema_id:
                tema = await db.get(Tema, deck.tema_id)
                enfoque = tema.enfoque if tema else ""
                prioridades = tema.prioridades if tema else ""
            fragmentos = await _fragmentos_aleatorios(
                db, documento_id, max(n * 2, 8), tema_id=deck.tema_id, prioridades=prioridades
            )
            if not fragmentos:
                raise ValueError("no hay chunks indexados en el tema" if deck.tema_id else "no hay chunks indexados")

            tarjetas: list[dict] = []
            from estudio.rag.prompts import construir_contexto

            # contexto compacto: llama-server (BONSAI_CTX 8192) desconecta si el
            # prompt desborda la ventana
            contexto = construir_contexto(fragmentos[:6], max_frag=900)
            from estudio.credenciales import config_llm
            raw = await chat(
                [{"role": "user", "content": PROMPT_DECK.format(
                    n=n, enfoque=perfil_enfoque(enfoque), contexto=contexto)}],
                temperature=0.4, max_tokens=1600, json_mode=True,
                cfg=await config_llm(db),
            )
            datos = extraer_json(raw)
            if datos and isinstance(datos.get("tarjetas"), list) and datos["tarjetas"]:
                deck.titulo = str(datos.get("titulo") or deck.titulo)
                for t in datos["tarjetas"][:n]:
                    frente, reverso = str(t.get("frente", "")).strip(), str(t.get("reverso", "")).strip()
                    if not frente or not reverso:
                        continue
                    idx = int(t.get("fuente", 1) or 1) - 1
                    frag = fragmentos[idx] if 0 <= idx < len(fragmentos) else fragmentos[0]
                    tarjetas.append(
                        {"frente": frente, "reverso": reverso,
                         "cita": {"archivo": frag.archivo, "pagina": frag.pagina}}
                    )

            if not tarjetas:  # fallback determinista: cloze sobre entidades del grafo
                deck.titulo = "Repaso cloze de la tesis"
                for frag in fragmentos:
                    if len(tarjetas) >= n:
                        break
                    oraciones = [o for o in re.split(r"(?<=[.!?])\s+", frag.texto) if len(o) > 60]
                    ents = entidades_en_texto(frag.texto)
                    if not oraciones or not ents:
                        continue
                    ent = ents[0]
                    oracion = oraciones[0]
                    if ent.lower() not in oracion.lower():
                        oracion = next(
                            (o for o in oraciones if ent.lower() in o.lower()), oracion
                        )
                    frente = re.sub(re.escape(ent), "______", oracion, count=1, flags=re.IGNORECASE)
                    tarjetas.append(
                        {"frente": frente, "reverso": ent,
                         "cita": {"archivo": frag.archivo, "pagina": frag.pagina}}
                    )

            if not tarjetas:
                raise ValueError("sin material para tarjetas")

            hoy = date.today()
            for t in tarjetas:
                db.add(Flashcard(deck_id=deck.id, frente=t["frente"], reverso=t["reverso"],
                                 cita=t["cita"], proxima_repaso=hoy))
            deck.estado = "listo"
            await db.commit()
            return {"ok": True, "deck_id": deck.id, "tarjetas": len(tarjetas)}
        except Exception as exc:  # noqa: BLE001
            deck.estado = "error"
            deck.error = str(exc)[:1000]
            await db.commit()
            log.error("Deck %s falló: %s", deck_id, exc)
            return {"error": deck.error}


async def generar_quiz(ctx: dict, quiz_id: str, n: int = 10, tipo: str = "quiz") -> dict:
    async with SessionLocal() as db:
        quiz = await db.get(Quiz, quiz_id)
        if not quiz:
            return {"error": "quiz no existe"}
        try:
            from estudio.models import Tema
            from estudio.rag.prompts import construir_contexto, perfil_enfoque

            enfoque, prioridades = "", ""
            if quiz.tema_id:
                tema = await db.get(Tema, quiz.tema_id)
                enfoque = tema.enfoque if tema else ""
                prioridades = tema.prioridades if tema else ""
            fragmentos = await _fragmentos_aleatorios(
                db, None, max(n + 4, 8), tema_id=quiz.tema_id, prioridades=prioridades
            )
            if not fragmentos:
                raise ValueError("no hay chunks indexados en el tema" if quiz.tema_id else "no hay chunks indexados")

            contexto = construir_contexto(fragmentos[:8], max_frag=900)
            from estudio.credenciales import config_llm
            raw = await chat(
                [{"role": "user", "content": PROMPT_QUIZ.format(
                    n=n, enfoque=perfil_enfoque(enfoque), contexto=contexto)}],
                temperature=0.5, max_tokens=3000, json_mode=True,
                cfg=await config_llm(db),
            )
            datos = extraer_json(raw)
            if not (datos and isinstance(datos.get("preguntas"), list) and datos["preguntas"]):
                raise ValueError("se requiere LLM disponible para generar preguntas")

            quiz.titulo = str(datos.get("titulo") or quiz.titulo)
            for i, p in enumerate(datos["preguntas"][:n], start=1):
                alts = [str(a) for a in (p.get("alternativas") or [])][:4]
                if len(alts) < 2:
                    continue
                idx = int(p.get("fuente", 1) or 1) - 1
                frag = fragmentos[idx] if 0 <= idx < len(fragmentos) else fragmentos[0]
                db.add(Pregunta(
                    quiz_id=quiz.id, n=i, enunciado=str(p.get("enunciado", "")).strip(),
                    alternativas=alts, correcta=max(0, min(len(alts) - 1, int(p.get("correcta", 0) or 0))),
                    explicacion=str(p.get("explicacion", "")).strip(),
                    cita={"archivo": frag.archivo, "pagina": frag.pagina},
                ))
            quiz.estado = "listo"
            await db.commit()
            return {"ok": True, "quiz_id": quiz.id}
        except Exception as exc:  # noqa: BLE001
            quiz.estado = "error"
            quiz.error = str(exc)[:1000]
            await db.commit()
            log.error("Quiz %s falló: %s", quiz_id, exc)
            return {"error": quiz.error}
