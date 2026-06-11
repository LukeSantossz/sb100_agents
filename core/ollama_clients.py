"""Shared Ollama clients.

Consolidates into a single module the Ollama HTTP client pattern with timeout,
which previously existed in three inconsistent variants (in ``generation/llm.py``,
``verification/entropy.py`` and ``retrieval/ollama_embeddings.py``).

Exposes two thread-safe singletons via double-checked locking:

- :func:`get_chat_client` — for answer generation; timeout configurable via
  ``settings.ollama_timeout`` (default 120s).
- :func:`get_embed_client` — for embeddings; timeout configurable via
  ``settings.ollama_embed_timeout`` (default 5s, more aggressive because embed
  is lightweight and part of the RAG hot path).

Tests that rely on ``ollama.Client`` mocks must call :func:`reset_clients`
in an autouse fixture to isolate state between scenarios.
"""

import threading

from ollama import Client as OllamaClient

from core.config import settings

_chat_client: OllamaClient | None = None
_chat_client_lock = threading.Lock()

_embed_client: OllamaClient | None = None
_embed_client_lock = threading.Lock()


def get_chat_client() -> OllamaClient:
    """Return the Ollama client singleton for chat completions.

    Uses ``settings.ollama_timeout`` as the HTTP timeout. Thread-safe lazy init.
    """
    global _chat_client
    if _chat_client is None:
        with _chat_client_lock:
            if _chat_client is None:
                _chat_client = OllamaClient(timeout=settings.ollama_timeout)
    return _chat_client


def get_embed_client() -> OllamaClient:
    """Return the Ollama client singleton for embeddings.

    Uses ``settings.ollama_embed_timeout`` as the HTTP timeout. Thread-safe lazy init.
    """
    global _embed_client
    if _embed_client is None:
        with _embed_client_lock:
            if _embed_client is None:
                _embed_client = OllamaClient(timeout=settings.ollama_embed_timeout)
    return _embed_client


def reset_clients() -> None:
    """Clear the singletons (chat and embed).

    Expected use: autouse fixture in tests that need to patch ``OllamaClient``
    and ensure the next call instantiates from the mock.
    """
    global _chat_client, _embed_client
    with _chat_client_lock:
        _chat_client = None
    with _embed_client_lock:
        _embed_client = None
