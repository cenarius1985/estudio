"""Encolado de jobs ARQ desde la API.

Cola default = ingesta (pesada). Cola "urgentes" = tips/decks/quizzes,
atendida por el worker-urgente para no quedar tras una ingesta masiva.
"""

from __future__ import annotations

import logging

from arq import create_pool
from arq.connections import RedisSettings

from estudio.config import get_settings

log = logging.getLogger("estudio.cola")


async def encolar(job: str, *args, urgente: bool = False) -> str | None:
    """Encola un job en el worker; devuelve job_id (None si el worker no está)."""
    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        cola = get_settings().cola_urgentes if urgente else None
        j = await pool.enqueue_job(job, *args, _queue_name=cola)
        return j.job_id if j else None
    finally:
        await pool.aclose()
