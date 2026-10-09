"""Jobs de ingesta: escaneo incremental de fuentes e indexado por documento.

Flujo: escanear_fuentes (hash SHA256 → solo lo nuevo/cambiado) →
ingestar_archivo (extraer → chunkear → embeddings → chunks + grafo).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from estudio.config import get_settings
from estudio.db import SessionLocal
from estudio.ingest.chunker import chunkear
from estudio.ingest.escaner import escanear, sha256_archivo
from estudio.ingest.extractores import extraer
from estudio.llm import chat, extraer_json
from estudio.models import Arista, Chunk, Documento, Nodo
from estudio.rag.embeddings import embedir_passages
from estudio.rag.grafo import entidades_en_texto
from estudio.rag.prompts import PROMPT_GRAFO

log = logging.getLogger("estudio.ingesta")

UPLOAD_DIR = "/data/cargas"  # volumen compartido api↔worker para uploads
MAX_ENTS_POR_CHUNK = 6  # límite de pares por chunk (control de volumen del grafo)


def ruta_absoluta(doc: Documento) -> Path:
    base = Path(get_settings().ruta_fuentes) if doc.fuente == "montada" else Path(UPLOAD_DIR)
    return base / doc.ruta


async def escanear_fuentes(ctx: dict) -> dict:
    s = get_settings()
    archivos = escanear(Path(s.ruta_fuentes), s.exclude_dirs_list, s.max_archivo_bytes)
    nuevos, actualizados, intactos, pendientes = 0, 0, 0, []

    async with SessionLocal() as db:
        for a in archivos:
            res = await db.execute(
                select(Documento).where(Documento.ruta == a["ruta"], Documento.fuente == "montada")
            )
            doc = res.scalar_one_or_none()
            if doc and doc.bytes_n == a["bytes"] and doc.estado in ("listo", "procesando"):
                intactos += 1
                continue
            h = sha256_archivo(Path(a["absoluta"]))
            if doc:
                if doc.hash == h and doc.estado == "listo":
                    doc.bytes_n = a["bytes"]
                    intactos += 1
                    continue
                doc.hash, doc.bytes_n, doc.tipo, doc.estado = h, a["bytes"], a["tipo"], "pendiente"
                actualizados += 1
            else:
                doc = Documento(
                    ruta=a["ruta"], fuente="montada", tipo=a["tipo"],
                    titulo=Path(a["ruta"]).stem, hash=h, bytes_n=a["bytes"], estado="pendiente",
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
        "actualizados": actualizados, "intactos": intactos, "encolados": len(pendientes),
    }
    log.info("Escaneo: %s", resumen)
    return resumen


async def ingestar_archivo(ctx: dict, documento_id: str) -> dict:
    return await _indexar(documento_id)


async def reindexar_documento(ctx: dict, documento_id: str) -> dict:
    """Fuerza reindexado completo aunque el hash no haya cambiado."""
    return await _indexar(documento_id, forzar=True)


async def _indexar(documento_id: str, forzar: bool = False) -> dict:
    async with SessionLocal() as db:
        doc = await db.get(Documento, documento_id)
        if not doc:
            return {"error": f"documento {documento_id} no existe"}
        doc.estado = "procesando"
        await db.commit()
        try:
            bloques = extraer(ruta_absoluta(doc), doc.tipo)
            chunks = chunkear(bloques)
            if not chunks:
                raise ValueError("sin chunks")

            await db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
            textos = [c.texto for c in chunks]
            embs: list[list[float]] = []
            for i in range(0, len(textos), 32):  # lotes de 32
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

            await _grafo_llm(db, doc, textos)  # fail-soft, tras el commit
            log.info("Indexado %s → %d chunks", doc.ruta, len(chunks))
            return {"ok": True, "documento": doc.ruta, "chunks": len(chunks), "forzado": forzar}
        except Exception as exc:  # noqa: BLE001 — el error queda registrado en el documento
            doc.estado = "error"
            doc.error = f"{type(exc).__name__}: {exc}"[:2000]
            await db.commit()
            log.error("Error indexando %s: %s", doc.ruta, exc)
            return {"error": doc.error, "documento": doc.ruta}


async def _grafo_diccionario(db, document_id: str) -> None:
    """Aristas de co-ocurrencia por chunk con el vocabulario MRI."""
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
    """Tripletas opcionales por documento con Bonsai (fail-soft)."""
    muestra = "\n\n".join(textos[:2])[:3000]
    raw = await chat(
        [{"role": "user", "content": PROMPT_GRAFO.format(texto=muestra)}],
        temperature=0.1, max_tokens=600, json_mode=True,
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
