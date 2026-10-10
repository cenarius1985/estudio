"""Tips diarios por TEMA: cron idempotente + generación RAG + dedupe por
similitud dentro del tema + envío por Brevo con log. Reenvíos usan el
contenido almacenado (0 reproceso)."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from sqlalchemy import delete, func, select

from estudio.config import get_settings
from estudio.credenciales import config_llm, config_smtp
from estudio.db import SessionLocal
from estudio.llm import chat, extraer_json
from estudio.mail.brevo import enviar, smtp_configurado
from estudio.mail.plantilla import cuerpo_html_de, cuerpo_texto_de, plantilla_tip
from estudio.models import Chunk, Tema, Tip, TipChunk, TipEnvio
from estudio.rag.embeddings import embedir_passages
from estudio.rag.prompts import PROMPT_TIP, construir_contexto
from estudio.rag.retrieval import Fragmento, chunk_menos_cubierto, recuperar, similitud_maxima
from estudio.worker.comun import hoy_local, obtener_ajustes_tips

log = logging.getLogger("estudio.tips")


FIN_DIA_MIN = 22 * 60  # los N tips del día se reparten entre tips_hora y las 22:00


def _minutos_hora(texto: str) -> int:
    try:
        hh, mm = (int(x) for x in texto.split(":")[:2])
        return hh * 60 + mm
    except ValueError:
        return 7 * 60 + 30


async def chequear_tip_diario(ctx: dict) -> dict:
    """Cron cada 15 min: dispara la generación del siguiente tip cuando toca.
    Con N tips/día, el j-ésimo sale a tips_hora + j·paso (paso reparte la
    ventana hasta las 22:00). Además libera el modelo si está ocioso."""
    from estudio.rag.embeddings import descargar_si_inactivo
    descargar_si_inactivo()

    async with SessionLocal() as db:
        ajustes = await obtener_ajustes_tips(db)
    if not ajustes["habilitado"]:
        return {"estado": "deshabilitado"}

    inicio = _minutos_hora(ajustes["hora"])
    ahora = datetime.now()
    ahora_min = ahora.hour * 60 + ahora.minute
    if ahora_min < inicio:
        return {"estado": "aun_no_hora"}

    por_dia = ajustes["por_dia"]
    paso = (FIN_DIA_MIN - inicio) // (por_dia - 1) if por_dia > 1 else 0

    async with SessionLocal() as db:
        hoy = hoy_local()
        temas_activos = (
            await db.execute(select(Tema.id).where(Tema.tips_activo))  # type: ignore[attr-defined]
        ).fetchall()
        pendientes = 0
        for (tema_id,) in temas_activos:
            enviados = (await db.execute(
                select(func.count()).select_from(Tip).where(
                    Tip.fecha == hoy, Tip.estado == "enviado", Tip.tema_id == tema_id
                )
            )).scalar() or 0
            if enviados >= por_dia:
                continue
            objetivo = inicio + enviados * paso  # hora del siguiente tip
            if ahora_min >= objetivo:
                pendientes += 1
        if not pendientes:
            return {"estado": "al_dia"}

    await ctx["redis"].enqueue_job("generar_tip_diario", {}, _queue_name=get_settings().cola_urgentes)
    return {"estado": "encolado", "temas_pendientes": pendientes}


async def generar_tip_diario(ctx: dict, forzar: bool = False) -> dict:
    """Genera y envía el tip de HOY por cada tema con tips_activo."""
    resumen: dict = {}
    async with SessionLocal() as db:
        ajustes = await obtener_ajustes_tips(db)
        temas = (await db.execute(select(Tema).where(Tema.tips_activo))).scalars().all()  # type: ignore[attr-defined]
        for tema in temas:
            try:
                resumen[tema.nombre] = await _tip_de_tema(db, tema, ajustes, forzar)
            except Exception as exc:  # noqa: BLE001 — un tema no frena a los demás
                log.exception("Tip de %s falló: %s", tema.nombre, exc)
                resumen[tema.nombre] = {"estado": "error", "motivo": str(exc)[:200]}
    return {"temas": resumen}


async def _tip_de_tema(db, tema: Tema, ajustes: dict, forzar: bool) -> dict:
    s = get_settings()
    hoy = hoy_local()

    # Idempotencia por CUOTA: uno (o N) tips ya enviados hoy para este tema
    enviados_hoy = (await db.execute(
        select(func.count()).select_from(Tip).where(
            Tip.fecha == hoy, Tip.estado == "enviado", Tip.tema_id == tema.id
        )
    )).scalar() or 0
    if enviados_hoy >= ajustes["por_dia"] and not forzar:
        return {"estado": "omitido", "motivo": f"ya se enviaron los {ajustes['por_dia']} de hoy",
                "tip_id": None}
    if forzar:
        await db.execute(
            delete(Tip).where(
                Tip.fecha == hoy,
                Tip.estado.in_(["generado", "duplicado"]),
                Tip.tema_id == tema.id,
            )
        )
        await db.commit()

    umbral = ajustes["umbral"]
    reintentos = max(1, ajustes["reintentos"])
    cfg_llm = await config_llm(db)
    tip: Tip | None = None
    dup_id: str | None = None
    dup_sim = 0.0

    for _ in range(reintentos):
        semillas = await chunk_menos_cubierto(db, n=1, tema_id=tema.id, prioridades=tema.prioridades)
        if not semillas:
            return {"estado": "error", "motivo": "el tema no tiene chunks indexados"}
        seed_row = (await db.execute(select(Chunk).where(Chunk.id == semillas[0]))).scalar_one()
        fragmentos = await recuperar(db, seed_row.texto[:800], k=6, tema_id=tema.id)
        if fragmentos:
            semilla = next((f for f in fragmentos if f.id == seed_row.id), None)
        else:
            semilla = None

        titulo, cuerpo, usados = await _generar_contenido(seed_row, fragmentos, cfg_llm, tema.enfoque)
        if semilla:
            usados = usados or [semilla]
        if not usados:
            usados = [
                Fragmento(id=seed_row.id, texto=seed_row.texto, pagina=seed_row.pagina,
                          archivo="", tipo="txt", titulo="")
            ]

        emb = embedir_passages([f"{titulo}\n{cuerpo}"])[0]
        sim, dup_id = await similitud_maxima(db, emb, "tips", tema_id=tema.id)
        if sim >= umbral:
            dup_sim = sim
            log.info("[%s] tip duplicado (sim=%.3f ≥ %.2f); reintento", tema.nombre, sim, umbral)
            continue

        parrafos = [p.strip() for p in re.split(r"\n+", cuerpo) if p.strip()]
        citas = _citas_de(usados)
        tip = Tip(
            fecha=hoy, titulo=titulo, cuerpo_texto=cuerpo_texto_de(parrafos, citas),
            cuerpo_html=cuerpo_html_de(parrafos, citas), embedding=emb, estado="generado",
            tema_id=tema.id,
        )
        db.add(tip)
        await db.flush()
        ids_usados = {f.id for f in usados}
        for cid in ids_usados:
            db.add(TipChunk(tip_id=tip.id, chunk_id=cid, es_semilla=(cid == seed_row.id)))
        await db.commit()
        break

    if tip is None:
        # Todos los intentos duplicaron un tip previo DEL TEMA → reutilizar el
        # almacenado SIN reprocesar (requisito: nada de re-generar).
        original = await db.get(Tip, dup_id) if dup_id else None
        if not original:
            return {"estado": "error", "motivo": "duplicados sin original"}
        log.info("[%s] reutilizando tip del %s (sim=%.3f) sin reprocesar",
                 tema.nombre, original.fecha, dup_sim)
        tip = Tip(
            fecha=hoy, titulo=original.titulo, cuerpo_texto=original.cuerpo_texto,
            cuerpo_html=original.cuerpo_html, embedding=original.embedding,
            estado="duplicado", duplicado_de=original.id, tema_id=tema.id,
        )
        db.add(tip)
        await db.flush()
        vinculados = (
            await db.execute(select(TipChunk.chunk_id, TipChunk.es_semilla)
                             .where(TipChunk.tip_id == original.id))
        ).all()
        for chunk_id, es_semilla in vinculados:
            db.add(TipChunk(tip_id=tip.id, chunk_id=chunk_id, es_semilla=es_semilla))
        await db.commit()

    resultado = await _enviar_tip(db, tip, tema.nombre, ajustes["destinos"], s.frontend_url)
    return {"estado": resultado.get("estado"), "tip_id": tip.id,
            **{k: v for k, v in resultado.items() if k != "estado"}}


async def _generar_contenido(
    seed: Chunk, fragmentos: list[Fragmento], cfg_llm: dict, enfoque: str = ""
) -> tuple[str, str, list[Fragmento]]:
    """LLM con citas y el nivel/enfoque del tema; fallback extractivo sin LLM."""
    from estudio.rag.prompts import perfil_enfoque

    contexto = construir_contexto(fragmentos) if fragmentos else seed.texto[:1800]
    raw = await chat(
        [{"role": "user", "content": PROMPT_TIP.format(
            enfoque=perfil_enfoque(enfoque), contexto=contexto)}],
        temperature=0.6, max_tokens=600, json_mode=True, cfg=cfg_llm,
    )
    datos = extraer_json(raw)
    if datos and datos.get("titulo") and datos.get("cuerpo"):
        return str(datos["titulo"]).strip(), str(datos["cuerpo"]).strip(), fragmentos

    # Fallback: extractivo (garantiza tip aunque el LLM esté apagado)
    oraciones = [o for o in re.split(r"(?<=[.!?])\s+", seed.texto.strip()) if len(o) > 40]
    cuerpo = " ".join(oraciones[:3]) + " [Fuente 1]"
    titulo = " ".join(seed.texto.split()[:8]).strip(" ,.;:")
    return titulo or "Repaso de estudio", cuerpo, []


def _citas_de(fragmentos: list[Fragmento]) -> list[dict]:
    vistos: set[tuple[str, str]] = set()
    citas = []
    for f in fragmentos:
        clave = (f.archivo, f.pagina)
        if clave in vistos:
            continue
        vistos.add(clave)
        citas.append({"archivo": f.archivo, "pagina": f.pagina})
    return citas[:5]


async def _enviar_tip(db, tip: Tip, tema_nombre: str, destinos: list[str], frontend_url: str) -> dict:
    link = f"{frontend_url.rstrip('/')}/tips"
    plant = plantilla_tip(tip.titulo, tip.cuerpo_html, tip.cuerpo_texto, link, tema=tema_nombre)
    cfg_smtp = await config_smtp(db)

    if not destinos:
        return {"estado": "sin_destinatarios", "tip_id": tip.id}
    if not smtp_configurado(cfg_smtp):
        return {"estado": "sin_smtp", "tip_id": tip.id,
                "motivo": "configura el correo Brevo en Ajustes (o SMTP_* en .env)"}

    fallos = 0
    for email in destinos:
        try:
            await enviar(email, plant["asunto"], plant["html"], plant["texto"], cfg_smtp)
            db.add(TipEnvio(tip_id=tip.id, email=email, estado="ok"))
        except Exception as exc:  # noqa: BLE001 — log por destinatario, estilo EnvioLog
            fallos += 1
            db.add(TipEnvio(tip_id=tip.id, email=email, estado="error", error=str(exc)[:1000]))
            log.error("Envío a %s falló: %s", email, exc)
    tip.estado = "enviado" if fallos < len(destinos) else "error"
    tip.enviado_en = datetime.utcnow()
    await db.commit()
    return {"estado": tip.estado, "enviados": len(destinos) - fallos, "fallos": fallos}


async def reenviar_tip(ctx: dict, tip_id: str) -> dict:
    """Reenvía un tip histórico usando EXACTAMENTE el contenido almacenado."""
    s = get_settings()
    async with SessionLocal() as db:
        tip = await db.get(Tip, tip_id)
        if not tip:
            return {"estado": "error", "motivo": "tip no existe"}
        tema = await db.get(Tema, tip.tema_id) if tip.tema_id else None
        ajustes = await obtener_ajustes_tips(db)
        return await _enviar_tip(db, tip, tema.nombre if tema else None, ajustes["destinos"], s.frontend_url)
