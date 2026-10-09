"""App FastAPI: esquema al arrancar, routers protegidos por x-token."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from estudio.api.ajustes import router as ajustes_router
from estudio.api.auth import router as auth_router, verificar_admin
from estudio.api.chat import router as chat_router
from estudio.api.documentos import router as documentos_router
from estudio.api.estudio import router as estudio_router
from estudio.api.tips import router as tips_router
from estudio.config import get_settings
from estudio.db import crear_esquema, engine
from estudio.llm import ping as llm_ping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("estudio.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await crear_esquema()
    log.info("API lista")
    yield
    await engine.dispose()


app = FastAPI(title="Estudio — plataforma de estudio con IA local", version="0.2.0", lifespan=lifespan)

_s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_s.frontend_url, "http://localhost:8601", "http://127.0.0.1:8601"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
for r in (documentos_router, tips_router, chat_router, estudio_router, ajustes_router):
    app.include_router(r, dependencies=[Depends(verificar_admin)])


@app.get("/salud", tags=["salud"])
async def salud():
    estado: dict = {"api": "ok"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        estado["db"] = "ok"
    except Exception as exc:  # noqa: BLE001
        estado["db"] = f"error: {exc}"
    estado["llm"] = await llm_ping()
    return estado


@app.get("/stats", tags=["stats"], dependencies=[Depends(verificar_admin)])
async def stats():
    from sqlalchemy import func, select

    from estudio.db import SessionLocal
    from estudio.models import Arista, Chunk, Documento, Flashcard, Nodo, Tip, TipEnvio

    async with SessionLocal() as db:
        docs_por_estado = dict(
            (await db.execute(select(Documento.estado, func.count()).group_by(Documento.estado))).fetchall()
        )
        docs_por_tipo = dict(
            (await db.execute(select(Documento.tipo, func.count()).group_by(Documento.tipo))).fetchall()
        )
        total_chunks = (await db.execute(select(func.count()).select_from(Chunk))).scalar() or 0
        total_tips = (await db.execute(select(func.count()).select_from(Tip))).scalar() or 0
        envios_ok = (
            await db.execute(select(func.count()).select_from(TipEnvio).where(TipEnvio.estado == "ok"))
        ).scalar() or 0
        total_nodos = (await db.execute(select(func.count()).select_from(Nodo))).scalar() or 0
        total_aristas = (await db.execute(select(func.count()).select_from(Arista))).scalar() or 0
        flashcards = (await db.execute(select(func.count()).select_from(Flashcard))).scalar() or 0
    return {
        "documentos": {"por_estado": docs_por_estado, "por_tipo": docs_por_tipo},
        "chunks": total_chunks,
        "tips": total_tips,
        "envios_ok": envios_ok,
        "grafo": {"nodos": total_nodos, "aristas": total_aristas},
        "flashcards": flashcards,
    }
