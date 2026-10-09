#!/usr/bin/env python3
"""Drenaje manual de la ingesta: indexa directamente todos los documentos
pendiente/procesando SIN pasar por la cola ARQ.

Útil si la cola quedó envenenada o el worker tiene problemas:
    docker compose run --rm --no-deps -v "./scripts:/mnt" worker python /mnt/drenar.py
"""

import asyncio
import sys

sys.path.insert(0, "/app")


async def main() -> None:
    from sqlalchemy import select, text

    from estudio.db import SessionLocal
    from estudio.models import Documento
    from estudio.worker.jobs_ingesta import _indexar

    vuelta = 0
    while True:
        async with SessionLocal() as db:
            lote = (await db.execute(
                select(Documento.id).where(Documento.estado.in_(["pendiente", "procesando"])).limit(25)
            )).fetchall()
        if not lote:
            break
        for (did,) in lote:
            try:
                await _indexar(did)
            except Exception as exc:  # noqa: BLE001 — seguir con el resto
                print(f"!! {did}: {exc}", flush=True)
        async with SessionLocal() as db:
            restan = (await db.execute(
                select(Documento.id).where(Documento.estado.in_(["pendiente", "procesando"]))
            )).fetchall()
        vuelta += 1
        print(f"=== vuelta {vuelta}: restan {len(restan)} ===", flush=True)

    async with SessionLocal() as db:
        res = (await db.execute(text("SELECT estado, count(*) FROM documents GROUP BY estado"))).fetchall()
        chunks = (await db.execute(text("SELECT count(*) FROM chunks"))).scalar()
    print("FINAL:", res, "| chunks:", chunks, flush=True)


asyncio.run(main())
