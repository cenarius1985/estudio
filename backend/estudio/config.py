"""Configuración central (variables de entorno del docker-compose)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Infraestructura
    database_url: str = "postgresql+asyncpg://estudio:dev@db:5432/estudio"
    redis_url: str = "redis://redis:6379/0"
    ruta_fuentes: str = "/fuentes"
    modelos_dir: str = "/data/modelos"

    # Ingesta
    exclude_dirs: str = ".git,node_modules,__pycache__,.venv,Tensorflowmri,build"
    max_archivo_bytes: int = 209_715_200  # 200 MB

    # Correo (SMTP Brevo — mismos valores que reportesDiariosGes)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""

    # Tips diarios
    tips_to: str = ""           # correos separados por coma
    tips_hora: str = "07:30"    # HH:MM local (America/Santiago)
    tips_umbral_dedupe: float = 0.90
    tips_reintentos: int = 3

    # Panel
    admin_password: str = "cambia-me-admin"
    frontend_url: str = "http://localhost:8601"

    # LLM (Bonsai + fallback OpenAI-compatible)
    llm_base_url: str = "http://bonsai:8080/v1"
    llm_fallback_url: str = ""
    llm_model: str = "ternary-bonsai-2-27b"
    llm_timeout_s: float = 240.0

    # Embeddings (e5-large ⇒ 1024 dimensiones; el esquema fija Vector(1024))
    embed_model: str = "intfloat/multilingual-e5-large"
    embed_dim: int = 1024

    # Recuperación híbrida
    retrieval_k: int = 8
    retrieval_k_vector: int = 30
    retrieval_k_bm25: int = 30

    @property
    def exclude_dirs_list(self) -> list[str]:
        return [d.strip() for d in self.exclude_dirs.split(",") if d.strip()]

    @property
    def tips_to_list(self) -> list[str]:
        return [e.strip() for e in self.tips_to.split(",") if e.strip() and "@" in e]

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass)


@lru_cache
def get_settings() -> Settings:
    return Settings()
