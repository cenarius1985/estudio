"""Chunker: agrupa bloques consecutivos en chunks de ~max_chars con overlap."""

from __future__ import annotations

from estudio.ingest.extractores import Bloque

MAX_CHARS = 4000   # ≈ 1000 tokens
OVERLAY_CHARS = 600  # ≈ 15%


def chunkear(bloques: list[Bloque], max_chars: int = MAX_CHARS, overlap: int = OVERLAY_CHARS) -> list[Bloque]:
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
