"""Configuración de los workers ARQ.

Dos colas (para que un tip diario nunca quede atrás de una ingesta masiva):
- cola default (worker):      escanear_fuentes / ingestar_archivo / reindexar (CPU intensivo)
- cola "urgentes" (worker-urgente): tips diarios + decks + quizzes (rápidos)

El cron del tip diario vive en el worker urgente.
"""

from __future__ import annotations

import logging

from arq import cron
from arq.connections import RedisSettings

from estudio.config import get_settings
from estudio.db import crear_esquema, engine
from estudio.worker.jobs_estudio import generar_deck, generar_quiz
from estudio.worker.jobs_ingesta import escanear_fuentes, ingestar_archivo, reindexar_documento
from estudio.worker.jobs_tips import chequear_tip_diario, generar_tip_diario, reenviar_tip

log = logging.getLogger("estudio.worker")


async def al_arrancar(ctx: dict) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    await crear_esquema()
    log.info("Worker listo")


async def al_apagar(ctx: dict) -> None:
    await engine.dispose()


class WorkerSettings:
    """Worker de ingesta (cola default): pesado, OCR + embeddings."""

    functions = [escanear_fuentes, ingestar_archivo, reindexar_documento]
    on_startup = al_arrancar
    on_shutdown = al_apagar
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 2  # embeddings (ORT suelta el GIL) y OCR en subproceso → escala
    job_timeout = 3600
    keep_result = 3600


class WorkerSettingsUrgente:
    """Worker urgente (cola "urgentes"): tips diarios, decks, quizzes."""

    functions = [generar_tip_diario, reenviar_tip, generar_deck, generar_quiz]
    cron_jobs = [
        # Chequeo cada 15 min: dispara la generación cuando llega TIPS_HORA y
        # aún no hay tip enviado hoy (idempotente; respeta cambios del panel).
        cron(chequear_tip_diario, minute={0, 15, 30, 45}, unique=True, timeout=120)
    ]
    on_startup = al_arrancar
    on_shutdown = al_apagar
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    queue_name = get_settings().cola_urgentes
    max_jobs = 1
    job_timeout = 1800
    keep_result = 3600
