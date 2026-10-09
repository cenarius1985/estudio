"""Ajustes del panel: TODAS las credenciales se gestionan aquí (tabla settings,
que pisa al .env cuando está seteada). Lectura siempre enmascarada; escritura
de secretos write-only. Incluye prueba de SMTP y estado del LLM."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.config import get_settings
from estudio.credenciales import (
    cambiar_password,
    config_llm,
    config_smtp,
    eliminar_setting,
    guardar_setting,
    obtener_setting,
    resolver,
    ruta_fuentes_efectiva,
)
from estudio.db import SessionLocal, get_db
from estudio.llm import ping as llm_ping
from estudio.mail.brevo import probar as probar_smtp
from estudio.worker.comun import obtener_ajustes_tips

router = APIRouter(prefix="/ajustes", tags=["ajustes"])


def _mascaras(texto: str, visibles: int = 3) -> str:
    if not texto:
        return ""
    if len(texto) <= visibles:
        return "*" * len(texto)
    return texto[:visibles] + "*" * (len(texto) - visibles)


@router.get("")
async def obtener(db: AsyncSession = Depends(get_db)):
    s = get_settings()
    ajustes_tips = await obtener_ajustes_tips(db)
    smtp = await config_smtp(db)
    llm = await config_llm(db)
    api_key_seteada = bool(llm.pop("api_key", ""))  # la clave nunca sale de la API
    ruta = await ruta_fuentes_efectiva(db)
    pass_personalizada = bool(await obtener_setting(db, "admin_password_hash"))
    return {
        "smtp": {
            "host": smtp["host"], "puerto": smtp["puerto"],
            "usuario": smtp["user"], "usuario_marcado": _mascaras(smtp["user"]),
            "password_seteada": bool(smtp["pass"]),
            "from": smtp["from"],
            "configurado": smtp["configurado"],
        },
        "tips": ajustes_tips,
        "ruta_fuentes": ruta,
        "ruta_fuentes_existe": Path(ruta).is_dir(),
        "ruta_fuentes_env": s.ruta_fuentes,
        "llm": {**llm, "api_key_seteada": api_key_seteada},
        "password_panel": "personalizada" if pass_personalizada else "del .env",
        "brevo_url": "https://www.brevo.com/",
    }


class AjustesBody(BaseModel):
    # Correo Brevo (None = no tocar; "" = volver al valor del .env)
    smtp_host: str | None = None
    smtp_puerto: int | None = None
    smtp_user: str | None = None
    smtp_pass: str | None = None  # write-only
    smtp_from: str | None = None
    # Tips
    tips_hora: str | None = None
    tips_to: str | None = None
    tips_por_dia: int | None = None
    tips_umbral_dedupe: float | None = None
    tips_reintentos: int | None = None
    tips_habilitado: bool | None = None
    # Fuentes / LLM
    ruta_fuentes: str | None = None
    llm_base_url: str | None = None
    llm_fallback_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None  # write-only; "" = borrar (vuelve al .env)
    # Seguridad (write-only). restablecer_password=True vuelve a la del .env.
    admin_password_nueva: str | None = None
    admin_password_restablecer: bool = False


_ESCRITURA_SIMPLE = {
    "smtp_host": "smtp_host",
    "smtp_user": "smtp_user",
    "smtp_pass": "smtp_pass",
    "smtp_from": "smtp_from",
    "ruta_fuentes": "ruta_fuentes",
    "llm_base_url": "llm_base_url",
    "llm_fallback_url": "llm_fallback_url",
    "llm_model": "llm_model",
    "llm_api_key": "llm_api_key",
    "tips_to": "tips_to",
}


@router.put("")
async def guardar(body: AjustesBody, db: AsyncSession = Depends(get_db)):
    cambios: list[str] = []

    for campo_body, clave in _ESCRITURA_SIMPLE.items():
        valor = getattr(body, campo_body)
        if valor is None:
            continue
        if valor == "":
            await eliminar_setting(db, clave)  # "" → vuelve al .env
            cambios.append(f"{clave} → usa .env")
        else:
            await guardar_setting(db, clave, valor.strip())
            cambios.append(clave)

    if body.smtp_puerto is not None:
        await guardar_setting(db, "smtp_port", str(body.smtp_puerto))
        cambios.append("smtp_port")

    for campo, clave in (("tips_hora", "tips_hora"),):
        valor = getattr(body, campo)
        if valor is not None and re.fullmatch(r"\d{1,2}:\d{2}", valor.strip()):
            await guardar_setting(db, clave, valor.strip())
            cambios.append(clave)

    if body.tips_por_dia is not None and 1 <= body.tips_por_dia <= 10:
        await guardar_setting(db, "tips_por_dia", str(body.tips_por_dia))
        cambios.append("tips_por_dia")
    if body.tips_umbral_dedupe is not None and 0.5 <= body.tips_umbral_dedupe <= 1.0:
        await guardar_setting(db, "tips_umbral_dedupe", str(body.tips_umbral_dedupe))
        cambios.append("tips_umbral_dedupe")
    if body.tips_reintentos is not None and 1 <= body.tips_reintentos <= 10:
        await guardar_setting(db, "tips_reintentos", str(body.tips_reintentos))
        cambios.append("tips_reintentos")
    if body.tips_habilitado is not None:
        await guardar_setting(db, "tips_habilitado", "1" if body.tips_habilitado else "0")
        cambios.append("tips_habilitado")

    if body.admin_password_restablecer:
        await eliminar_setting(db, "admin_password_hash")
        cambios.append("password → vuelve a la del .env")
    elif body.admin_password_nueva:
        if len(body.admin_password_nueva) < 8:
            raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
        await cambiar_password(db, body.admin_password_nueva)
        cambios.append("password actualizada (vuelve a iniciar sesión)")

    await db.commit()
    return {"ok": True, "cambios": cambios}


@router.get("/llm/proveedores")
async def proveedores_llm():
    """Catálogo de presets (local, de pago con API key, personalizado)."""
    from estudio.llm.proveedores import PROVEEDORES

    return PROVEEDORES


@router.post("/probar-smtp")
async def test_smtp(db: AsyncSession = Depends(get_db)):
    cfg = await config_smtp(db)
    ok, mensaje = await probar_smtp(cfg)
    return {"ok": ok, "mensaje": mensaje}


@router.get("/estado")
async def estado(db: AsyncSession = Depends(get_db)):
    return {"llm": await llm_ping(await config_llm(db))}
