"""Tips diarios por TEMA: cron idempotente + generación RAG + dedupe por
similitud dentro del tema + envío por Brevo con log.

Duplicados: si todo lo generable ya existe (sim ≥ umbral), NO se reenvía el
tip original — el usuario no debe recibir el mismo contenido dos veces; se
marca el tema como agotado por hoy (Redis) y el cupo queda en silencio.
`forzar` (siembra/banco de tips) genera SIN enviar correo."""

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
TTL_AGOTADO_S = 24 * 3600  # la marca "tema agotado hoy" vive un día


def _minutos_hora(texto: str) -> int:
    try:
        hh, mm = (int(x) for x in texto.split(":")[:2])
        return hh * 60 + mm
    except ValueError:
        return 7 * 60 + 30


def _clave_agotado(tema_id: str, fecha) -> str:
    return f"tip:agotado:{tema_id}:{fecha.isoformat()}"


async def _tema_agotado(redis, tema_id: str, fecha) -> bool:
    """True si hoy ya se agotó el tema (todo duplica o sin material técnico).
    Evita quemar reintentos de LLM en cada tick de 15 min para el mismo
    resultado. `forzar` ignora la marca."""
    if redis is None:
        return False
    return bool(await redis.get(_clave_agotado(tema_id, fecha)))


async def _marcar_agotado(redis, tema_id: str, fecha) -> None:
    if redis is not None:
        await redis.set(_clave_agotado(tema_id, fecha), "1", ex=TTL_AGOTADO_S)


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
    # Reparto equiespaciado DENTRO de [tips_hora, 22:00): el j-ésimo sale a
    # inicio + j·paso, de modo que el último cupo nunca cae en las 22:00
    # justas (con 2/día y 07:30 ⇒ 07:30 y ~14:45).
    paso = (FIN_DIA_MIN - inicio) // por_dia if por_dia > 1 else 0

    async with SessionLocal() as db:
        hoy = hoy_local()
        temas_activos = (
            await db.execute(select(Tema.id).where(Tema.tips_activo))  # type: ignore[attr-defined]
        ).fetchall()
        pendientes = 0
        for (tema_id,) in temas_activos:
            if await _tema_agotado(ctx["redis"], tema_id, hoy):
                continue
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

    # _job_id por día: si el job aún no corre, arq REEMPLAZA el pendiente en
    # vez de acumular copias (el cron dispara cada 15 min).
    await ctx["redis"].enqueue_job(
        "generar_tip_diario", {}, _queue_name=get_settings().cola_urgentes,
        _job_id=f"tip_diario_{hoy.isoformat()}",
    )
    return {"estado": "encolado", "temas_pendientes": pendientes}


async def generar_tip_diario(ctx: dict, forzar: bool = False, enviar: bool | None = None) -> dict:
    """Genera (y envía, salvo siembra) el tip de HOY por cada tema con tips_activo.

    `forzar=True` es el modo siembra (banco de tips): regenera sin respetar
    cuota y NO envía correo salvo `enviar=True` explícito.
    """
    if enviar is None:
        enviar = not forzar
    redis = ctx.get("redis")
    resumen: dict = {}
    async with SessionLocal() as db:
        ajustes = await obtener_ajustes_tips(db)
        temas = (await db.execute(select(Tema).where(Tema.tips_activo))).scalars().all()  # type: ignore[attr-defined]
        for tema in temas:
            try:
                resumen[tema.nombre] = await _tip_de_tema(
                    db, tema, ajustes, forzar, enviar, redis=redis)
            except Exception as exc:  # noqa: BLE001 — un tema no frena a los demás
                log.exception("Tip de %s falló: %s", tema.nombre, exc)
                resumen[tema.nombre] = {"estado": "error", "motivo": str(exc)[:200]}
    return {"temas": resumen}


