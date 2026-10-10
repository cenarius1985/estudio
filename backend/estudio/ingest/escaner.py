"""Escaneo incremental de la carpeta de fuentes (hash SHA256 por archivo)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from estudio.ingest.extractores import tipo_de


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def escanear(raiz: Path, excludes: list[str], max_bytes: int) -> list[dict]:
    """Archivos indexables bajo raíz. Cada dict: ruta, tipo, bytes, absoluta.

    Además de los directorios excluidos, se descartan archivos basura de
    compilación: logs LaTeX, auxiliares y artefactos sin contenido técnico
    (contaminan el RAG con miles de chunks de ruido).
    """
    excluye_nombre = {
        "compilation_log.txt", "main.log", "main.bcf", "main.run.xml",
        "main.snm", "main.toc", "main.nav", "main.out", "main.aux",
        "main.bbl", "main.blg", "guion_bilingue.log",
    }
    excluye_sufijo = (".log", ".aux", ".bbl", ".blg", ".out", ".synctex.gz")
    encontrados: list[dict] = []
    if not raiz.is_dir():
        return encontrados
    for p in sorted(raiz.rglob("*")):
        try:
            if not p.is_file():
                continue
            rel = p.relative_to(raiz)
            if any(part in excludes for part in rel.parts):
                continue
            if p.name in excluye_nombre or p.name.endswith(excluye_sufijo):
                continue
            tipo = tipo_de(p)
            if tipo is None:
                continue
            size = p.stat().st_size
            if size == 0 or size > max_bytes:
                continue
            encontrados.append(
                {"ruta": rel.as_posix(), "tipo": tipo, "bytes": size, "absoluta": str(p)}
            )
        except OSError:
            continue  # archivos bloqueados / permisos
    return encontrados
