"""Embeddings multilingües (fastembed ONNX, CPU). Singleton con caché en volumen.

Modelo default: intfloat/multilingual-e5-large (1024 dims, ES/EN).
fastembed añade los prefijos query:/passage: de la familia e5 por sí mismo:
usar embedir_passages() para documentos y embedir_query() para preguntas.
"""

from __future__ import annotations

import logging
import threading

from fastembed import TextEmbedding

from estudio.config import get_settings

log = logging.getLogger("estudio.embeddings")
_modelo: TextEmbedding | None = None
_lock = threading.Lock()


def _get() -> TextEmbedding:
    global _modelo
    if _modelo is None:
        with _lock:
            if _modelo is None:
                s = get_settings()
                log.info("Cargando modelo de embeddings %s (caché %s)", s.embed_model, s.modelos_dir)
                _modelo = TextEmbedding(model_name=s.embed_model, cache_dir=s.modelos_dir)
    return _modelo


def embedir_passages(textos: list[str]) -> list[list[float]]:
    if not textos:
        return []
    m = _get()
    # truncado defensivo: e5 soporta 512 tokens ≈ 2000-3000 chars
    trozados = [t[:3000] for t in textos]
    return [[float(x) for x in vec] for vec in m.embed(trozados, batch_size=16)]


def embedir_query(pregunta: str) -> list[float]:
    m = _get()
    return [float(x) for x in next(iter(m.query_embed([pregunta[:2000]])))]


def vector_a_pg(vec: list[float]) -> str:
    """Representación literal para bind de pgvector (… ::vector)."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
