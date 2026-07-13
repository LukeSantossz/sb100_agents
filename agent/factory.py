"""Factory for the SmartB100 deep agent (deepagents + Groq), isolated behind agent/."""

import threading
from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr

from agent.prompt import AGENT_INSTRUCTIONS
from agent.tools import search_corpus
from core.config import AgentProvider, settings


def default_model() -> BaseChatModel:
    """Build the default agent chat model from settings, per ``agent_provider``.

    ``ollama`` runs a local model (no hosted rate limit); ``groq`` uses the hosted model
    (ADR-0009). See the local-provider ADR for why the local path is the default.
    """
    if settings.agent_provider == AgentProvider.ollama:
        # Pass the configured Ollama timeout (operators raise it for slow local generation),
        # matching how the rest of the app builds its Ollama clients.
        return ChatOllama(
            model=settings.agent_model, client_kwargs={"timeout": settings.ollama_timeout}
        )
    api_key = SecretStr(settings.groq_api_key) if settings.groq_api_key is not None else None
    return ChatGroq(model=settings.agent_model, api_key=api_key)


def create_agent(model: BaseChatModel | None = None) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Build the compiled deep-agent graph.

    `model` defaults to the Groq model from settings; inject a model in tests to compile
    the graph without network access.
    """
    if model is None:
        model = default_model()
    return create_deep_agent(
        model=model,
        tools=[search_corpus],
        system_prompt=AGENT_INSTRUCTIONS,
    )


_cached_graph: CompiledStateGraph[Any, Any, Any, Any] | None = None
_graph_lock = threading.Lock()


def get_agent() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Return the process-wide compiled agent graph, building it once (lazy, thread-safe).

    The compiled graph (and its `ChatGroq` client) is expensive to build, so it is cached and
    reused across requests. Double-checked locking mirrors the ``_sessions_lock`` pattern in
    ``api/routes/chat.py`` so concurrent first requests on the FastAPI threadpool do not
    double-build. Tests bypass this by injecting a graph into ``invoke_agent``.
    """
    global _cached_graph
    graph = _cached_graph
    if graph is None:
        with _graph_lock:
            graph = _cached_graph
            if graph is None:
                graph = create_agent()
                _cached_graph = graph
    return graph


def reset_agent_cache() -> None:
    """Clear the cached graph so the next ``get_agent()`` rebuilds it (reconfiguration / tests)."""
    global _cached_graph
    with _graph_lock:
        _cached_graph = None
