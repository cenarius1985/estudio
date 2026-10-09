"""Documentos: listado, escaneo de fuentes, upload, reindexar, borrar, grafo."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import hashlib

from estudio.api.cola import encolar
from estudio.config import get_settings
from estudio.db import SessionLocal, get_db
from estudio.ingest.escaner import sha256_archivo
from estudio.ingest.extractores import EXTENSIONES
from estudio.models import Arista, Chunk, Documento, Nodo

router = APIRouter(prefix="/documentos", tags=["documentos"])

UPLOAD_DIR = Path("/data/cargas")


@router.get("")
async def listar(
    pagina: int = 1,
    por_pagina: int = 50,
    estado: str | None = None,
    tema_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginado: total + página actual + documentos."""
    por_pagina = max(1, min(200, por_pagina))
    pagina = max(1, pagina)
    q = select(Documento).order_by(desc(Documento.creado_en))
    qc = select(func.count()).select_from(Documento)
    if estado:
        q = q.where(Documento.estado == estado)
        qc = qc.where(Documento.estado == estado)
    if tema_id:
        q = q.where(Documento.tema_id == tema_id)
        qc = qc.where(Documento.tema_id == tema_id)
    total = (await db.execute(qc)).scalar() or 0
    docs = (await db.execute(q.offset((pagina - 1) * por_pagina).limit(por_pagina))).scalars().all()
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "documentos": [
            {
                "id": d.id, "ruta": d.ruta, "fuente": d.fuente, "tipo": d.tipo, "titulo": d.titulo,
                "estado": d.estado, "error": d.error, "bytes": d.bytes_n, "chunks": d.chunks_n,
                "tema_id": d.tema_id,
                "indexado_en": d.indexado_en.isoformat() if d.indexado_en else None,
            }
            for d in docs
        ],
    }


@router.post("/escanear")
async def escanear():
    job_id = await encolar("escanear_fuentes")
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id, "mensaje": "Escaneo encolado; los nuevos se indexarán en segundo plano"}


class UrlBody(BaseModel):
    url: str
    tema_id: str | None = None


@router.post("/url")
async def agregar_url(body: UrlBody, db: AsyncSession = Depends(get_db)):
    """Agrega una página web como fuente: se descarga, se indexa y queda
    citable en el chat/tips con su URL."""
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "La URL debe empezar con http:// o https://")
    from urllib.parse import urlparse

    dominio = urlparse(url).netloc or url[:60]
    h = hashlib.sha256(url.lower().encode()).hexdigest()
    existente = (
        await db.execute(select(Documento).where(Documento.fuente == "url", Documento.ruta == url))
    ).scalar_one_or_none()
    if existente:
        doc = existente
        if body.tema_id:
            doc.tema_id = body.tema_id
    else:
        doc = Documento(ruta=url, fuente="url", tipo="txt", titulo=dominio, hash=h,
                        estado="pendiente", tema_id=body.tema_id or "general")
        db.add(doc)
        await db.flush()
    await db.commit()
    job_id = await encolar("ingestar_url", doc.id, urgente=True)
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "documento": doc.id, "job": job_id,
            "mensaje": "ya registrada; se reindexará" if existente else "URL agregada e indexando"}


class MoverTemaBody(BaseModel):
    tema_id: str | None = None  # None/vacío → sin tema


@router.post("/{documento_id}/tema")
async def mover_tema(documento_id: str, body: MoverTemaBody, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(404, "Documento no existe")
    doc.tema_id = body.tema_id or None
    await db.commit()
    return {"ok": True, "tema_id": doc.tema_id}


@router.post("/upload")
async def upload(archivos: list[UploadFile], tema_id: str = Form(None)):
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
                titulo=Path(archivo.filename).stem, hash=h, bytes_n=len(contenido),
                estado="pendiente", tema_id=tema_id or "general",
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
