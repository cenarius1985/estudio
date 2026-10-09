"""Utilidades compartidas del worker (ajustes en BD, zona horaria)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.config import get_settings
from estudio.models import Setting

ZONA = ZoneInfo("America/Santiago")


def hoy_local() -> date:
    return datetime.now(ZONA).date()


async def obtener_ajuste(db: AsyncSession, clave: str, default: str) -> str:
    """Los ajustes del panel (tabla settings) pisan los defaults del .env."""
    fila = await db.get(Setting, clave)
    if fila and fila.v.strip():
        return fila.v.strip()
    return default


async def obtener_ajustes_tips(db: AsyncSession) -> dict:
    s = get_settings()
    hora = await obtener_ajuste(db, "tips_hora", s.tips_hora)
    destinos = await obtener_ajuste(db, "tips_to", s.tips_to)
    por_dia = int(await obtener_ajuste(db, "tips_por_dia", str(s.tips_por_dia)))
    umbral = float(await obtener_ajuste(db, "tips_umbral_dedupe", str(s.tips_umbral_dedupe)))
    reintentos = int(await obtener_ajuste(db, "tips_reintentos", str(s.tips_reintentos)))
    habilitado = (await obtener_ajuste(db, "tips_habilitado", "1")) == "1"
    return {
        "hora": hora,
        "por_dia": max(1, min(10, por_dia)),
        "destinos": [e.strip() for e in destinos.split(",") if e.strip() and "@" in e],
        "umbral": umbral,
        "reintentos": reintentos,
        "habilitado": habilitado,
    }
