"""Configurações do sistema SmartB100 via Pydantic Settings.

Este módulo carrega configurações de variáveis de ambiente (arquivo .env)
e fornece defaults sensatos para desenvolvimento local.

Validações (TASK-T62) garantem bounds numéricos, enum para provider e
API keys opcionais como ``str | None``.

Exemplo de uso:
    from core.config import settings
    print(settings.chat_model)  # "llama3.2:3b"
"""

from enum import StrEnum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VerificationProvider(StrEnum):
    """Provedores suportados para verificação de alucinação por entropia."""

    groq = "groq"
    ollama = "ollama"
    openrouter = "openrouter"


class Settings(BaseSettings):
    """Configurações globais do sistema SmartB100.

    Carrega valores de variáveis de ambiente com fallback para defaults.
    O arquivo .env na raiz do projeto é lido automaticamente.

    Bounds aplicados (regra 04.2 / TASK-T62):
        - ``top_k``: 1..100
        - ``buffer_maxlen``: 1..100
        - ``llm_max_tokens``: 1..4096
        - ``hallucination_threshold``: 0.0..1.0
        - ``entropy_num_samples``: >=2
        - ``verification_provider``: ``groq | ollama | openrouter``
        - ``jwt_secret_key``: obrigatório, comprimento >= 32
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # GPU: ~10-30s | CPU-only: ~160-200s (llama3.2:3b) per response
    chat_model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    collection_name: str = "archives_v2"
    top_k: int = Field(default=3, ge=1, le=100)
    buffer_maxlen: int = Field(default=10, ge=1, le=100)
    llm_max_tokens: int = Field(default=256, ge=1, le=4096)
    hallucination_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_enabled: bool = True
    verification_provider: VerificationProvider = VerificationProvider.groq
    verification_chat_model: str = ""  # Empty = use provider default
    entropy_num_samples: int = Field(default=2, ge=2)
    entropy_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    jwt_secret_key: str = ""

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret_key(cls, value: str) -> str:
        """Garante que o segredo do JWT existe e tem entropia mínima."""
        if not value:
            raise ValueError("JWT_SECRET_KEY must be configured in .env or environment variables")
        if len(value) < 32:
            raise ValueError(f"JWT_SECRET_KEY must be at least 32 characters (got {len(value)})")
        return value


settings = Settings()
