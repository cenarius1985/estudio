"""Jobs de ingesta: escaneo incremental de la carpeta configurada, indexado
por documento (archivo o URL) y grafo de conceptos.

Flujo: escanear_fuentes (hash SHA256 → solo lo nuevo/cambiado) →
ingestar_archivo / ingestar_url (extraer → chunkear → embeddings → chunks + grafo).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from estudio.config import get_settings
from estudio.credenciales import config_llm, ruta_fuentes_efectiva
from estudio.db import SessionLocal
from estudio.ingest.chunker import chunkear
from estudio.ingest.escaner import escanear, sha256_archivo
from estudio.ingest.extractores import Bloque, extraer
from estudio.llm import chat, extraer_json
from estudio.models import Arista, Chunk, Documento, Nodo, Tema
from estudio.rag.embeddings import embedir_passages
from estudio.rag.grafo import entidades_en_texto
from estudio.rag.prompts import PROMPT_GRAFO

log = logging.getLogger("estudio.ingesta")

UPLOAD_DIR = Path("/data/cargas")
MAX_ENTS_POR_CHUNK = 6  # límite de pares por chunk (control de volumen del grafo)


async def ruta_absoluta(db, doc: Documento) -> Path:
    if doc.fuente == "montada":
        base = Path(await ruta_fuentes_efectiva(db))
        return base / doc.ruta
    if doc.fuente == "upload":
        return UPLOAD_DIR / doc.ruta
    raise ValueError(f"El documento {doc.fuente}:{doc.ruta} no es un archivo local")


async def _temas_carpetas(db) -> list[tuple[str, list[str]]]:
    """[(tema_id, [prefijos])] de los temas que declaran carpetas."""
    filas = (await db.execute(select(Tema.id, Tema.carpetas).where(Tema.carpetas != ""))).fetchall()
    return [
        (tid, [c.strip().rstrip("/") for c in (carp or "").split(",") if c.strip()])
        for tid, carp in filas
    ]


def _tema_de_ruta(ruta: str, temas_carpetas: list[tuple[str, list[str]]]) -> str:
    """Auto-clasificación: primer prefijo que calza; si no, tema General."""
    for tid, prefijos in temas_carpetas:
        for pref in prefijos:
            if ruta.startswith(pref):
                return tid
    return "general"


async def escanear_fuentes(ctx: dict) -> dict:
    s = get_settings()
    async with SessionLocal() as db:
        raiz = Path(await ruta_fuentes_efectiva(db))
    if not raiz.is_dir():
        return {"error": f"La carpeta de fuentes no existe en el contenedor: {raiz} "
                "(configúrala en Ajustes → Fuentes y móntala en Docker si aplica)"}

    archivos = escanear(raiz, s.exclude_dirs_list, s.max_archivo_bytes)
    nuevos, actualizados, intactos, reclasificados, pendientes = 0, 0, 0, 0, []

    async with SessionLocal() as db:
        temas_carpetas = await _temas_carpetas(db)
        for a in archivos:
            tema_id = _tema_de_ruta(a["ruta"], temas_carpetas)
            res = await db.execute(
                select(Documento).where(Documento.ruta == a["ruta"], Documento.fuente == "montada")
            )
            doc = res.scalar_one_or_none()
            if doc:
                if doc.tema_id != tema_id:
                    doc.tema_id = tema_id
                    reclasificados += 1
                # sin_texto también es un estado estable (imagen sin OCR): no re-procesar
                if doc.bytes_n == a["bytes"] and doc.estado in ("listo", "procesando", "sin_texto"):
                    intactos += 1
                    continue
                h = sha256_archivo(Path(a["absoluta"]))
                if doc.hash == h and doc.estado == "listo":
                    doc.bytes_n = a["bytes"]
                    intactos += 1
                    continue
                doc.hash, doc.bytes_n, doc.tipo, doc.estado = h, a["bytes"], a["tipo"], "pendiente"
                actualizados += 1
            else:
                h = sha256_archivo(Path(a["absoluta"]))
                doc = Documento(
                    ruta=a["ruta"], fuente="montada", tipo=a["tipo"],
                    titulo=Path(a["ruta"]).stem, hash=h, bytes_n=a["bytes"],
                    estado="pendiente", tema_id=tema_id,
                )
                db.add(doc)
                await db.flush()
                nuevos += 1
            pendientes.append(doc.id)
        await db.commit()

    for did in pendientes:
        await ctx["redis"].enqueue_job("ingestar_archivo", did)
    resumen = {
        "encontrados": len(archivos), "nuevos": nuevos,
        "actualizados": actualizados, "intactos": intactos,
        "reclasificados": reclasificados, "encolados": len(pendientes),
    }
    log.info("Escaneo %s: %s", raiz, resumen)
    return resumen


async def ingestar_archivo(ctx: dict, documento_id: str) -> dict:
    return await _indexar(documento_id)


async def reindexar_documento(ctx: dict, documento_id: str) -> dict:
    """Fuerza reindexado completo aunque el hash no haya cambiado."""
    return await _indexar(documento_id, forzar=True)


async def ingestar_url(ctx: dict, documento_id: str) -> dict:
    """Descarga e indexa una URL registrada como documento (fuente='url')."""
    from estudio.ingest.web import descargar_pagina

    async with SessionLocal() as db:
        doc = await db.get(Documento, documento_id)
        if not doc:
            return {"error": f"documento {documento_id} no existe"}
        if doc.estado == "listo" and doc.chunks_n > 0:
            return {"ok": True, "documento": doc.ruta, "omitido": "ya listo"}
        doc.estado = "procesando"
        await db.commit()
        try:
            pagina = await descargar_pagina(doc.ruta)
            doc.titulo = pagina.titulo
            resultado = await _procesar_bloques(db, doc, pagina.bloques)
            log.info("Indexada URL %s → %d chunks", pagina.url_final, resultado.get("chunks", 0))
            return {"ok": True, "url": pagina.url_final, **resultado}
        except Exception as exc:  # noqa: BLE001
            try:
                await db.rollback()
            except Exception:  # noqa: BLE001
                pass
            doc.estado = "error"
            doc.error = f"{type(exc).__name__}: {exc}"[:2000]
            await db.commit()
            log.error("Error indexando URL %s: %s", doc.ruta, exc)
            return {"error": doc.error, "url": doc.ruta}


async def _indexar(documento_id: str, forzar: bool = False) -> dict:
    async with SessionLocal() as db:
        doc = await db.get(Documento, documento_id)
        if not doc:
            return {"error": f"documento {documento_id} no existe"}
        if doc.estado == "listo" and not forzar:
            return {"ok": True, "documento": doc.ruta, "omitido": "ya listo"}
        if doc.fuente == "url":
            return {"error": "los documentos tipo url se indexan con ingestar_url"}
        doc.estado = "procesando"
        await db.commit()
        try:
            bloques = extraer(await ruta_absoluta(db, doc), doc.tipo)
            resultado = await _procesar_bloques(db, doc, bloques)
            log.info("Indexado %s → %d chunks", doc.ruta, resultado.get("chunks", 0))
            return {"ok": True, "documento": doc.ruta, **resultado}
        except Exception as exc:  # noqa: BLE001 — el error queda en el documento
            # Si la sesión quedó en rollback pendiente (p. ej. byte inválido al
            # insertar), liberarla ANTES de tocar la BD o el job re-explota y
            # arq lo reintenta 5 veces re-procesando todo.
            try:
                await db.rollback()
            except Exception:  # noqa: BLE001
                pass
            # Imágenes sin texto (figuras científicas, logos): no es un fallo,
            # se marcan «sin_texto» para no ensuciar la lista de errores.
            if doc.tipo == "imagen" and "sin texto" in str(exc).lower():
                doc.estado = "sin_texto"
                doc.error = ""
                doc.chunks_n = 0
                await db.commit()
                return {"ok": True, "documento": doc.ruta, "sin_texto": True}
            doc.estado = "error"
            doc.error = f"{type(exc).__name__}: {exc}"[:2000]
            await db.commit()
            log.error("Error indexando %s: %s", doc.ruta, exc)
            return {"error": doc.error, "documento": doc.ruta}


async def _procesar_bloques(db, doc: Documento, bloques: list[Bloque]) -> dict:
    """Chunks → embeddings → inserción + grafo diccionario → commit."""
    chunks = chunkear(bloques)
    if not chunks:
        raise ValueError("sin chunks")

    await db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    textos = [c.texto for c in chunks]
    embs: list[list[float]] = []
    for i in range(0, len(textos), 32):
        embs.extend(embedir_passages(textos[i : i + 32]))
    for n, (c, e) in enumerate(zip(chunks, embs)):
        db.add(Chunk(document_id=doc.id, n=n, pagina=c.pagina, texto=c.texto, embedding=e))
    await db.flush()

    await _grafo_diccionario(db, doc.id)
    doc.chunks_n = len(chunks)
    doc.estado = "listo"
    doc.error = ""
    doc.indexado_en = datetime.utcnow()
    await db.commit()

    if get_settings().grafo_llm:
        await _grafo_llm(db, doc, textos)
    return {"chunks": len(chunks)}


async def _grafo_diccionario(db, document_id: str) -> None:
    """Aristas de co-ocurrencia por chunk con el vocabulario del dominio."""
    res = await db.execute(
        select(Chunk.id, Chunk.texto).where(Chunk.document_id == document_id)
    )
    filas = res.fetchall()
    nombres: set[str] = set()
    por_chunk: list[tuple[int, list[str]]] = []
    for cid, texto in filas:
        ents = entidades_en_texto(texto)[:MAX_ENTS_POR_CHUNK]
        por_chunk.append((cid, ents))
        nombres.update(ents)
    if not nombres:
        return

    existentes = {r[0]: r[1] for r in (await db.execute(select(Nodo.nombre, Nodo.id))).fetchall()}
    for nomb in sorted(nombres):
        if nomb not in existentes:
            nodo = Nodo(nombre=nomb)
            db.add(nodo)
            await db.flush()
            existentes[nomb] = nodo.id

    for cid, ents in por_chunk:
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                db.add(Arista(nodo_a=existentes[ents[i]], nodo_b=existentes[ents[j]], chunk_id=cid))


async def _grafo_llm(db, doc: Documento, textos: list[str]) -> None:
    """Tripletas opcionales por documento con el LLM (fail-soft, default OFF)."""
    muestra = "\n\n".join(textos[:2])[:3000]
    cfg = await config_llm(db)
    raw = await chat(
        [{"role": "user", "content": PROMPT_GRAFO.format(texto=muestra)}],
        temperature=0.1, max_tokens=600, json_mode=True, cfg=cfg,
    )
    datos = extraer_json(raw)
    if not datos or not isinstance(datos.get("tripletas"), list):
        return
    existentes = {r[0]: r[1] for r in (await db.execute(select(Nodo.nombre, Nodo.id))).fetchall()}
    for t in datos["tripletas"][:8]:
        a, rel, b = (str(t.get(k, "")).strip() for k in ("a", "rel", "b"))
        if not a or not b or len(a) > 100 or len(b) > 100:
            continue
        for nomb in (a, b):
            if nomb not in existentes:
                nodo = Nodo(nombre=nomb, tipo="extraido")
                db.add(nodo)
                await db.flush()
                existentes[nomb] = nodo.id
        db.add(Arista(nodo_a=existentes[a], nodo_b=existentes[b], relacion=rel[:90] or "relacionado con"))
    await db.commit()


def hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()
