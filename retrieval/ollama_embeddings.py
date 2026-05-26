"""Chamadas a embeddings Ollama com truncagem e retries.

O servidor local do Ollama no Windows pode retornar 500 ou derrubar a conexão
sob carga; retries com backoff reduzem falhas intermitentes na indexação e no RAG.
"""

from __future__ import annotations

import logging
import time

import httpx
import ollama
from ollama import RequestError, ResponseError

logger = logging.getLogger(__name__)

# Limite conservador para o contexto do modelo de embedding (caracteres).
_MAX_EMBED_CHARS = 8192
_MAX_RETRIES = 6
_RETRY_BASE_SEC = 0.75
_RETRY_MAX_SEC = 60.0


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
    last_exc: BaseException | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = ollama.embeddings(model=model, prompt=text)
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
