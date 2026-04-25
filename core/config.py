"""Configurações do sistema SmartB100 via Pydantic Settings.

Este módulo carrega configurações de variáveis de ambiente (arquivo .env)
e fornece defaults sensatos para desenvolvimento local.

Exemplo de uso:
    from core.config import settings
    print(settings.chat_model)  # "llama3.2:3b"
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais do sistema SmartB100.

    Carrega valores de variáveis de ambiente com fallback para defaults.
    O arquivo .env na raiz do projeto é lido automaticamente.

    Attributes:
        chat_model: Modelo Ollama para geração de respostas.
        embed_model: Modelo Ollama para geração de embeddings.
        qdrant_url: URL do servidor Qdrant para busca vetorial.
        collection_name: Nome da coleção no Qdrant.
        top_k: Número de chunks retornados na busca por similaridade.
        buffer_maxlen: Tamanho máximo do buffer de conversação.
        hallucination_threshold: Limiar de entropia para detecção de alucinação.
        verification_enabled: Habilita verificação de alucinações via entropia.
        openai_api_key: Chave da API OpenAI (para verificação de alucinações).
        groq_api_key: Chave da API Groq (para pipeline de avaliação).
        openrouter_api_key: Chave da API OpenRouter (para pipeline de avaliação).
        jwt_secret_key: Segredo para assinatura de tokens JWT.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    chat_model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "archives_v2"
    top_k: int = 3
    buffer_maxlen: int = 10
    hallucination_threshold: float = 0.5
    verification_enabled: bool = True
    openai_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    jwt_secret_key: str = ""


settings = Settings()
