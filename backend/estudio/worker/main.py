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
from sqlalchemy import select, update

from estudio.config import get_settings
from estudio.db import SessionLocal, crear_esquema, engine
from estudio.models import Documento
from estudio.worker.jobs_estudio import generar_deck, generar_quiz
from estudio.worker.jobs_ingesta import escanear_fuentes, ingestar_archivo, ingestar_url, reindexar_documento
from estudio.worker.jobs_tips import chequear_tip_diario, generar_tip_diario, reenviar_tip

log = logging.getLogger("estudio.worker")


async def al_arrancar(ctx: dict) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    await crear_esquema()
    log.info("Worker listo")


async def al_arrancar_ingesta(ctx: dict) -> None:
    """Arranque del worker de ingesta: además, recupera documentos quedados
    en «procesando» (worker muerto a mitad de job) o «pendiente» sin job en
    cola — al arrancar no hay jobs en vuelo, así que todos se reencolan."""
    await al_arrancar(ctx)
    async with SessionLocal() as db:
        atascados = (await db.execute(
            select(Documento.id).where(Documento.estado.in_(["procesando", "pendiente"]))
        )).fetchall()
        if not atascados:
            return
        await db.execute(
            update(Documento).where(Documento.estado.in_(["procesando", "pendiente"]))
            .values(estado="pendiente")
        )
        await db.commit()
    for (did,) in atascados:
        await ctx["redis"].enqueue_job("ingestar_archivo", did)
    log.info("Reencolados %d documentos pendientes/_atascados al arrancar", len(atascados))


async def al_apagar(ctx: dict) -> None:
    await engine.dispose()


class WorkerSettings:
    """Worker de ingesta (cola default): pesado, OCR + embeddings."""

    functions = [escanear_fuentes, ingestar_archivo, ingestar_url, reindexar_documento]
    on_startup = al_arrancar_ingesta
    on_shutdown = al_apagar
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # UN job a la vez: con 2 tareas ARQ concurrentes + tramos síncronos largos
    # (OCR/embeddings) el segundo job moría con MissingGreenlet al conectar
    # (pares simultáneos, siempre). El paralelismo real lo aporta el pool de
    # OCR_HILOS dentro de cada job; la BD queda estrictamente secuencial.
    max_jobs = 1
    job_timeout = 3600
    keep_result = 3600


class WorkerSettingsUrgente:
    """Worker urgente (cola "urgentes"): tips diarios, decks, quizzes y URLs
    (lo que el usuario acaba de pedir y espera pronto)."""

    functions = [generar_tip_diario, reenviar_tip, generar_deck, generar_quiz, ingestar_url]
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
