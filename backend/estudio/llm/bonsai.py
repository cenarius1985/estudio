"""Cliente del LLM (Bonsai u otro endpoint OpenAI-compatible) — fail-soft.

Los endpoints/modelo llegan como cfg dict (resuelto desde BD panel → .env en
estudio.credenciales.config_llm) o, si no, del .env. chat() devuelve None si
ningún endpoint responde; chat_stream() lanza LLMNoDisponible.
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


def _cfg_por_defecto() -> dict:
    s = get_settings()
    return {"base_url": s.llm_base_url, "fallback_url": s.llm_fallback_url, "model": s.llm_model}


def _endpoints(cfg: dict | None) -> list[str]:
    cfg = cfg or _cfg_por_defecto()
    eps = [cfg.get("base_url", "").rstrip("/")]
    if cfg.get("fallback_url"):
        eps.append(cfg["fallback_url"].rstrip("/"))
    return [e for e in eps if e]


def _headers(cfg: dict | None) -> dict[str, str]:
    """Bearer solo si hay API key (proveedores de pago); local va sin auth."""
    cfg = cfg or _cfg_por_defecto()
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = f"Bearer {cfg['api_key']}"
    return h


def _payload_base(cfg: dict | None, temperature: float, max_tokens: int, json_mode: bool) -> dict[str, Any]:
    modelo = (cfg or _cfg_por_defecto()).get("model") or get_settings().llm_model
    p: dict[str, Any] = {"model": modelo, "temperature": temperature, "max_tokens": max_tokens}
    # GLM/ZAI: desactivar razonamiento para respuesta inmediata (razona ~2500 tokens si no)
    if "z.ai" in ((cfg or {}).get("base_url", "") or get_settings().llm_base_url):
        p["thinking"] = {"type": "disabled"}
    if json_mode:
        p["response_format"] = {"type": "json_object"}
    return p


async def chat(
    mensajes: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 3000,
    json_mode: bool = False,
    cfg: dict | None = None,
) -> str | None:
    """Respuesta completa (str) o None si ningún endpoint responde.
    GLM-5/5.3 razona ~1000-2700 tokens antes de escribir: max_tokens >= 3000."""
    s = get_settings()
    for ep in _endpoints(cfg):
        try:
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as cliente:
                resp = await cliente.post(
                    f"{ep}/chat/completions",
                    headers=_headers(cfg),
                    json={"messages": mensajes, **_payload_base(cfg, temperature, max_tokens, json_mode)},
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"].get("content", "")
                return content.strip() or None
        except Exception as exc:  # noqa: BLE001 — fail-soft es el contrato
            log.warning("LLM %s falló: %s", ep, exc)
    return None


async def chat_stream(
    mensajes: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 3000,
    cfg: dict | None = None,
) -> AsyncIterator[str]:
    """Stream de deltas de texto. Si todos los endpoints fallan → LLMNoDisponible."""
    s = get_settings()
    errores: list[str] = []
    for ep in _endpoints(cfg):
        cliente = httpx.AsyncClient(timeout=s.llm_timeout_s)
        try:
            async with cliente.stream(
                "POST",
                f"{ep}/chat/completions",
                headers=_headers(cfg),
                json={
                    "messages": mensajes,
                    **_payload_base(cfg, temperature, max_tokens, False),
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
                        d = json.loads(dato)["choices"][0]["delta"]
                        # GLM-5: razona primero (reasoning_content), luego responde (content)
                        delta = d.get("content")
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


async def ping(cfg: dict | None = None) -> dict:
    """Estado de cada endpoint (para el panel). Con API key también valida
    la autenticación (401/403 ⇒ clave rechazada, no solo «no disponible»)."""
    estado = {}
    for ep in _endpoints(cfg):
        try:
            async with httpx.AsyncClient(timeout=10) as cliente:
                r = await cliente.get(f"{ep}/models", headers=_headers(cfg))
                if r.status_code in (401, 403):
                    estado[ep] = "API key rechazada"
                elif r.status_code == 200:
                    estado[ep] = "ok"
                else:
                    estado[ep] = f"http {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            estado[ep] = f"no disponible ({type(exc).__name__})"
    estado["modelo"] = (cfg or _cfg_por_defecto()).get("model") or "?"
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
