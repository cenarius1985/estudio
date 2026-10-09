"""Motor async de SQLAlchemy + DDL adicional (tsvector generado, índices pgvector)."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from estudio.config import get_settings

log = logging.getLogger("estudio.db")

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """Dependencia FastAPI: una sesión por request."""
    async with SessionLocal() as session:
        yield session


# DDL que SQLAlchemy no modela: columna tsvector generada (BM25), índices GIN/HNSW.
_DDL = [
    "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS tsv tsvector"
    " GENERATED ALWAYS AS (to_tsvector('simple', coalesce(texto, ''))) STORED",
    "CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (tsv)",
    "CREATE INDEX IF NOT EXISTS chunks_emb_idx ON chunks USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX IF NOT EXISTS tips_emb_idx ON tips USING hnsw (embedding vector_cosine_ops)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_ruta_fuente ON documents (ruta, fuente)",
]


async def crear_esquema() -> None:
    """create_all + DDL adicional. Idempotente; la llaman api y worker al arrancar."""
    from estudio.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in _DDL:
            await conn.execute(text(ddl))
    log.info("Esquema verificado (tablas + tsvector + índices vectoriales)")
