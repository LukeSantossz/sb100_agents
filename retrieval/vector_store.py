"""Busca vetorial no Qdrant.

Recupera chunks de texto semanticamente similares à query usando
busca por vizinhos mais próximos (ANN) no Qdrant.

TASK-T66: usa singleton thread-safe do ``QdrantClient`` (evita instanciar
TCP/HTTP a cada query) e valida a dimensão do embedding antes da chamada.
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
    """Retorna instância singleton do ``QdrantClient`` (lazy init thread-safe).

    Implementa double-checked locking para minimizar contenção após o primeiro
    acesso. Reset (para testes) deve zerar o módulo-level ``_qdrant_client``.
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
    """Recupera chunks de texto similares ao vetor de consulta.

    Executa busca ANN (Approximate Nearest Neighbors) na coleção Qdrant
    configurada e retorna os textos dos top_k resultados mais similares.

    Args:
        embedding: Vetor de embedding da query (768 dimensões).

    Returns:
        Lista de strings contendo o texto de cada chunk recuperado.
        Retorna lista vazia se nenhum resultado for encontrado.

    Raises:
        ValueError: Se o embedding não tiver exatamente 768 dimensões.
        qdrant_client.http.exceptions.UnexpectedResponse: Se a coleção não existir.
        requests.exceptions.ConnectionError: Se o Qdrant estiver offline.
    """
    if len(embedding) != _EMBEDDING_DIM:
        raise ValueError(f"embedding must have {_EMBEDDING_DIM} dimensions; got {len(embedding)}")

    client = _get_client()
    resultados = client.query_points(
        collection_name=settings.collection_name,
        query=embedding,
        limit=settings.top_k,
        with_payload=True,
    ).points

    chunks: list[str] = []
    for point in resultados:
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
