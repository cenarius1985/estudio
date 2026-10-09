"""Auth de usuario único: POST /auth/login → token HMAC (30 días).

La contraseña vive en la tabla settings (cambiable desde Ajustes, hash sha256)
o, en su defecto, en ADMIN_PASSWORD del .env. Cambiarla invalida los tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.credenciales import password_valida, secreto_admin
from estudio.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

DURACION_S = 30 * 24 * 3600


def _firma(secreto: str, exp: int) -> str:
    return hmac.new(secreto.encode(), f"admin:{exp}".encode(), hashlib.sha256).hexdigest()


def _crear_token(secreto: str) -> str:
    exp = int(time.time()) + DURACION_S
    return f"{exp}.{_firma(secreto, exp)}"


def _token_valido(token: str | None, secreto: str) -> bool:
    if not token or "." not in token:
        return False
    try:
        exp, firma = token.split(".", 1)
        exp_i = int(exp)
    except ValueError:
        return False
    return exp_i > time.time() and hmac.compare_digest(firma, _firma(secreto, exp_i))


async def verificar_admin(
    x_token: str | None = Header(None), db: AsyncSession = Depends(get_db)
) -> None:
    secreto = await secreto_admin(db)
    if not _token_valido(x_token, secreto):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


class Credenciales(BaseModel):
    password: str


@router.post("/login")
async def login(cred: Credenciales, db: AsyncSession = Depends(get_db)):
    if not await password_valida(db, cred.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return {"token": _crear_token(await secreto_admin(db)), "expira_en": DURACION_S}