async def _tip_de_tema(
    db, tema: Tema, ajustes: dict, forzar: bool, enviar: bool, redis=None
) -> dict:
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
    if not forzar and await _tema_agotado(redis, tema.id, hoy):
        return {"estado": "agotado", "motivo": "tema sin contenido nuevo hoy (dedupe)",
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
    dup_sim = 0.0

    # Semilla: si el tema trae una CONSULTA de siembra (campo prioridades
    # usado como consulta semántica por el ciclo dirigido), se buscan los
    # chunks más pertinentes a esa consulta. Si no, cobertura por tema.
    # Con consulta fija los reintentos son inútiles (misma semilla siempre).
    consulta = (tema.prioridades or "").strip()
    usa_consulta = bool(consulta) and not any(c in consulta for c in ("/", ",")) and len(consulta) > 40
    semillas_cobertura: list[int] = []
    if not usa_consulta:
        # una semilla DISTINTA por reintento: reintentar con la misma semilla
        # tras un duplicado solo reproduce el duplicado
        semillas_cobertura = await chunk_menos_cubierto(
            db, n=reintentos, tema_id=tema.id, prioridades=tema.prioridades)
        if not semillas_cobertura:
            return {"estado": "error", "motivo": "el tema no tiene chunks indexados"}
    intentos = len(semillas_cobertura) if semillas_cobertura else 1

    for intento in range(intentos):
        if usa_consulta:
            frs_semilla = await recuperar(db, consulta, k=8, tema_id=tema.id)
            if not frs_semilla:
                await _marcar_agotado(redis, tema.id, hoy)
                return {"estado": "sin_contenido_nuevo", "motivo": "sin chunks para la consulta"}
            seed_row = (await db.execute(
                select(Chunk).where(Chunk.id == frs_semilla[0].id)
            )).scalar_one()
            fragmentos = frs_semilla
        else:
            seed_row = (await db.execute(
                select(Chunk).where(Chunk.id == semillas_cobertura[intento])
            )).scalar_one()
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
            log.info("[%s] tip duplicado (sim=%.3f ≥ %.2f); reintento con otra semilla",
                     tema.nombre, sim, umbral)
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
        # Todo lo generable del tema ya existe (o ninguna semilla tuvo material
        # técnico). NO se reenvía el tip original: el usuario no debe recibir
        # el mismo contenido dos veces. Se marca el tema agotado por hoy para
        # que el cron deje de intentar cada 15 min.
        await _marcar_agotado(redis, tema.id, hoy)
        if dup_sim > 0:
            return {"estado": "sin_contenido_nuevo",
                    "motivo": f"todo duplica (máx sim={dup_sim:.3f} ≥ {umbral}); tema agotado"}
        return {"estado": "sin_contenido_nuevo",
                "motivo": "sin semillas con material técnico nuevo"}

    if not enviar:
        # Modo siembra (forzar): queda en BD como "generado", sin correo.
        return {"estado": "generado", "tip_id": tip.id}

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
    """Descarta cuerpos que son código, OCR de figura o volcado de datos.

    Los segmentos LaTeX ($…$/$$…$$) se excluyen de los checks de "sucio" y
    de palabras funcionales: \\frac{}, ^{}, "= {" legítimos dentro de una
    ecuación no deben rechazar el tip.
    """
    if len(c) < 120:
        return False
    # debe citar al menos una fuente (el tip se fundamenta en tus documentos)
    if not re.search(r"\[Fuente\s+\d+", c):
        return False
    sin_math = re.sub(r"\$\$.+?\$\$|\$[^$\n]+\$", " ", c, flags=re.DOTALL)
    sucio = (
        "```" in sin_math or sin_math.count("def ") >= 2 or "print(" in sin_math
        or " = {" in sin_math or "import " in sin_math
        or re.search(r"\b\d{2,}\s+\d{2,}\s+\d{2,}", sin_math)   # filas de números
        or len(re.findall(r"[|\t]", sin_math)) > 6               # tablas crudas
    )
    if sucio:
        return False
    # proporción de texto en español razonable (tiene palabras funcionales)
    comunes = (" de ", " la ", " el ", " y ", " en ", " que ", " se ", " con ")
    return sum(sin_math.lower().count(p) for p in comunes) >= 3


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
