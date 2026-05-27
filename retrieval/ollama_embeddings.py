"""Chamadas a embeddings Ollama com truncagem e retries.

O servidor local do Ollama no Windows pode retornar 500 ou derrubar a conexão
sob carga; retries com backoff reduzem falhas intermitentes na indexação e no RAG.

TASK-T76 (consolidação): cliente HTTP centralizado em
:mod:`core.ollama_clients`. Timeout HTTP vem de ``settings.ollama_embed_timeout``
(default 5s, ajustável). Worst-case do orçamento total permanece em ~25s
(4 tentativas × 5s + sleeps 0.75/1.5/2.0).
"""

from __future__ import annotations

import logging
import time

import httpx
from ollama import RequestError, ResponseError

from core.ollama_clients import get_embed_client

logger = logging.getLogger(__name__)

# Limite conservador para o contexto do modelo de embedding (caracteres).
_MAX_EMBED_CHARS = 8192
_MAX_RETRIES = 4
_RETRY_BASE_SEC = 0.75
_RETRY_MAX_SEC = 2.0


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
    client = get_embed_client()
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
