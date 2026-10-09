"""Catálogo de proveedores LLM (patrón de PROYECTO-INFORMATICO/core/api_llm).

Todos los proveedores de pago exponen API compatible con OpenAI
(/chat/completions con Bearer key), así que el cliente genérico de
estudio.llm.bonsai los cubre sin código nuevo por proveedor. El catálogo
solo alimenta los presets del panel (endpoint, modelo sugerido y dónde
conseguir la API key).
"""

PROVEEDORES: list[dict] = [
    {
        "id": "local",
        "nombre": "Local — Bonsai (docker, perfil gpu)",
        "base_url": "http://bonsai:8080/v1",
        "model": "ternary-bonsai-2-27b",
        "requiere_api_key": False,
        "url_key": None,
    },
    {
        "id": "ollama",
        "nombre": "Local — Ollama",
        "base_url": "http://host.docker.internal:11434/v1",
        "model": "qwen2.5:7b",
        "requiere_api_key": False,
        "url_key": None,
    },
    {
        "id": "openai",
        "nombre": "OpenAI (de pago)",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "requiere_api_key": True,
        "url_key": "https://platform.openai.com/api-keys",
    },
    {
        "id": "deepseek",
        "nombre": "DeepSeek (de pago, económico)",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "requiere_api_key": True,
        "url_key": "https://platform.deepseek.com/api_keys",
    },
    {
        "id": "moonshot",
        "nombre": "Moonshot · Kimi (de pago)",
        "base_url": "https://api.moonshot.ai/v1",
        "model": "kimi-k2-0905-preview",
        "requiere_api_key": True,
        "url_key": "https://platform.moonshot.ai/console/api-keys",
    },
    {
        "id": "gemini",
        "nombre": "Google Gemini (endpoint OpenAI-compatible)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "requiere_api_key": True,
        "url_key": "https://aistudio.google.com/app/apikey",
    },
    {
        "id": "claude",
        "nombre": "Anthropic Claude (endpoint OpenAI-compatible)",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-sonnet-4-5",
        "requiere_api_key": True,
        "url_key": "https://console.anthropic.com/settings/keys",
    },
    {
        "id": "groq",
        "nombre": "Groq (de pago, muy rápido)",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "requiere_api_key": True,
        "url_key": "https://console.groq.com/keys",
    },
    {
        "id": "openrouter",
        "nombre": "OpenRouter (miles de modelos con una key)",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "requiere_api_key": True,
        "url_key": "https://openrouter.ai/settings/keys",
    },
    {
        "id": "custom",
        "nombre": "Personalizado (cualquier API OpenAI-compatible)",
        "base_url": "",
        "model": "",
        "requiere_api_key": True,
        "url_key": None,
    },
]
