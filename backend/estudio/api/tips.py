"""Tips: historial, preview, generar/enviar ahora, reenviar sin reprocesar."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.api.cola import encolar
from estudio.db import get_db
from estudio.models import Chunk, Tip, TipEnvio, TipChunk

router = APIRouter(prefix="/tips", tags=["tips"])


@router.get("")
async def historial(limite: int = 100, db: AsyncSession = Depends(get_db)):
    tips = (
        await db.execute(select(Tip).order_by(desc(Tip.fecha), desc(Tip.creado_en)).limit(limite))
    ).scalars().all()
    resultado = []
    for t in tips:
        envios = (
            await db.execute(select(TipEnvio).where(TipEnvio.tip_id == t.id))
        ).scalars().all()
        resultado.append(
            {
                "id": t.id, "fecha": t.fecha.isoformat(), "titulo": t.titulo,
                "estado": t.estado, "duplicado_de": t.duplicado_de,
                "creado_en": t.creado_en.isoformat(), "enviado_en": t.enviado_en.isoformat() if t.enviado_en else None,
                "envios": [
                    {"email": e.email, "estado": e.estado, "error": e.error} for e in envios
                ],
            }
        )
    return resultado


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Tip))).scalar() or 0
    por_estado = dict(
        (await db.execute(select(Tip.estado, func.count()).group_by(Tip.estado))).fetchall()
    )
    envios_ok = (
        await db.execute(select(func.count()).select_from(TipEnvio).where(TipEnvio.estado == "ok"))
    ).scalar() or 0
    chunks_total = (await db.execute(select(func.count()).select_from(Chunk))).scalar() or 0
    cubiertos = (await db.execute(select(func.count()).select_from(TipChunk))).scalar() or 0
    ultimo = (
        await db.execute(select(Tip).where(Tip.estado == "enviado").order_by(desc(Tip.enviado_en)).limit(1))
    ).scalar_one_or_none()
    return {
        "total": total, "por_estado": por_estado, "envios_ok": envios_ok,
        "cobertura_chunks": {
            "total": chunks_total,
            "cubiertos": cubiertos,
            "pct": round(100 * cubiertos / chunks_total, 1) if chunks_total else 0.0,
        },
        "ultimo_enviado": {
            "fecha": ultimo.fecha.isoformat(), "titulo": ultimo.titulo
        } if ultimo else None,
    }


@router.get("/{tip_id}")
async def detalle(tip_id: str, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tip, tip_id)
    if not t:
        raise HTTPException(404, "Tip no existe")
    envios = (await db.execute(select(TipEnvio).where(TipEnvio.tip_id == tip_id))).scalars().all()
    return {
        "id": t.id, "fecha": t.fecha.isoformat(), "titulo": t.titulo,
        "cuerpo_html": t.cuerpo_html, "cuerpo_texto": t.cuerpo_texto,
        "estado": t.estado, "duplicado_de": t.duplicado_de,
        "creado_en": t.creado_en.isoformat(), "enviado_en": t.enviado_en.isoformat() if t.enviado_en else None,
        "envios": [{"email": e.email, "estado": e.estado, "error": e.error, "enviado_en": e.enviado_en.isoformat()} for e in envios],
    }


class GenerarBody(BaseModel):
    forzar: bool = False


@router.post("/generar")
async def generar(body: GenerarBody):
    job_id = await encolar("generar_tip_diario", body.forzar, urgente=True)
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id, "forzar": body.forzar}


@router.post("/{tip_id}/reenviar")
async def reenviar(tip_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(Tip, tip_id):
        raise HTTPException(404, "Tip no existe")
    job_id = await encolar("reenviar_tip", tip_id, urgente=True)
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "job": job_id, "mensaje": "Reenvío encolado usando el contenido almacenado (sin reprocesar)"}
