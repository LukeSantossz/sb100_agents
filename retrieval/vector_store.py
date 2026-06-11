"""Vector search in Qdrant.

Retrieves text chunks semantically similar to the query using
approximate nearest neighbor (ANN) search in Qdrant.

Uses a thread-safe ``QdrantClient`` singleton (avoids opening TCP/HTTP per
query) and validates the embedding dimension before the call.
"""

import logging
import threading

from qdrant_client import QdrantClient

from core.config import settings

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 768

_qdrant_client: QdrantClient | None = None
_qdrant_lock = threading.Lock()


def _get_client() -> QdrantClient:
    """Returns the ``QdrantClient`` singleton (thread-safe lazy init).

    Uses double-checked locking to minimize contention after the first
    access. Reset (for tests) must clear the module-level ``_qdrant_client``.
    """
    global _qdrant_client
    if _qdrant_client is None:
        with _qdrant_lock:
            if _qdrant_client is None:
                _qdrant_client = QdrantClient(
                    url=settings.qdrant_url, api_key=settings.qdrant_api_key
                )
    return _qdrant_client


def search_context(embedding: list[float]) -> list[str]:
    """Retrieves text chunks similar to the query vector.

    Runs ANN (Approximate Nearest Neighbors) search on the configured Qdrant
    collection and returns the texts of the top_k most similar results.

    Args:
        embedding: Query embedding vector (768 dimensions).

    Returns:
        List of strings with the text of each retrieved chunk.
        Returns an empty list if no results are found.

    Raises:
        ValueError: If the embedding does not have exactly 768 dimensions.
        qdrant_client.http.exceptions.UnexpectedResponse: If the collection does not exist.
        requests.exceptions.ConnectionError: If Qdrant is offline.
    """
    if len(embedding) != _EMBEDDING_DIM:
        raise ValueError(f"embedding must have {_EMBEDDING_DIM} dimensions; got {len(embedding)}")

    client = _get_client()
    results = client.query_points(
        collection_name=settings.collection_name,
        query=embedding,
        limit=settings.top_k,
        with_payload=True,
    ).points

    chunks: list[str] = []
    for point in results:
        payload = point.payload or {}
        text = payload.get("text")
        if not text:
            logger.warning(
                "vector_store.empty_or_missing_text",
                extra={"payload_keys": sorted(payload.keys())},
            )
            chunks.append("")
        else:
            chunks.append(str(text))
    return chunks
