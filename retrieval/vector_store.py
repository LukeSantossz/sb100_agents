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


def search_context_rich(embedding: list[float]) -> list[dict]:
    """Retrieves text chunks with metadata similar to the query vector.

    Runs ANN (Approximate Nearest Neighbors) search on the configured Qdrant
    collection and returns a list of dictionaries with metadata and scores.

    Args:
        embedding: Query embedding vector.

    Returns:
        List of dicts representing each retrieved chunk and its metadata.

    Raises:
        ValueError: If the embedding does not have the expected dimensions.
        qdrant_client.http.exceptions.UnexpectedResponse: If the collection does not exist.
        requests.exceptions.ConnectionError: If Qdrant is offline.
    """
    if len(embedding) != settings.embed_dim:
        raise ValueError(f"embedding must have {settings.embed_dim} dimensions; got {len(embedding)}")

    client = _get_client()
    results = client.query_points(
        collection_name=settings.collection_name,
        query=embedding,
        using=settings.qdrant_vector_name,
        limit=settings.top_k,
        with_payload=True,
    ).points

    chunks: list[dict] = []
    for point in results:
        payload = point.payload or {}
        text = payload.get("content") or payload.get("text") or ""
        inicio = payload.get("chunk_index") or payload.get("inicio") or 0
        file = payload.get("file") or payload.get("source_file")
        pagina = payload.get("pagina_pdf") or payload.get("pagina")

        if not text:
            logger.warning(
                "vector_store.empty_or_missing_text",
                extra={"payload_keys": sorted(payload.keys())},
            )

        chunks.append({
            "id": str(point.id),
            "inicio": int(inicio),
            "text": str(text),
            "file": str(file) if file is not None else None,
            "pagina": int(pagina) if pagina is not None else None,
            "score": float(point.score) if point.score is not None else None,
        })
    return chunks


def search_context(embedding: list[float]) -> list[str]:
    """Retrieves text chunks similar to the query vector.

    Runs ANN (Approximate Nearest Neighbors) search on the configured Qdrant
    collection and returns the texts of the top_k most similar results.

    Args:
        embedding: Query embedding vector.

    Returns:
        List of strings with the text of each retrieved chunk.
        Returns an empty list if no results are found.

    Raises:
        ValueError: If the embedding does not have the expected dimensions.
        qdrant_client.http.exceptions.UnexpectedResponse: If the collection does not exist.
        requests.exceptions.ConnectionError: If Qdrant is offline.
    """
    rich_chunks = search_context_rich(embedding)
    return [c["text"] for c in rich_chunks]


def top_similarity(embedding: list[float]) -> float | None:
    """Return the highest corpus similarity score for the query vector, or None.

    Runs a top-1 ANN search on the configured collection and returns the score of the
    single nearest point. Used by the agent-path domain gate to decide whether the
    corpus can ground an answer at all.

    Args:
        embedding: Query embedding vector.

    Returns:
        The nearest point's similarity score, or ``None`` when no points are returned.

    Raises:
        ValueError: If the embedding does not have the expected dimensions.
    """
    if len(embedding) != settings.embed_dim:
        raise ValueError(f"embedding must have {settings.embed_dim} dimensions; got {len(embedding)}")

    client = _get_client()
    results = client.query_points(
        collection_name=settings.collection_name,
        query=embedding,
        using=settings.qdrant_vector_name,
        limit=1,
    ).points
    if not results:
        return None
    # Coerce to a concrete float: the Qdrant client is untyped under the CI
    # typecheck (deps not installed), so `.score` is Any there — returning it
    # directly would trip mypy's no-any-return (mirrors search_context building
    # a concrete list[str] rather than returning library Any).
    return float(results[0].score)
