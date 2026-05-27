"""Clientes Ollama compartilhados (TASK-T76).

Consolida em um único módulo o padrão de cliente HTTP Ollama com timeout, que
antes existia em três variantes inconsistentes (em ``generation/llm.py``,
``verification/entropy.py`` e ``retrieval/ollama_embeddings.py``).

Expõe dois singletons thread-safe via double-checked locking:

- :func:`get_chat_client` — para geração de respostas; timeout configurável via
  ``settings.ollama_timeout`` (default 120s).
- :func:`get_embed_client` — para embeddings; timeout configurável via
  ``settings.ollama_embed_timeout`` (default 5s, mais agressivo porque embed
  é leve e parte do hot-path do RAG).

Testes que dependem de mocks do ``ollama.Client`` devem chamar
:func:`reset_clients` em fixture autouse para isolar o estado entre cenários.
"""

import threading

from ollama import Client as OllamaClient

from core.config import settings

_chat_client: OllamaClient | None = None
_chat_client_lock = threading.Lock()

_embed_client: OllamaClient | None = None
_embed_client_lock = threading.Lock()


def get_chat_client() -> OllamaClient:
    """Retorna o singleton do cliente Ollama para chat completions.

    Usa ``settings.ollama_timeout`` como timeout HTTP. Lazy init thread-safe.
    """
    global _chat_client
    if _chat_client is None:
        with _chat_client_lock:
            if _chat_client is None:
                _chat_client = OllamaClient(timeout=settings.ollama_timeout)
    return _chat_client


def get_embed_client() -> OllamaClient:
    """Retorna o singleton do cliente Ollama para embeddings.

    Usa ``settings.ollama_embed_timeout`` como timeout HTTP. Lazy init thread-safe.
    """
    global _embed_client
    if _embed_client is None:
        with _embed_client_lock:
            if _embed_client is None:
                _embed_client = OllamaClient(timeout=settings.ollama_embed_timeout)
    return _embed_client


def reset_clients() -> None:
    """Limpa os singletons (chat e embed).

    Uso esperado: fixture autouse em testes que precisem patchar ``OllamaClient``
    e garantir que a próxima chamada instancie a partir do mock.
    """
    global _chat_client, _embed_client
    with _chat_client_lock:
        _chat_client = None
    with _embed_client_lock:
        _embed_client = None
