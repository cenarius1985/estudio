"""Estudio tipo Astra: decks/flashcards (SM-2 lite) y quizzes/simulacros."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.api.cola import encolar
from estudio.db import get_db
from estudio.models import Deck, Flashcard, Intento, Pregunta, Quiz

router = APIRouter(prefix="/estudio", tags=["estudio"])


# ---------------------------------------------------------------- decks


class DeckBody(BaseModel):
    documento_id: str | None = None
    n: int = 12


@router.post("/decks")
async def crear_deck(body: DeckBody, db: AsyncSession = Depends(get_db)):
    deck = Deck(
        titulo="Generando…", documento_id=body.documento_id, estado="pendiente"
    )
    db.add(deck)
    await db.flush()
    await db.commit()
    job_id = await encolar("generar_deck", deck.id, body.documento_id, min(max(body.n, 4), 30))
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "deck_id": deck.id}


@router.get("/decks")
async def listar_decks(db: AsyncSession = Depends(get_db)):
    decks = (await db.execute(select(Deck).order_by(Deck.creado_en.desc()).limit(100))).scalars().all()
    salida = []
    for d in decks:
        n = (await db.execute(select(func.count()).select_from(Flashcard).where(Flashcard.deck_id == d.id))).scalar() or 0
        pendientes = (
            await db.execute(
                select(func.count()).select_from(Flashcard)
                .where(Flashcard.deck_id == d.id, Flashcard.proxima_repaso <= date.today())
            )
        ).scalar() or 0
        salida.append(
            {"id": d.id, "titulo": d.titulo, "estado": d.estado, "error": d.error,
             "documento_id": d.documento_id, "tarjetas": n, "pendientes_hoy": pendientes,
             "creado_en": d.creado_en.isoformat()}
        )
    return salida


@router.get("/decks/{deck_id}")
async def detalle_deck(deck_id: str, solo_pendientes: bool = False, db: AsyncSession = Depends(get_db)):
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(404, "Deck no existe")
    q = select(Flashcard).where(Flashcard.deck_id == deck_id).order_by(Flashcard.id)
    if solo_pendientes:
        q = q.where(Flashcard.proxima_repaso <= date.today())
    tarjetas = (await db.execute(q)).scalars().all()
    return {
        "id": deck.id, "titulo": deck.titulo, "estado": deck.estado, "error": deck.error,
        "tarjetas": [
            {
                "id": t.id, "frente": t.frente, "reverso": t.reverso, "cita": t.cita,
                "intervalo_dias": t.intervalo_dias, "proxima_repaso": t.proxima_repaso.isoformat(),
            }
            for t in tarjetas
        ],
    }


class RepasoBody(BaseModel):
    calidad: int  # 0-5 (SM-2)


@router.post("/flashcards/{flashcard_id}/repasar")
async def repasar(flashcard_id: int, body: RepasoBody, db: AsyncSession = Depends(get_db)):
    t = await db.get(Flashcard, flashcard_id)
    if not t:
        raise HTTPException(404, "Flashcard no existe")
    q = max(0, min(5, body.calidad))

    # SM-2 lite
    if q < 3:
        t.reps = 0
        t.intervalo_dias = 1
    else:
        t.ease = max(1.3, t.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
        t.reps += 1
        t.intervalo_dias = 1 if t.reps == 1 else (6 if t.reps == 2 else round(t.intervalo_dias * t.ease) or 6)
    t.ultima_q = q
    from datetime import timedelta

    t.proxima_repaso = date.today() + timedelta(days=t.intervalo_dias)
    await db.commit()
    return {"ok": True, "intervalo_dias": t.intervalo_dias, "ease": round(t.ease, 2),
            "proxima_repaso": t.proxima_repaso.isoformat()}


# ---------------------------------------------------------------- quizzes


class QuizBody(BaseModel):
    n: int = 10
    tipo: str = "quiz"  # quiz | simulacro
    duracion_min: int = 0


@router.post("/quizzes")
async def crear_quiz(body: QuizBody, db: AsyncSession = Depends(get_db)):
    quiz = Quiz(
        titulo="Generando…", tipo=body.tipo if body.tipo in ("quiz", "simulacro") else "quiz",
        estado="pendiente", duracion_min=body.duracion_min,
    )
    db.add(quiz)
    await db.flush()
    await db.commit()
    job_id = await encolar("generar_quiz", quiz.id, min(max(body.n, 3), 25), quiz.tipo)
    if not job_id:
        raise HTTPException(503, "Worker no disponible")
    return {"ok": True, "quiz_id": quiz.id}


@router.get("/quizzes")
async def listar_quizzes(db: AsyncSession = Depends(get_db)):
    quizzes = (await db.execute(select(Quiz).order_by(Quiz.creado_en.desc()).limit(100))).scalars().all()
    salida = []
    for q in quizzes:
        n = (await db.execute(select(func.count()).select_from(Pregunta).where(Pregunta.quiz_id == q.id))).scalar() or 0
        salida.append(
            {"id": q.id, "titulo": q.titulo, "tipo": q.tipo, "estado": q.estado, "error": q.error,
             "preguntas": n, "creado_en": q.creado_en.isoformat()}
        )
    return salida


@router.get("/quizzes/{quiz_id}")
async def detalle_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)):
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "Quiz no existe")
    preguntas = (
        await db.execute(select(Pregunta).where(Pregunta.quiz_id == quiz_id).order_by(Pregunta.n))
    ).scalars().all()
    return {
        "id": quiz.id, "titulo": quiz.titulo, "tipo": quiz.tipo, "estado": quiz.estado,
        "error": quiz.error, "duracion_min": quiz.duracion_min,
        "preguntas": [
            {
                "id": p.id, "n": p.n, "enunciado": p.enunciado, "alternativas": p.alternativas,
                "correcta": p.correcta, "explicacion": p.explicacion, "cita": p.cita,
            }
            for p in preguntas
        ],
    }


class RespuestasBody(BaseModel):
    respuestas: list[dict]  # [{pregunta_id, elegida}]


@router.post("/quizzes/{quiz_id}/intentos")
async def responder(quiz_id: str, body: RespuestasBody, db: AsyncSession = Depends(get_db)):
    preguntas = (
        await db.execute(select(Pregunta).where(Pregunta.quiz_id == quiz_id))
    ).scalars().all()
    if not preguntas:
        raise HTTPException(404, "Quiz sin preguntas")
    correctas = {p.id: p.correcta for p in preguntas}
    mapa = {r["pregunta_id"]: int(r["elegida"]) for r in body.respuestas}
    aciertos = sum(1 for pid, correcta in correctas.items() if mapa.get(pid) == correcta)
    puntaje = round(100 * aciertos / len(preguntas), 1)
    db.add(Intento(quiz_id=quiz_id, respuestas=body.respuestas, puntaje=puntaje))
    await db.commit()
    return {"ok": True, "aciertos": aciertos, "total": len(preguntas), "puntaje": puntaje}
