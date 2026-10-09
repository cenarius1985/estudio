"""Resolución de credenciales/configuración: tabla settings (panel) → .env → vacío.

Open source: quien no toque el .env configura TODO desde el panel; los valores
del panel (BD) pisan a los del .env cuando existen.
"""

from __future__ import annotations

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from estudio.config import get_settings
from estudio.models import Setting


async def obtener_setting(db: AsyncSession, clave: str) -> str | None:
    fila = await db.get(Setting, clave)
    if fila and fila.v.strip():
        return fila.v.strip()
    return None


async def guardar_setting(db: AsyncSession, clave: str, valor: str) -> None:
    fila = await db.get(Setting, clave)
    if fila:
        fila.v = valor
    else:
        db.add(Setting(k=clave, v=valor))


async def eliminar_setting(db: AsyncSession, clave: str) -> None:
    fila = await db.get(Setting, clave)
    if fila:
        await db.delete(fila)


async def resolver(db: AsyncSession, clave_setting: str, valor_env: str) -> str:
    """BD (panel) si está seteada; si no, el valor del .env; si no, vacío."""
    en_bd = await obtener_setting(db, clave_setting)
    return en_bd or (valor_env or "")


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


async def config_smtp(db: AsyncSession) -> dict:
    """Config SMTP Brevo resuelta (BD → .env). Claves: host, puerto, user, pass, from."""
    s = get_settings()
    host = await resolver(db, "smtp_host", s.smtp_host)
    user = await resolver(db, "smtp_user", s.smtp_user)
    password = await resolver(db, "smtp_pass", s.smtp_pass)
    puerto = await resolver(db, "smtp_port", str(s.smtp_port or 587))
    try:
        puerto_i = int(puerto)
    except ValueError:
        puerto_i = 587
    remitente = await resolver(db, "smtp_from", s.smtp_from) or user
    return {
        "host": host, "puerto": puerto_i, "user": user,
        "pass": password, "from": remitente,
        "configurado": bool(host and user and password),
    }


async def config_llm(db: AsyncSession) -> dict:
    s = get_settings()
    return {
        "base_url": await resolver(db, "llm_base_url", s.llm_base_url),
        "fallback_url": await resolver(db, "llm_fallback_url", s.llm_fallback_url),
        "model": await resolver(db, "llm_model", s.llm_model),
    }


async def ruta_fuentes_efectiva(db: AsyncSession) -> str:
    s = get_settings()
    return await resolver(db, "ruta_fuentes", s.ruta_fuentes)


# ---------------------------------------------------------------- contraseña del panel
# Si existe el ajuste admin_password_hash, esa es la contraseña vigente (hash
# sha256); si no, manda ADMIN_PASSWORD del .env. El "secreto" para firmar
# tokens es el hash o la contraseña del .env: cambiarla invalida los tokens.


async def cambiar_password(db: AsyncSession, nueva: str) -> None:
    await guardar_setting(db, "admin_password_hash", _sha256(nueva))


async def restablecer_password(db: AsyncSession) -> None:
    """Vuelve a la contraseña del .env."""
    await eliminar_setting(db, "admin_password_hash")


async def secreto_admin(db: AsyncSession) -> str:
    en_bd = await obtener_setting(db, "admin_password_hash")
    return en_bd or get_settings().admin_password


async def password_valida(db: AsyncSession, candidata: str) -> bool:
    secreto = await secreto_admin(db)
    en_bd = await obtener_setting(db, "admin_password_hash")
    if en_bd:
        return _sha256(candidata) == en_bd
    return candidata == secreto
