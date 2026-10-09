"""Auth simple de usuario único: POST /auth/login con ADMIN_PASSWORD →
token HMAC con expiración (30 días). El resto de endpoints lo exige en
la cabecera x-token."""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from estudio.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

DURACION_S = 30 * 24 * 3600


def _firma(exp: int) -> str:
    s = get_settings()
    return hmac.new(s.admin_password.encode(), f"admin:{exp}".encode(), hashlib.sha256).hexdigest()


def crear_token() -> str:
    exp = int(time.time()) + DURACION_S
    return f"{exp}.{_firma(exp)}"


def token_valido(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    try:
        exp, firma = token.split(".", 1)
        exp_i = int(exp)
    except ValueError:
        return False
    return exp_i > time.time() and hmac.compare_digest(firma, _firma(exp_i))


async def verificar_admin(x_token: str | None = Header(None)) -> None:
    if not token_valido(x_token):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


class Credenciales(BaseModel):
    password: str


@router.post("/login")
async def login(cred: Credenciales):
    s = get_settings()
    if not hmac.compare_digest(cred.password, s.admin_password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return {"token": crear_token(), "expira_en": DURACION_S}
