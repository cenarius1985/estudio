"""Cliente LLM (Bonsai local, OpenAI-compatible) — fail-soft con fallback."""

from estudio.llm.bonsai import (
    LLMNoDisponible,
    chat,
    chat_stream,
    extraer_json,
    ping,
)

__all__ = ["LLMNoDisponible", "chat", "chat_stream", "extraer_json", "ping"]
