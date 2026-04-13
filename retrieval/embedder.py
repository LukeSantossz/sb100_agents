import ollama

from core.config import settings


def generate_embedding(text: str) -> list[float]:
    """Retorna o vetor de embedding denso para o texto, usando o modelo configurado."""
    response = ollama.embeddings(model=settings.embed_model, prompt=text)
    return response["embedding"]
