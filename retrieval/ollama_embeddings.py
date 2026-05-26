"""Chamadas a embeddings Ollama com truncagem e retries.

O servidor local do Ollama no Windows pode retornar 500 ou derrubar a conexão
sob carga; retries com backoff reduzem falhas intermitentes na indexação e no RAG.

TASK-T75 (follow-up T68): orçamento total de timeout endurecido para ≤30s.
Antes: 6 tentativas com sleeps capeados em 60s e sem timeout HTTP — chamadas
podiam ficar penduradas indefinidamente se o Ollama hang.

Configuração atual (worst-case ~25s):
    - ``_EMBED_HTTP_TIMEOUT`` = 5.0s por chamada (via ``ollama.Client(timeout=...)``)
    - ``_MAX_RETRIES`` = 4 tentativas (era 6)
    - ``_RETRY_MAX_SEC`` = 2.0s (capeia o backoff exponencial — era 60.0)

Trade-off: a retração agressiva falha mais cedo se o servidor Ollama estiver
overloaded ou em cold-start de modelo (~10s típico). Em ambientes de produção
com cold-load esperado, considerar aumentar ``_EMBED_HTTP_TIMEOUT`` ou
``_MAX_RETRIES`` via configuração — atualmente são constantes de módulo.
"""

from __future__ import annotations

import logging
import threading
import time

import httpx
import ollama
from ollama import RequestError, ResponseError

logger = logging.getLogger(__name__)

# Limite conservador para o contexto do modelo de embedding (caracteres).
_MAX_EMBED_CHARS = 8192
_MAX_RETRIES = 4
_RETRY_BASE_SEC = 0.75
_RETRY_MAX_SEC = 2.0
_EMBED_HTTP_TIMEOUT = 5.0

_embed_client: ollama.Client | None = None
_embed_client_lock = threading.Lock()


def _get_embed_client() -> ollama.Client:
    """Singleton thread-safe do cliente Ollama para embeddings (com timeout)."""
    global _embed_client
    if _embed_client is None:
        with _embed_client_lock:
            if _embed_client is None:
                _embed_client = ollama.Client(timeout=_EMBED_HTTP_TIMEOUT)
    return _embed_client


def embed_text(model: str, prompt: str) -> list[float]:
    """Retorna o vetor de embedding para o texto, com truncagem e retries.

    Args:
        model: Nome do modelo no Ollama (ex.: nomic-embed-text).
        prompt: Texto de entrada.

    Returns:
        Lista de floats do embedding.

    Raises:
        A última exceção após esgotar as tentativas, se todas falharem.
    """
    text = (prompt or "")[:_MAX_EMBED_CHARS]
    client = _get_embed_client()
    last_exc: BaseException | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.embeddings(model=model, prompt=text)
            result: list[float] = response["embedding"]
            return result
        except (
            ResponseError,
            RequestError,
            ConnectionError,
            TimeoutError,
            httpx.RequestError,
            OSError,
        ) as exc:
            last_exc = exc
            logger.warning(
                "ollama_embeddings.attempt_failed",
                extra={"attempt": attempt, "error": str(exc)},
            )
            if attempt >= _MAX_RETRIES - 1:
                break
            delay = min(_RETRY_BASE_SEC * (2**attempt), _RETRY_MAX_SEC)
            time.sleep(delay)
    if last_exc is None:
        # Defensivo: o loop só sai sem exceção se retornar com sucesso.
        raise RuntimeError("embed_text exhausted retries with no captured exception")
    raise last_exc
