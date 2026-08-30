"""Ollama embedding calls with truncation and retries.

The local Ollama server on Windows may return 500 or drop the connection
under load; retries with backoff reduce intermittent failures during
indexing and RAG.

The HTTP client is centralized in :mod:`core.ollama_clients`. The HTTP
timeout comes from ``settings.ollama_embed_timeout`` (default 5s, tunable).
Worst-case total budget stays at ~25s (4 attempts x 5s + sleeps 0.75/1.5/2.0).
"""

from __future__ import annotations

import logging
import time

import httpx
from ollama import RequestError, ResponseError

from core.ollama_clients import get_embed_client

logger = logging.getLogger(__name__)

# Truncation guard for the embedding model context, in characters.
#
# It was 8192, which is above what nomic-embed-text accepts, so the truncation ran
# and the call still failed with "the input length exceeds the context length"
# (#225). The model has a 2048-token context and how many characters fit depends on
# the tokenizer and the text, so the bound has to be measured, not derived: a binary
# search for the largest accepted prefix of the longest chunks in the shipped
# collection found a worst case of 6203 characters, or 3.03 characters per token.
# 4000 is 1.95 characters per token, a third under that worst case, and is the value
# 519 chunks were embedded at during the #106 benchmark without a rejection.
#
# It stays above the 2000-character cap on ChatRequest.question, so nothing the API
# accepts is truncated. Counting real tokens would be exact and would cost a
# model-specific tokenizer dependency to bound one call. See docs/specs/0020.
_MAX_EMBED_CHARS = 4000
_MAX_RETRIES = 4
_RETRY_BASE_SEC = 0.75
_RETRY_MAX_SEC = 2.0


def embed_text(model: str, prompt: str) -> list[float]:
    """Returns the embedding vector for the text, with truncation and retries.

    Args:
        model: Model name in Ollama (e.g. nomic-embed-text).
        prompt: Input text.

    Returns:
        List of floats for the embedding.

    Raises:
        The last exception after exhausting attempts, if all fail.
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
        # Defensive: the loop only exits without an exception on success.
        raise RuntimeError("embed_text exhausted retries with no captured exception")
    raise last_exc
