"""SmartB100 system settings via Pydantic Settings.

This module loads settings from environment variables (.env file)
and provides sensible defaults for local development.

Validations enforce numeric bounds, an enum for the provider and
optional API keys as ``str | None``.

Usage example:
    from core.config import settings
    print(settings.chat_model)  # "llama3.2:3b"
"""

from enum import StrEnum

from limits import parse_many
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VerificationProvider(StrEnum):
    """Supported providers for entropy-based hallucination verification."""

    groq = "groq"
    ollama = "ollama"
    openrouter = "openrouter"


class AgentProvider(StrEnum):
    """Supported chat-model providers for the deep agent (ADR-0009 and the local-provider ADR)."""

    groq = "groq"
    ollama = "ollama"


# Provider-appropriate default agent models, applied when ``agent_model`` is left empty so a
# deployment that only sets ``agent_provider`` gets a valid model for that provider.
_DEFAULT_OLLAMA_AGENT_MODEL = "qwen2.5:7b"
_DEFAULT_GROQ_AGENT_MODEL = "openai/gpt-oss-20b"


class Settings(BaseSettings):
    """Global SmartB100 system settings.

    Loads values from environment variables with fallback to defaults.
    The .env file at the project root is read automatically.

    Enforced bounds:
        - ``top_k``: 1..100
        - ``buffer_maxlen``: 1..100
        - ``llm_max_tokens``: 1..4096
        - ``hallucination_threshold``: 0.0..1.0
        - ``entropy_num_samples``: >=2
        - ``verification_provider``: ``groq | ollama | openrouter``
        - ``jwt_secret_key``: required, length >= 32
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    ollama_timeout: float = Field(default=240.0, ge=1.0, le=600.0)
    ollama_embed_timeout: float = Field(default=5.0, ge=1.0, le=120.0)
    chat_timeout: float = Field(default=600.0, ge=1.0, le=3600.0)
    # slowapi limit string enforced per authenticated user on POST /chat.
    chat_rate_limit: str = "30/minute"
    groq_api_key: str | None = None
    agent_provider: AgentProvider = AgentProvider.ollama
    agent_model: str = ""  # Empty = use the provider default (see _apply_agent_model_default)
    agent_enabled: bool = False
    agent_recursion_limit: int = Field(default=25, ge=1, le=100)
    agent_token_budget: int = Field(default=100_000, ge=1)
    # Local (Ollama) context window for the agent. Must exceed the ~9.8k-token deep-agent
    # prompt (deepagents scaffolding) so the system/tool prompt is not truncated; only used
    # when agent_provider is ollama.
    agent_num_ctx: int = Field(default=16384, ge=2048, le=131072)
    intent_filter_enabled: bool = True
    intent_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    openrouter_api_key: str | None = None
    jwt_secret_key: str = ""

    @field_validator("chat_rate_limit")
    @classmethod
    def _validate_chat_rate_limit(cls, value: str) -> str:
        """Reject an empty or malformed rate-limit string at startup.

        slowapi parses this lazily on the first request, so an invalid
        ``CHAT_RATE_LIMIT`` would otherwise surface as a 500 on every ``/chat``
        call instead of a fail-loud boot error. Validating the slowapi format
        here (via the same ``limits`` parser slowapi uses) catches it early.
        """
        try:
            parse_many(value)
        except ValueError as exc:
            raise ValueError(
                f"CHAT_RATE_LIMIT must be a slowapi limit string like '30/minute' (got {value!r})"
            ) from exc
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret_key(cls, value: str) -> str:
        """Ensure the JWT secret exists and has minimum entropy."""
        if not value:
            raise ValueError("JWT_SECRET_KEY must be configured in .env or environment variables")
        if len(value) < 32:
            raise ValueError(f"JWT_SECRET_KEY must be at least 32 characters (got {len(value)})")
        return value

    @model_validator(mode="after")
    def _apply_agent_model_default(self) -> "Settings":
        """Fill an empty ``agent_model`` with the default model for the selected provider.

        Keeps the two settings consistent: setting only ``AGENT_PROVIDER=groq`` must not leave the
        Ollama default model in place (``ChatGroq`` would reject it). An explicit ``AGENT_MODEL``
        always wins.
        """
        if not self.agent_model:
            self.agent_model = (
                _DEFAULT_OLLAMA_AGENT_MODEL
                if self.agent_provider == AgentProvider.ollama
                else _DEFAULT_GROQ_AGENT_MODEL
            )
        return self


settings = Settings()
