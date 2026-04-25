"""Geração de embeddings via Ollama.

Utiliza o modelo configurado em settings.embed_model (default: nomic-embed-text)
para converter texto em vetores densos de 768 dimensões.
"""

import ollama

from core.config import settings


def generate_embedding(text: str) -> list[float]:
    """Gera vetor de embedding denso para o texto fornecido.

    Utiliza o modelo de embedding configurado em settings (default: nomic-embed-text)
    via API local do Ollama.

    Args:
        text: Texto a ser convertido em embedding.

    Returns:
        Lista de floats representando o vetor de embedding (768 dimensões).

    Raises:
        ollama.ResponseError: Se o modelo não estiver disponível ou Ollama offline.
    """
    response = ollama.embeddings(model=settings.embed_model, prompt=text)
    embedding: list[float] = response["embedding"]
    return embedding
