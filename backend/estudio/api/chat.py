"""Chat con la tesis: SSE con citas estrictas (anti-alucinación).

Eventos SSE: fuentes → deltas → fin | error. El LLM solo ve los fragmentos
recuperados; si no hay LLM o no hay contexto, se responde fielmente sin
inventar nada.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.db import SessionLocal, get_db
from estudio.llm import LLMNoDisponible, chat_stream
from estudio.models import Conversacion, Mensaje
from estudio.rag.prompts import SISTEMA_CHAT, construir_contexto
from estudio.rag.retrieval import recuperar

router = APIRouter(tags=["chat"])

MAX_HISTORIAL = 6  # turnos previos que se envían como contexto conversacional


def _evento(nombre: str, dato) -> str:
    return f"event: {nombre}\ndata: {json.dumps(dato, ensure_ascii=False)}\n\n"


class PreguntaBody(BaseModel):
    conversacion_id: str | None = None
    pregunta: str


@router.post("/chat")
async def chat(body: PreguntaBody, db: AsyncSession = Depends(get_db)):
    if not body.pregunta.strip():
        return StreamingResponse(
            iter([_evento("error", {"mensaje": "Pregunta vacía"})]),
            media_type="text/event-stream",
        )

    conversacion_id = body.conversacion_id
    if not conversacion_id:
        conv = Conversacion(titulo=body.pregunta[:80])
        db.add(conv)
        await db.flush()
        conversacion_id = conv.id
    db.add(Mensaje(conversacion_id=conversacion_id, rol="user", contenido=body.pregunta))
    await db.commit()

    historial = (
        await db.execute(
            select(Mensaje.rol, Mensaje.contenido)
            .where(Mensaje.conversacion_id == conversacion_id)
            .order_by(desc(Mensaje.id)).limit(MAX_HISTORIAL)
        )
    ).fetchall()[::-1]

    fragmentos = await recuperar(db, body.pregunta)

    async def flujo():
        yield _evento("inicio", {"conversacion_id": conversacion_id})
        if not fragmentos:
            texto = (
                "No encontré eso en tus documentos. Aún no hay fragmentos "
                "indexados que coincidan — indexa material o reformula la pregunta."
            )
            yield _evento("delta", {"t": texto})
            async with SessionLocal() as s2:
                s2.add(Mensaje(conversacion_id=conversacion_id, rol="assistant", contenido=texto, fuentes=[]))
                await s2.commit()
            yield _evento("fin", {"conversacion_id": conversacion_id})
            return

        yield _evento(
            "fuentes",
            [
                {"archivo": f.archivo, "pagina": f.pagina, "origen": f.origen, "score": f.score}
                for f in fragmentos
            ],
        )

        mensajes = [{"role": "system", "content": SISTEMA_CHAT}]
        for rol, contenido in historial[:-1]:
            mensajes.append({"role": "user" if rol == "user" else "assistant", "content": contenido[:1500]})
        mensajes.append(
            {
                "role": "user",
                "content": f"FRAGMENTOS:\n\n{construir_contexto(fragmentos)}\n\n"
                f"PREGUNTA: {body.pregunta}",
            }
        )

        acumulado: list[str] = []
        try:
            async for delta in chat_stream(mensajes, temperature=0.2, max_tokens=900):
                acumulado.append(delta)
                yield _evento("delta", {"t": delta})
        except LLMNoDisponible as exc:
            texto = (
                "⚠️ No hay LLM disponible ahora (revisa el servicio bonsai o el "
                "fallback en Ajustes). Lo encontrado en tus documentos:\n\n"
                + "\n---\n".join(
                    f"[Fuente {i}] {f.archivo}"
                    + (f" (pág. {f.pagina})" if f.pagina else "")
                    + f": {f.texto[:600]}"
                    for i, f in enumerate(fragmentos, 1)
                )
            )
            yield _evento("delta", {"t": texto})
            acumulado = [texto]
            _ = exc

        respuesta = "".join(acumulado)
        async with SessionLocal() as s2:
            s2.add(
                Mensaje(
                    conversacion_id=conversacion_id,
                    rol="assistant",
                    contenido=respuesta,
                    fuentes=[
                        {"archivo": f.archivo, "pagina": f.pagina} for f in fragmentos
                    ],
                )
            )
            await s2.commit()
        yield _evento("fin", {"conversacion_id": conversacion_id})

    return StreamingResponse(flujo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/conversaciones")
async def conversaciones(db: AsyncSession = Depends(get_db)):
    filas = (
        await db.execute(
            select(Conversacion).order_by(desc(Conversacion.creado_en)).limit(100)
        )
    ).scalars().all()
    return [{"id": c.id, "titulo": c.titulo, "creado_en": c.creado_en.isoformat()} for c in filas]


@router.get("/conversaciones/{conversacion_id}/mensajes")
async def mensajes(conversacion_id: str, db: AsyncSession = Depends(get_db)):
    filas = (
        await db.execute(
            select(Mensaje).where(Mensaje.conversacion_id == conversacion_id).order_by(Mensaje.id)
        )
    ).scalars().all()
    return [
        {"rol": m.rol, "contenido": m.contenido, "fuentes": m.fuentes, "creado_en": m.creado_en.isoformat()}
        for m in filas
    ]
