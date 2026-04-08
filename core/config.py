from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais do sistema"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    chat_model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "archives_v2"
    top_k: int = 3
    hallucination_threshold: float = 0.5
    verification_enabled: bool = True
    openai_api_key: str = ""


settings = Settings()
