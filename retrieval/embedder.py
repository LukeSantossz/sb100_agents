"""Embedding generation via Ollama.

Uses the model configured in settings.embed_model (default: nomic-embed-text)
to convert text into 768-dimension dense vectors.
"""

import logging

from core.config import settings
from retrieval.ollama_embeddings import embed_text

logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> list[float]:
    """Generates a dense embedding vector for the given text.

    Uses the embedding model configured in settings (default: nomic-embed-text)
    via the local Ollama API.

    Args:
        text: Text to convert into an embedding.

    Returns:
        List of floats representing the embedding vector (768 dimensions).

    Raises:
        Exception: Last failure returned by Ollama after exhausting retries
            (e.g. missing model).
    """
    logger.debug("embedder.generate", extra={"chars": len(text)})
    return embed_text(settings.embed_model, text)
