"""Relay SMTP Brevo. La configuración se RESUELVE (BD panel → .env) fuera de
aquí y se pasa como dict — ver estudio.credenciales.config_smtp."""

from __future__ import annotations

import logging
import ssl
from email.message import EmailMessage

import aiosmtplib

log = logging.getLogger("estudio.mail")


def smtp_configurado(cfg: dict) -> bool:
    return bool(cfg.get("host") and cfg.get("user") and cfg.get("pass"))


async def enviar(to: str, asunto: str, html: str, texto: str, cfg: dict) -> None:
    if not smtp_configurado(cfg):
        raise RuntimeError("SMTP sin configurar (Ajustes → Correo Brevo, o SMTP_* en .env)")
    msg = EmailMessage()
    msg["From"] = f"Estudio <{cfg['from'] or cfg['user']}>"
    msg["To"] = to
    msg["Subject"] = asunto
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    puerto = int(cfg.get("puerto") or 587)
    await aiosmtplib.send(
        msg,
        hostname=cfg["host"],
        port=puerto,
        start_tls=puerto != 465,
        use_tls=puerto == 465,
        username=cfg["user"],
        password=cfg["pass"],
        timeout=30,
        tls_context=ssl.create_default_context(),
    )
    log.info("Correo enviado a %s: %s", to, asunto)


async def probar(cfg: dict) -> tuple[bool, str]:
    """Verifica autenticación SMTP SIN enviar correo."""
    if not smtp_configurado(cfg):
        return False, "SMTP incompleto: falta host, usuario o contraseña"
    puerto = int(cfg.get("puerto") or 587)
    try:
        cliente = aiosmtplib.SMTP(
            hostname=cfg["host"], port=puerto, start_tls=puerto != 465,
            use_tls=puerto == 465, username=cfg["user"], password=cfg["pass"],
            timeout=20, tls_context=ssl.create_default_context(),
        )
        await cliente.connect()
        await cliente.quit()
        return True, f"Autenticación OK contra {cfg['host']}:{puerto}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Falló la autenticación SMTP: {exc}"
