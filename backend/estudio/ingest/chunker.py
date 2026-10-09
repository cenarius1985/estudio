"""Chunker: agrupa bloques consecutivos en chunks de ~max_chars con overlap.
Sanitiza el texto (NUL y controles): Postgres TEXT no admite \\x00 y algunos
PDFs/LaTeX lo arrastran — sin esto el INSERT del chunk revienta la ingesta."""

from __future__ import annotations

import re

from estudio.ingest.extractores import Bloque

MAX_CHARS = 4000   # ≈ 1000 tokens
OVERLAY_CHARS = 600  # ≈ 15%

# todo control salvo \n \t (el \r se normaliza)
_CONTROLES = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitizar(texto: str) -> str:
    return _CONTROLES.sub("", texto.replace("\r\n", "\n").replace("\r", "\n"))


def chunkear(bloques: list[Bloque], max_chars: int = MAX_CHARS, overlap: int = OVERLAY_CHARS) -> list[Bloque]:
    limpios: list[Bloque] = []
    for b in bloques:
        t = sanitizar(b.texto)
        if t.strip():
            limpios.append(Bloque(t, sanitizar(b.pagina)))
    bloques = limpios

    chunks: list[Bloque] = []
    actual: list[Bloque] = []
    actual_len = 0

    def _paginas(partes: list[Bloque]) -> str:
        vistos: list[str] = []
        for b in partes:
            for p in b.pagina.split("+"):
                if p and p not in vistos:
                    vistos.append(p)
        return "+".join(vistos[:6])

    for b in bloques:
        if actual and actual_len + len(b.texto) > max_chars:
            chunks.append(Bloque("\n\n".join(x.texto for x in actual), _paginas(actual)))
            # overlap: el último bloque pequeño del chunk anterior encabeza el siguiente
            cola = actual[-1] if len(actual[-1].texto) <= overlap else None
            actual = [cola] if cola else []
            actual_len = len(cola.texto) if cola else 0
        actual.append(b)
        actual_len += len(b.texto)

    if actual:
        texto = "\n\n".join(x.texto for x in actual).strip()
        if texto:
            chunks.append(Bloque(texto, _paginas(actual)))
    return chunks
