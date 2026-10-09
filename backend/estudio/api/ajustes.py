"""Ajustes del panel (tabla settings) + pruebas de SMTP y estado del sistema."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from estudio.config import get_settings
from estudio.db import SessionLocal
from estudio.llm import ping as llm_ping
from estudio.mail.brevo import probar as probar_smtp
from estudio.models import Setting

router = APIRouter(prefix="/ajustes", tags=["ajustes"])

CLAVES = ["tips_hora", "tips_to", "tips_umbral_dedupe", "tips_reintentos", "tips_habilitado"]


@router.get("")
async def obtener():
    s = get_settings()
    async with SessionLocal() as db:
        filas = (await db.execute(select(Setting).where(Setting.k.in_(CLAVES)))).scalars().all()
    guardados = {f.k: f.v for f in filas}
    return {
        "tips_hora": guardados.get("tips_hora", s.tips_hora),
        "tips_to": guardados.get("tips_to", s.tips_to),
        "tips_umbral_dedupe": float(guardados.get("tips_umbral_dedupe", s.tips_umbral_dedupe)),
        "tips_reintentos": int(guardados.get("tips_reintentos", s.tips_reintentos)),
        "tips_habilitado": guardados.get("tips_habilitado", "1") == "1",
        "smtp": {
            "host": s.smtp_host, "puerto": s.smtp_port,
            "usuario": s.smtp_user[:3] + "***" if s.smtp_user else "",
            "from": s.smtp_from, "configurado": s.smtp_configurado,
        },
        "llm": {"base_url": s.llm_base_url, "fallback_url": s.llm_fallback_url, "modelo": s.llm_model},
        "embed_model": s.embed_model,
    }


class AjustesBody(BaseModel):
    tips_hora: str | None = None
    tips_to: str | None = None
    tips_umbral_dedupe: float | None = None
    tips_reintentos: int | None = None
    tips_habilitado: bool | None = None


@router.put("")
async def guardar(body: AjustesBody):
    cambios = {
        "tips_hora": body.tips_hora,
        "tips_to": body.tips_to,
        "tips_umbral_dedupe": str(body.tips_umbral_dedupe) if body.tips_umbral_dedupe is not None else None,
        "tips_reintentos": str(body.tips_reintentos) if body.tips_reintentos is not None else None,
        "tips_habilitado": ("1" if body.tips_habilitado else "0") if body.tips_habilitado is not None else None,
    }
    async with SessionLocal() as db:
        for k, v in cambios.items():
            if v is None:
                continue
            fila = await db.get(Setting, k)
            if fila:
                fila.v = v
            else:
                db.add(Setting(k=k, v=v))
        await db.commit()
    return {"ok": True}


@router.post("/probar-smtp")
async def test_smtp():
    ok, mensaje = await probar_smtp()
    return {"ok": ok, "mensaje": mensaje}


@router.get("/estado")
async def estado():
    return {"llm": await llm_ping()}
