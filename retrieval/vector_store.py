from qdrant_client import QdrantClient

from core.config import settings


def search_context(embedding: list[float]) -> list[str]:
    """Recupera até ``top_k`` textos de payload a partir do vetor de consulta."""
    client = QdrantClient(url=settings.qdrant_url)
    resultados = client.query_points(
        collection_name=settings.collection,
        query=embedding,
        limit=settings.top_k,
        with_payload=True,
    ).points
    return [str((r.payload or {}).get("text") or "") for r in resultados]
