"""Encolado de jobs ARQ desde la API."""

from __future__ import annotations

import logging

from arq import create_pool
from arq.connections import RedisSettings

from estudio.config import get_settings

log = logging.getLogger("estudio.cola")


async def encolar(job: str, *args) -> str | None:
    """Encola un job en el worker; devuelve job_id (None si el worker no está)."""
    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        j = await pool.enqueue_job(job, *args)
        return j.job_id if j else None
    finally:
        await pool.aclose()
