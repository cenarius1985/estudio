"""Cliente del LLM local Bonsai (Ternary-Bonsai-2-27B vía llama-server,
API OpenAI-compatible — patrón whispertext rama gpu) con fallback opcional.

Todo es fail-soft: chat() devuelve None si ningún endpoint responde;
chat_stream() lanza LLMNoDisponible para que el llamante decida.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from estudio.config import get_settings

log = logging.getLogger("estudio.llm")

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMNoDisponible(Exception):
    pass


def _endpoints() -> list[str]:
    s = get_settings()
    eps = [s.llm_base_url.rstrip("/")]
    if s.llm_fallback_url:
        eps.append(s.llm_fallback_url.rstrip("/"))
    return eps


def _payload_base(temperature: float, max_tokens: int, json_mode: bool) -> dict[str, Any]:
    s = get_settings()
    p: dict[str, Any] = {
        "model": s.llm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        p["response_format"] = {"type": "json_object"}
    return p


async def chat(
    mensajes: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 900,
    json_mode: bool = False,
) -> str | None:
    """Respuesta completa (str) o None si ningún endpoint responde."""
    s = get_settings()
    for ep in _endpoints():
        try:
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as cliente:
                resp = await cliente.post(
                    f"{ep}/chat/completions",
                    json={"messages": mensajes, **_payload_base(temperature, max_tokens, json_mode)},
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip() or None
        except Exception as exc:  # noqa: BLE001 — fail-soft es el contrato
            log.warning("LLM %s falló: %s", ep, exc)
    return None


async def chat_stream(
    mensajes: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 900,
) -> AsyncIterator[str]:
    """Stream de deltas de texto. Si todos los endpoints fallan → LLMNoDisponible."""
    s = get_settings()
    errores: list[str] = []
    for ep in _endpoints():
        try:
            cliente = httpx.AsyncClient(timeout=s.llm_timeout_s)
            async with cliente.stream(
                "POST",
                f"{ep}/chat/completions",
                json={
                    "messages": mensajes,
                    **_payload_base(temperature, max_tokens, False),
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for linea in resp.aiter_lines():
                    if not linea.startswith("data:"):
                        continue
                    dato = linea[5:].strip()
                    if dato == "[DONE]":
                        break
                    try:
                        delta = json.loads(dato)["choices"][0]["delta"].get("content")
                    except (ValueError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta
            await cliente.aclose()
            return
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{ep}: {exc}")
            log.warning("LLM stream %s falló: %s", ep, exc)
            try:
                await cliente.aclose()
            except Exception:  # noqa: BLE001
                pass
    raise LLMNoDisponible("Sin LLM disponible → " + " | ".join(errores))


async def ping() -> dict:
    """Estado de cada endpoint (para el panel)."""
    s = get_settings()
    estado = {}
    for ep in _endpoints():
        try:
            async with httpx.AsyncClient(timeout=5) as cliente:
                r = await cliente.get(f"{ep}/models")
                estado[ep] = "ok" if r.status_code == 200 else f"http {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            estado[ep] = f"no disponible ({type(exc).__name__})"
    estado["modelo"] = s.llm_model
    return estado


def extraer_json(raw: str | None) -> dict | None:
    """Extrae el primer objeto JSON de una respuesta del LLM."""
    if not raw:
        return None
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None
