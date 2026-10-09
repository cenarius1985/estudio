"""Documentos: listado, escaneo de fuentes, upload, reindexar, borrar, grafo."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.api.cola import encolar
from estudio.config import get_settings
from estudio.db import SessionLocal, get_db
from estudio.ingest.escaner import sha256_archivo
from estudio.ingest.extractores import EXTENSIONES
from estudio.models import Arista, Chunk, Documento, Nodo

router = APIRouter(prefix="/documentos", tags=["documentos"])

UPLOAD_DIR = Path("/data/cargas")


@router.get("")
async def listar(estado: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Documento).order_by(desc(Documento.creado_en)).limit(1000)
    if estado:
        q = q.where(Documento.estado == estado)
    docs = (await db.execute(q)).scalars().all()
    return [
        {
            "id": d.id, "ruta": d.ruta, "fuente": d.fuente, "tipo": d.tipo, "titulo": d.titulo,
            "estado": d.estado, "error": d.error, "bytes": d.bytes_n, "chunks": d.chunks_n,
            "indexado_en": d.indexado_en.isoformat() if d.indexado_en else None,
        }
        for d in docs
    ]


@router.post("/escanear")
async def escanear():
    job_id = await encolar("escanear_fuentes")
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id, "mensaje": "Escaneo encolado; los nuevos se indexarán en segundo plano"}


@router.post("/upload")
async def upload(archivos: list[UploadFile]):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    creados = []
    for archivo in archivos:
        sufijo = Path(archivo.filename or "archivo.bin").suffix.lower()
        if sufijo not in EXTENSIONES:
            continue
        nombre = f"{uuid.uuid4().hex[:8]}-{Path(archivo.filename).name}"
        destino = UPLOAD_DIR / nombre
        contenido = await archivo.read()
        destino.write_bytes(contenido)
        h = hashlib.sha256(contenido).hexdigest()
        async with SessionLocal() as db:
            doc = Documento(
                ruta=nombre, fuente="upload", tipo=EXTENSIONES[sufijo],
                titulo=Path(archivo.filename).stem, hash=h, bytes_n=len(contenido), estado="pendiente",
            )
            db.add(doc)
            await db.flush()
            await db.commit()
            await encolar("ingestar_archivo", doc.id)
            creados.append({"id": doc.id, "ruta": nombre})
    if not creados:
        raise HTTPException(400, "Ningún archivo con formato soportado (pdf, tex, txt, md, csv, docx, xlsx, png, jpg, tif, ipynb)")
    return {"ok": True, "documentos": creados}


@router.post("/{documento_id}/reindexar")
async def reindexar(documento_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(404, "Documento no existe")
    job_id = await encolar("reindexar_documento", documento_id)
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id}


@router.delete("/{documento_id}")
async def borrar(documento_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(404, "Documento no existe")
    if doc.fuente == "upload":
        try:
            (UPLOAD_DIR / doc.ruta).unlink(missing_ok=True)
        except OSError:
            pass
    await db.execute(delete(Documento).where(Documento.id == documento_id))
    await db.commit()
    return {"ok": True}


@router.get("/{documento_id}/chunks")
async def chunks(documento_id: str, db: AsyncSession = Depends(get_db)):
    filas = (
        await db.execute(
            select(Chunk.id, Chunk.n, Chunk.pagina, Chunk.texto)
            .where(Chunk.document_id == documento_id)
            .order_by(Chunk.n)
        )
    ).fetchall()
    return [{"id": f[0], "n": f[1], "pagina": f[2], "texto": f[3][:400]} for f in filas]


@router.get("/grafo/resumen")
async def grafo(limite: int = 60, db: AsyncSession = Depends(get_db)):
    """Nodos por grado + aristas top (para visualizar el grafo de conceptos)."""
    nodos = (
        await db.execute(
            select(Nodo.id, Nodo.nombre, func.count(Arista.id))
            .outerjoin(Arista, (Arista.nodo_a == Nodo.id) | (Arista.nodo_b == Nodo.id))
            .group_by(Nodo.id).order_by(desc(func.count(Arista.id))).limit(limite)
        )
    ).fetchall()
    ids = {n[0] for n in nodos}
    nombres = {n[0]: n[1] for n in nodos}
    aristas = (await db.execute(select(Arista.nodo_a, Arista.nodo_b, Arista.relacion).limit(400))).fetchall()
    return {
        "nodos": [{"id": n[0], "nombre": n[1], "grado": n[2]} for n in nodos],
        "aristas": [
            {"a": nombres.get(a), "b": nombres.get(b), "rel": r}
            for a, b, r in aristas if a in ids and b in ids
        ][: limite * 2],
    }
