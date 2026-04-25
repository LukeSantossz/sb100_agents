"""Busca vetorial no Qdrant.

Recupera chunks de texto semanticamente similares à query usando
busca por vizinhos mais próximos (ANN) no Qdrant.
"""

from qdrant_client import QdrantClient

from core.config import settings


def search_context(embedding: list[float]) -> list[str]:
    """Recupera chunks de texto similares ao vetor de consulta.

    Executa busca ANN (Approximate Nearest Neighbors) na coleção Qdrant
    configurada e retorna os textos dos top_k resultados mais similares.

    Args:
        embedding: Vetor de embedding da query (768 dimensões).

    Returns:
        Lista de strings contendo o texto de cada chunk recuperado.
        Retorna lista vazia se nenhum resultado for encontrado.

    Raises:
        qdrant_client.http.exceptions.UnexpectedResponse: Se a coleção não existir.
        requests.exceptions.ConnectionError: Se o Qdrant estiver offline.
    """
    client = QdrantClient(url=settings.qdrant_url)
    resultados = client.query_points(
        collection_name=settings.collection,
        query=embedding,
        limit=settings.top_k,
        with_payload=True,
    ).points
    return [str((r.payload or {}).get("text") or "") for r in resultados]
