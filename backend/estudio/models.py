"""Modelos SQLAlchemy. Embeddings en pgvector; FTS por columna tsvector generada."""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------- temas


class Tema(Base):
    """Tema/materia de estudio: agrupa documentos, tips, chat y estudio."""

    __tablename__ = "temas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    # carpeta de primer nivel en fuentes/ que corresponde a este tema
    # (fuentes/<slug>/…): la estructura ES la clasificación
    slug: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(9), default="#2c5282")
    # Prefijos de carpeta (coma-separados) para auto-clasificar el escaneo
    carpetas: Mapped[str] = mapped_column(Text, default="")
    # Prefijos con PRIORIDAD para sembrar tips/preguntas (el core del tema;
    # vacío = todo el tema pesa igual)
    prioridades: Mapped[str] = mapped_column(Text, default="")
    # Perfil de nivel/temario inyectado en los prompts (tips, decks, quizzes, chat)
    enfoque: Mapped[str] = mapped_column(Text, default="")
    tips_activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- documentos


class Documento(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    ruta: Mapped[str] = mapped_column(Text)  # relativa a la fuente o nombre del upload
    fuente: Mapped[str] = mapped_column(String(16), default="montada")  # montada|upload|url
    tipo: Mapped[str] = mapped_column(String(16), default="txt")
    titulo: Mapped[str] = mapped_column(Text, default="")
    hash: Mapped[str] = mapped_column(String(64), index=True)
    estado: Mapped[str] = mapped_column(String(16), default="pendiente")
    error: Mapped[str] = mapped_column(Text, default="")
    bytes_n: Mapped[int] = mapped_column(Integer, default=0)
    chunks_n: Mapped[int] = mapped_column(Integer, default=0)
    tema_id: Mapped[str | None] = mapped_column(
        ForeignKey("temas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    indexado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    n: Mapped[int] = mapped_column(Integer, default=0)
    pagina: Mapped[str] = mapped_column(Text, default="")  # "12" | "hoja Resultados" | "cap. 3"
    texto: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1024))

    # tsv tsvector GENERADO — ver estudio.db._DDL (BM25)


# ---------------------------------------------------------------- grafo


class Nodo(Base):
    __tablename__ = "nodos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(64), default="concepto")


class Arista(Base):
    __tablename__ = "aristas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nodo_a: Mapped[int] = mapped_column(ForeignKey("nodos.id", ondelete="CASCADE"), index=True)
    nodo_b: Mapped[int] = mapped_column(ForeignKey("nodos.id", ondelete="CASCADE"), index=True)
    relacion: Mapped[str] = mapped_column(String(100), default="coocurre")
    chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )


# ---------------------------------------------------------------- tips


class Tip(Base):
    __tablename__ = "tips"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    titulo: Mapped[str] = mapped_column(Text, default="")
    cuerpo_texto: Mapped[str] = mapped_column(Text, default="")
    cuerpo_html: Mapped[str] = mapped_column(Text, default="")
    embedding = mapped_column(Vector(1024))
    tema_id: Mapped[str | None] = mapped_column(
        ForeignKey("temas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(16), default="generado")
    # generado | enviado | duplicado | error
    duplicado_de: Mapped[str | None] = mapped_column(
        ForeignKey("tips.id", ondelete="SET NULL"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TipChunk(Base):
    """Cobertura: qué chunks alimentaron cada tip (para elegir temas poco cubiertos)."""

    __tablename__ = "tips_chunks"

    tip_id: Mapped[str] = mapped_column(ForeignKey("tips.id", ondelete="CASCADE"), primary_key=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)
    es_semilla: Mapped[bool] = mapped_column(default=False)


class TipEnvio(Base):
    __tablename__ = "tips_envios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tip_id: Mapped[str] = mapped_column(ForeignKey("tips.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    estado: Mapped[str] = mapped_column(String(8), default="ok")  # ok | error
    error: Mapped[str] = mapped_column(Text, default="")
    enviado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- estudio (Astra-like)


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    titulo: Mapped[str] = mapped_column(Text, default="")
    documento_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    tema_id: Mapped[str | None] = mapped_column(
        ForeignKey("temas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(16), default="pendiente")  # pendiente|listo|error
    error: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), index=True)
    frente: Mapped[str] = mapped_column(Text)
    reverso: Mapped[str] = mapped_column(Text)
    cita: Mapped[dict] = mapped_column(JSON, default=dict)  # {archivo, pagina}
    # SM-2 lite
    reps: Mapped[int] = mapped_column(Integer, default=0)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    intervalo_dias: Mapped[int] = mapped_column(Integer, default=0)
    proxima_repaso: Mapped[date] = mapped_column(Date, index=True)
    ultima_q: Mapped[int] = mapped_column(Integer, default=0)


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    titulo: Mapped[str] = mapped_column(Text, default="")
    tipo: Mapped[str] = mapped_column(String(16), default="quiz")  # quiz | simulacro
    tema_id: Mapped[str | None] = mapped_column(
        ForeignKey("temas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(16), default="pendiente")
    duracion_min: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Pregunta(Base):
    __tablename__ = "preguntas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    enunciado: Mapped[str] = mapped_column(Text)
    alternativas: Mapped[list] = mapped_column(JSON, default=list)
    correcta: Mapped[int] = mapped_column(Integer, default=0)
    explicacion: Mapped[str] = mapped_column(Text, default="")
    cita: Mapped[dict] = mapped_column(JSON, default=dict)


class Intento(Base):
    __tablename__ = "intentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    respuestas: Mapped[list] = mapped_column(JSON, default=list)  # [{pregunta_id, elegida}]
    puntaje: Mapped[float] = mapped_column(Float, default=0.0)
    terminado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- chat


class Conversacion(Base):
    __tablename__ = "conversaciones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    titulo: Mapped[str] = mapped_column(Text, default="")
    tema_id: Mapped[str | None] = mapped_column(
        ForeignKey("temas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Mensaje(Base):
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversacion_id: Mapped[str] = mapped_column(
        ForeignKey("conversaciones.id", ondelete="CASCADE"), index=True
    )
    rol: Mapped[str] = mapped_column(String(12))  # user | assistant
    contenido: Mapped[str] = mapped_column(Text)
    fuentes: Mapped[list] = mapped_column(JSON, default=list)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- ajustes


class Setting(Base):
    __tablename__ = "settings"

    k: Mapped[str] = mapped_column(String(64), primary_key=True)
    v: Mapped[str] = mapped_column(Text, default="")
