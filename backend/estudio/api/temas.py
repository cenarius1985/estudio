"""Temas de estudio: CRUD + reclasificación + stats por tema."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.api.cola import encolar
from estudio.db import get_db
from estudio.models import Chunk, Conversacion, Deck, Documento, Quiz, Tema, Tip

router = APIRouter(prefix="/temas", tags=["temas"])


@router.get("")
async def listar(db: AsyncSession = Depends(get_db)):
    temas = (await db.execute(select(Tema).order_by(Tema.creado_en))).scalars().all()
    salida = []
    for t in temas:
        docs = (await db.execute(
            select(func.count()).select_from(Documento).where(Documento.tema_id == t.id)
        )).scalar() or 0
        chunks = (await db.execute(
            select(func.count()).select_from(Chunk).join(Documento, Documento.id == Chunk.document_id)
            .where(Documento.tema_id == t.id)
        )).scalar() or 0
        salida.append({
            "id": t.id, "nombre": t.nombre, "descripcion": t.descripcion, "color": t.color,
            "carpetas": t.carpetas, "enfoque": t.enfoque, "tips_activo": t.tips_activo,
            "documentos": docs, "chunks": chunks,
            "creado_en": t.creado_en.isoformat(),
        })
    return salida


class TemaBody(BaseModel):
    nombre: str
    descripcion: str = ""
    color: str = "#2c5282"
    carpetas: str = ""
    enfoque: str = ""
    tips_activo: bool = True


@router.post("")
async def crear(body: TemaBody, db: AsyncSession = Depends(get_db)):
    nombre = body.nombre.strip()
    if not nombre:
        raise HTTPException(400, "El nombre es obligatorio")
    existe = (await db.execute(select(Tema).where(Tema.nombre == nombre))).scalar_one_or_none()
    if existe:
        raise HTTPException(409, f"Ya existe el tema «{nombre}»")
    tema = Tema(
        nombre=nombre, descripcion=body.descripcion.strip(),
        color=body.color if body.color.startswith("#") else "#2c5282",
        carpetas=",".join(c.strip().rstrip("/") for c in body.carpetas.split(",") if c.strip()),
        enfoque=body.enfoque.strip(),
        tips_activo=body.tips_activo,
    )
    db.add(tema)
    await db.commit()
    return {"ok": True, "id": tema.id,
            "nota": "ejecuta un escaneo para auto-clasificar por carpetas" if tema.carpetas else ""}


class TemaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    color: str | None = None
    carpetas: str | None = None
    enfoque: str | None = None
    tips_activo: bool | None = None


@router.put("/{tema_id}")
async def editar(tema_id: str, body: TemaUpdate, db: AsyncSession = Depends(get_db)):
    tema = await db.get(Tema, tema_id)
    if not tema:
        raise HTTPException(404, "Tema no existe")
    if body.nombre is not None and body.nombre.strip():
        tema.nombre = body.nombre.strip()
    if body.descripcion is not None:
        tema.descripcion = body.descripcion.strip()
    if body.color is not None and body.color.startswith("#"):
        tema.color = body.color
    if body.carpetas is not None:
        tema.carpetas = ",".join(c.strip().rstrip("/") for c in body.carpetas.split(",") if c.strip())
    if body.enfoque is not None:
        tema.enfoque = body.enfoque.strip()
    if body.tips_activo is not None:
        tema.tips_activo = body.tips_activo
    await db.commit()
    return {"ok": True}


@router.delete("/{tema_id}")
async def borrar(tema_id: str, mover_a: str | None = None, db: AsyncSession = Depends(get_db)):
    """Elimina el tema. Con documentos: exige mover_a (los reasigna y conserva
    los chunks); tips/decks/quizzes del tema se borran."""
    tema = await db.get(Tema, tema_id)
    if not tema:
        raise HTTPException(404, "Tema no existe")
    n_docs = (await db.execute(
        select(func.count()).select_from(Documento).where(Documento.tema_id == tema_id)
    )).scalar() or 0
    if n_docs:
        if not mover_a:
            raise HTTPException(409, f"El tema tiene {n_docs} documento(s); indica mover_a=<tema_id>")
        destino = await db.get(Tema, mover_a)
        if not destino:
            raise HTTPException(404, "El tema destino (mover_a) no existe")
        await db.execute(
            update(Documento).where(Documento.tema_id == tema_id).values(tema_id=mover_a)
        )
        await db.execute(
            update(Conversacion).where(Conversacion.tema_id == tema_id).values(tema_id=mover_a)
        )
    await db.delete(tema)  # tips/decks/quizzes caen por ON DELETE CASCADE
    await db.commit()
    return {"ok": True, "documentos_movidos": n_docs if n_docs else 0}


@router.post("/{tema_id}/reclasificar")
async def reclasificar(tema_id: str, db: AsyncSession = Depends(get_db)):
    """Reasigna documentos cuyas rutas calzan con las carpetas de ESTE tema."""
    tema = await db.get(Tema, tema_id)
    if not tema:
        raise HTTPException(404, "Tema no existe")
    prefijos = [c.strip().rstrip("/") for c in (tema.carpetas or "").split(",") if c.strip()]
    if not prefijos:
        raise HTTPException(400, "El tema no declara carpetas")
    movidos = 0
    docs = (await db.execute(select(Documento).where(Documento.fuente == "montada"))).scalars().all()
    for d in docs:
        if any(d.ruta.startswith(p) for p in prefijos) and d.tema_id != tema.id:
            d.tema_id = tema.id
            movidos += 1
    await db.commit()
    return {"ok": True, "movidos": movidos}


@router.get("/{tema_id}/stats")
async def stats_tema(tema_id: str, db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(
        select(func.count()).select_from(Documento).where(Documento.tema_id == tema_id)
    )).scalar() or 0
    tips_n = (await db.execute(
        select(func.count()).select_from(Tip).where(Tip.tema_id == tema_id)
    )).scalar() or 0
    decks = (await db.execute(
        select(func.count()).select_from(Deck).where(Deck.tema_id == tema_id)
    )).scalar() or 0
    quizzes = (await db.execute(
        select(func.count()).select_from(Quiz).where(Quiz.tema_id == tema_id)
    )).scalar() or 0
    return {"documentos": docs, "tips": tips_n, "decks": decks, "quizzes": quizzes}


@router.post("/escanear")
async def escanear():
    job_id = await encolar("escanear_fuentes")
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id,
            "mensaje": "Escaneo encolado (clasifica por carpetas de cada tema)"}
