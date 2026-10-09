"""Embeddings multilingües (fastembed ONNX, CPU). Singleton con caché en volumen.

Modelo default: intfloat/multilingual-e5-large (1024 dims, ES/EN).
fastembed añade los prefijos query:/passage: de la familia e5 por sí mismo:
usar embedir_passages() para documentos y embedir_query() para preguntas.
"""

from __future__ import annotations

import gc
import logging
import threading
import time

from fastembed import TextEmbedding

from estudio.config import get_settings

log = logging.getLogger("estudio.embeddings")
_modelo: TextEmbedding | None = None
_lock = threading.Lock()
_ultimo_uso: float = 0.0


def _get() -> TextEmbedding:
    global _modelo, _ultimo_uso
    if _modelo is None:
        with _lock:
            if _modelo is None:
                s = get_settings()
                log.info("Cargando modelo de embeddings %s (caché %s)", s.embed_model, s.modelos_dir)
                _modelo = TextEmbedding(model_name=s.embed_model, cache_dir=s.modelos_dir)
    _ultimo_uso = time.monotonic()
    return _modelo


def descargar_si_inactivo(max_inactivo_s: float = 1200) -> bool:
    """Libera el modelo (~1.4 GB de RAM) si no se usa hace un rato.

    El worker-urgente solo genera un tip al día: mantener e5-large caliente
    24/7 para eso es un derroche que además presiona la RAM del host (v. Bonsai
    exit 137). Lo llama el cron del urgente cada 15 min; si luego hace falta,
    se recarga solo (frío ≈ 2 min).
    """
    global _modelo
    with _lock:
        if _modelo is None or (time.monotonic() - _ultimo_uso) < max_inactivo_s:
            return False
        _modelo = None
    gc.collect()
    log.info("Modelo de embeddings descargado por inactividad (RAM liberada)")
    return True


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
