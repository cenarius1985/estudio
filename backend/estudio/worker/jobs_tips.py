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
        # Semilla: si el tema trae una CONSULTA de siembra (campo prioridades
        # usado como consulta semántica por el ciclo dirigido), se buscan los
        # chunks más pertinentes a esa consulta. Si no, cobertura por tema.
        consulta = (tema.prioridades or "").strip()
        if consulta and not any(c in consulta for c in ("/", ",")) and len(consulta) > 40:
            frs_semilla = await recuperar(db, consulta, k=8, tema_id=tema.id)
            if not frs_semilla:
                return {"estado": "error", "motivo": "sin chunks para la consulta"}
            seed_row = (await db.execute(
                select(Chunk).where(Chunk.id == frs_semilla[0].id)
            )).scalar_one()
            fragmentos = frs_semilla
        else:
            semillas = await chunk_menos_cubierto(db, n=1, tema_id=tema.id, prioridades=tema.prioridades)
            if not semillas:
                return {"estado": "error", "motivo": "el tema no tiene chunks indexados"}
            seed_row = (await db.execute(select(Chunk).where(Chunk.id == semillas[0]))).scalar_one()
            fragmentos = await recuperar(db, seed_row.texto[:800], k=6, tema_id=tema.id)
        if fragmentos:
            semilla = next((f for f in fragmentos if f.id == seed_row.id), None)
        else:
            semilla = None

        generado = await _generar_contenido(seed_row, fragmentos, cfg_llm, tema.enfoque)
        if generado is None:
            log.info("[%s] semilla sin material técnico; otra semilla", tema.nombre)
            continue
        titulo, cuerpo, usados = generado
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
            # Los reintentos se agotaron sin duplicado real (p. ej. todas las
            # semillas fueron rechazadas por falta de material técnico): no es
            # un error del sistema, simplemente no hay tip nuevo hoy.
            return {"estado": "omitido",
                    "motivo": "sin semillas con material técnico nuevo"}
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


def _titulo_fallback(texto: str) -> str:
    """Primera línea legible del chunk: salta cabeceras de código, tablas y
    opciones LaTeX/TikZ para no titular un tip con '[ enhanced, colback=…'."""
    for linea in texto.splitlines():
        l = linea.strip()
        if len(l) > 40 and not l.startswith(("#", "[", "|", "%", "\\", "-", "=", "ink", "muted")):
            return " ".join(l.split()[:9]).strip(" ,.;:")
    return "Repaso de estudio"


async def _generar_contenido(
    seed: Chunk, fragmentos: list[Fragmento], cfg_llm: dict, enfoque: str = ""
) -> tuple[str, str, list[Fragmento]] | None:
    """LLM con citas y el nivel/enfoque del tema.

    Devuelve None si los fragmentos no traen material técnico real
    (`sin_material: true`) — el llamador prueba otra semilla. Solo hay
    fallback extractivo cuando el LLM no responde JSON válido.
    """
    from estudio.rag.prompts import perfil_enfoque

    contexto = construir_contexto(fragmentos) if fragmentos else seed.texto[:1800]
    raw = await chat(
        [{"role": "user", "content": PROMPT_TIP.format(
            enfoque=perfil_enfoque(enfoque), contexto=contexto)}],
        temperature=0.6, max_tokens=600, json_mode=True, cfg=cfg_llm,
    )
    datos = extraer_json(raw)
    if datos is not None and datos.get("sin_material"):
        log.info("semilla sin material técnico; se descarta (otra semilla)")
        return None
    titulo = str(datos.get("titulo") or "").strip() if datos else ""
    cuerpo = str(datos.get("cuerpo") or "").strip() if datos else ""
    if datos and titulo and cuerpo and _titulo_valido(titulo) and _cuerpo_valido(cuerpo):
        return titulo, cuerpo, fragmentos
    if datos and titulo and cuerpo:
        # título ilegible (frase cortada, signos, LaTeX) → derivar del cuerpo
        titulo = _titulo_desde_cuerpo(cuerpo)
        if titulo and _cuerpo_valido(cuerpo):
            return titulo, cuerpo, fragmentos
    # Sin JSON válido o contenido inválido: NO hay fallback extractivo. Copiar
    # el chunk crudo producía tips de código, OCR de figuras y tablas de datos
    # (causa de los tips ilegibles). Mejor descartar y probar otra semilla.
    log.info("respuesta sin contenido técnico utilizable; otra semilla")
    return None


def _cuerpo_valido(c: str) -> bool:
    """Descarta cuerpos que son código, OCR de figura o volcado de datos."""
    if len(c) < 120:
        return False
    # debe citar al menos una fuente (el tip se fundamenta en tus documentos)
    if not re.search(r"\[Fuente\s+\d+", c):
        return False
    sucio = (
        "```" in c or c.count("def ") >= 2 or "print(" in c
        or c.count(" = {") >= 1 or "import " in c
        or re.search(r"\b\d{2,}\s+\d{2,}\s+\d{2,}", c)          # filas de números
        or len(re.findall(r"[|\t]", c)) > 6                      # tablas crudas
    )
    if sucio:
        return False
    # proporción de texto en español razonable (tiene palabras funcionales)
    comunes = (" de ", " la ", " el ", " y ", " en ", " que ", " se ", " con ")
    return sum(c.lower().count(p) for p in comunes) >= 3


def _titulo_valido(t: str) -> bool:
    """Título legible: 4-14 palabras, sin LaTeX, sin empezar con signos."""
    limpio = t.strip()
    if not limpio or len(limpio) > 110:
        return False
    if limpio[0] in "-*#|$\\<>()[]{}":
        return False
    if any(c in limpio for c in "\\$^{}_|"):
        return False
    if any(k in limpio for k in ("def ", "print(", "import ", "http", ".py",
                                 "n = ", "r = ", "p = ")):
        return False
    # sin palabras funcionales del español → no es un título en español
    # (captura "A Subject 1 - female, 49", "10 — Gx — Gy — 62")
    texto_min = f" {limpio.lower()} "
    funcionales = (" de ", " la ", " el ", " en ", " y ", " con ", " para ",
                   " del ", " por ", " un ", " una ", " al ", " en ")
    if sum(texto_min.count(p) for p in funcionales) == 0:
        return False
    # exceso de separadores sueltos (OCR de gráficos, ejes, leyendas)
    if len(re.findall(r"[—–]", limpio)) >= 2 or limpio.count(",") >= 3:
        return False
    palabras = limpio.split()
    if not (4 <= len(palabras) <= 14):
        return False
    # termina a medias (conjunción/preposición/artículo o signo) → ilegible.
    # Comparar la PALABRA completa, no el sufijo (evita rechazar "cuadrática").
    ultima = palabras[-1].lower().strip(" ,.;:—-\"'()")
    if ultima in {"de", "del", "en", "y", "o", "con", "para", "por", "a", "al",
                  "el", "la", "los", "las", "un", "una", "que", "su", "sin"}:
        return False
    if limpio.endswith(("—", "-", ",", ":")):
        return False
    return True


def _titulo_desde_cuerpo(cuerpo: str) -> str:
    """Deriva un título legible de la primera oración del cuerpo."""
    oracion = re.split(r"(?<=[.!?])\s+", cuerpo.strip())[0]
    palabras = " ".join(oracion.split()[:8]).strip(" ,.;:—")
    return palabras if _titulo_valido(palabras) else ""


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
