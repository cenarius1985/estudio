#!/usr/bin/env python3
"""Verifica la autenticación SMTP de Brevo SIN enviar correo (stdlib).

Uso: python scripts/probar_correo.py  (lee el .env del proyecto)
"""

from __future__ import annotations

import smtplib
import ssl
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer_env() -> dict[str, str]:
    valores: dict[str, str] = {}
    env = RAIZ / ".env"
    if not env.exists():
        return valores
    for linea in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        valores[k.strip()] = v.strip()
    return valores


def main() -> int:
    env = leer_env()
    host = env.get("SMTP_HOST", "smtp-relay.brevo.com")
    puerto = int(env.get("SMTP_PORT", "587"))
    usuario = env.get("SMTP_USER", "")
    clave = env.get("SMTP_PASS", "")

    if not (host and usuario and clave):
        print("❌ Falta SMTP_HOST/SMTP_USER/SMTP_PASS en el .env "
              "(configúralos en el panel: Ajustes → Correo Brevo)")
        return 1

    print(f"Conectando a {host}:{puerto} (STARTTLS)…")
    try:
        with smtplib.SMTP(host, puerto, timeout=20) as srv:
            srv.starttls(context=ssl.create_default_context())
            srv.login(usuario, clave)
        print("✅ Autenticación SMTP correcta — Brevo aceptó las credenciales "
              "(no se envió ningún correo).")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Falló la autenticación: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
