"""Motor async de SQLAlchemy + DDL adicional (tsvector generado, índices pgvector)."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from estudio.config import get_settings

log = logging.getLogger("estudio.db")

settings = get_settings()
# NullPool: conexión fresca por uso. En el worker (tareas ARQ concurrentes con
# tramos síncronos largos de OCR/embeddings) un pool compartido provocaba
# MissingGreenlet en el pre-ping al reutilizar conexiones entre greenlets;
# el coste de conectar en localhost es despreciable frente a la ingesta.
engine = create_async_engine(settings.database_url, poolclass=NullPool)
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
    # ---- multi-tema: la tabla temas la crea create_all; el tema «general» es
    # el destino de todo lo pre-existente (no se pierde nada indexado).
    "INSERT INTO temas (id, nombre, descripcion, color, carpetas, tips_activo, creado_en) VALUES"
    " ('general', 'General', 'Documentos sin tema asignado', '#64748b', '', true, NOW())"
    " ON CONFLICT (id) DO NOTHING",
]

# tema_id en las tablas existentes (ALTER + backfill a «general» + índice)
_TEMA_ALTERS = [
    ("documents", "SET NULL"),
    ("tips", "CASCADE"),
    ("conversaciones", "SET NULL"),
    ("decks", "CASCADE"),
    ("quizzes", "CASCADE"),
]
_DDL += [
    f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS tema_id VARCHAR(32)"
    f" REFERENCES temas(id) ON DELETE {on_delete}" for tabla, on_delete in _TEMA_ALTERS
]
_DDL += [f"UPDATE {tabla} SET tema_id = 'general' WHERE tema_id IS NULL"
         for tabla, _ in _TEMA_ALTERS]
_DDL += [f"CREATE INDEX IF NOT EXISTS ix_{tabla}_tema ON {tabla} (tema_id)"
         for tabla, _ in _TEMA_ALTERS]


async def crear_esquema() -> None:
    """create_all + DDL adicional. Idempotente y tolerante a concurrencia:
    cada sentencia va en su transacción con lock_timeout (los ALTER incluso
    siendo no-ops necesitan lock exclusivo, y la ingesta puede tener la tabla
    caliente), con reintentos porque api y worker arrancan a la vez."""
    import asyncio

    from estudio.models import Base

    ultimo: Exception | None = None
    for intento in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            for ddl in _DDL:
                async with engine.begin() as conn:
                    await conn.execute(text("SET LOCAL lock_timeout = '3s'"))
                    await conn.execute(text(ddl))
            log.info("Esquema verificado (tablas + tsvector + índices + temas)")
            return
        except Exception as exc:  # noqa: BLE001 — carrera/lock temporal al arrancar
            ultimo = exc
            log.warning("crear_esquema intento %d falló (%s); reintento", intento + 1, exc)
            await asyncio.sleep(2 + intento)
    raise ultimo  # type: ignore[misc]
