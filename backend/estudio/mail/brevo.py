"""Relay SMTP Brevo — mismos valores que reportesDiariosGes (.env SMTP_*).

Patrón equivalente al transporte() de nodemailer: STARTTLS en 587,
falla temprano si falta configuración.
"""

from __future__ import annotations

import logging
import ssl

import aiosmtplib
from email.message import EmailMessage

from estudio.config import get_settings

log = logging.getLogger("estudio.mail")


def _transporte_config() -> dict:
    s = get_settings()
    if not (s.smtp_host and s.smtp_user and s.smtp_pass):
        raise RuntimeError("Falta configurar el SMTP (SMTP_HOST, SMTP_USER, SMTP_PASS)")
    puerto = int(s.smtp_port or 587)
    return {
        "hostname": s.smtp_host,
        "port": puerto,
        "start_tls": puerto != 465,
        "use_tls": puerto == 465,
        "username": s.smtp_user,
        "password": s.smtp_pass,
        "timeout": 30,
        "tls_context": ssl.create_default_context(),
    }


async def enviar(to: str, asunto: str, html: str, texto: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = f"Estudio Doctorado <{s.smtp_from or s.smtp_user}>"
    msg["To"] = to
    msg["Subject"] = asunto
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    await aiosmtplib.send(msg, **_transporte_config())
    log.info("Correo enviado a %s: %s", to, asunto)


async def probar() -> tuple[bool, str]:
    """Verifica autenticación SMTP SIN enviar correo (patrón probar_correo.py)."""
    try:
        cfg = _transporte_config()
    except RuntimeError as exc:
        return False, str(exc)
    try:
        cliente = aiosmtplib.SMTP(**cfg)
        await cliente.connect()
        await cliente.login(cfg["username"], cfg["password"])
        await cliente.quit()
        return True, f"Autenticación OK contra {cfg['hostname']}:{cfg['port']}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Falló la autenticación SMTP: {exc}"
