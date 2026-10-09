"""Ingesta de páginas web (URLs como fuente de información).

Descarga con httpx y convierte HTML a texto plano (stdlib, sin dependencias
extra). Las páginas que requieren JavaScript pueden extraer poco texto.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass

import httpx

from estudio.ingest.extractores import Bloque, IngestaError

MAX_BYTES = 3_000_000
UA = "Mozilla/5.0 (compatible; EstudioBot/1.0; +self-hosted study platform)"
_TIMEOUT = httpx.Timeout(30.0)


@dataclass
class Pagina:
    url_final: str
    titulo: str
    bloques: list[Bloque]


def _decodificar(resp: httpx.Response) -> str:
    contenido = resp.content[:MAX_BYTES]
    try:
        return contenido.decode("utf-8")
    except UnicodeDecodeError:
        m = re.search(rb'charset=["\']?([\w-]+)', contenido[:2048], re.IGNORECASE)
        if m:
            try:
                return contenido.decode(m.group(1).decode())
            except (LookupError, UnicodeDecodeError):
                pass
        return contenido.decode("latin-1", errors="replace")


def html_a_bloques(html_texto: str) -> tuple[str, list[Bloque]]:
    """(titulo, bloques) desde HTML plano."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html_texto, re.IGNORECASE | re.DOTALL)
    titulo = html_lib.unescape(m.group(1)).strip() if m else ""

    texto = re.sub(r"(?is)<(script|style|nav|footer|header|aside|noscript)[^>]*>.*?</\1>", " ", html_texto)
    texto = re.sub(r"(?i)<br\s*/?>", "\n", texto)
    texto = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article|blockquote)>", "\n\n", texto)
    texto = re.sub(r"(?i)<li[^>]*>", "\n- ", texto)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html_lib.unescape(texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    parrafos = [p.strip() for p in texto.split("\n\n") if len(p.strip()) > 40]
    if not parrafos:
        raise IngestaError("La página no tiene texto extraíble (¿requiere JavaScript?)")
    return titulo, [Bloque(p, "web") for p in parrafos]


async def descargar_pagina(url: str) -> Pagina:
    """Descarga una URL y la convierte en bloques indexables."""
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=_TIMEOUT, headers={"User-Agent": UA}
    ) as cliente:
        resp = await cliente.get(url)
        resp.raise_for_status()
        tipo = (resp.headers.get("content-type") or "").lower()
        cuerpo = _decodificar(resp)

    if "html" in tipo:
        titulo, bloques = html_a_bloques(cuerpo)
    elif any(t in tipo for t in ("text/", "json", "xml", "markdown")):
        titulo = url.rsplit("/", 1)[-1][:120]
        parrafos = [p.strip() for p in cuerpo.split("\n\n") if len(p.strip()) > 40]
        if not parrafos:
            raise IngestaError("Contenido de texto vacío")
        bloques = [Bloque(p, "web") for p in parrafos]
    else:
        raise IngestaError(f"Tipo no soportado: {tipo or 'desconocido'}")

    return Pagina(url_final=str(resp.url), titulo=titulo or url[:120], bloques=bloques)
