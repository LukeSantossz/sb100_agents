"""Tests for the agent/ scaffold: search_corpus tool and the agent factory."""

from unittest.mock import patch

from agent.tools import search_corpus


def test_search_corpus_returns_context_text() -> None:
    with (
        patch("agent.tools.generate_embedding", return_value=[0.0] * 768),
        patch("agent.tools.search_context", return_value=["chunk one", "chunk two"]),
    ):
        result = search_corpus.invoke({"query": "quando plantar soja?"})
    assert "chunk one" in result
    assert "chunk two" in result


def test_search_corpus_handles_empty_results() -> None:
    with (
        patch("agent.tools.generate_embedding", return_value=[0.0] * 768),
        patch("agent.tools.search_context", return_value=[]),
    ):
        result = search_corpus.invoke({"query": "x"})
    assert "no relevant context" in result.lower()


def test_search_corpus_degrades_on_retrieval_error() -> None:
    with patch("agent.tools.generate_embedding", side_effect=RuntimeError("ollama down")):
        result = search_corpus.invoke({"query": "x"})
    assert "retrieval error" in result.lower()


from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langgraph.graph.state import CompiledStateGraph

from agent.factory import create_agent, default_model


def test_create_agent_compiles_graph_with_injected_model() -> None:
    fake = GenericFakeChatModel(messages=iter(["ok"]))
    agent = create_agent(model=fake)
    assert isinstance(agent, CompiledStateGraph)
    assert "search_corpus" in str(agent.get_graph())


def test_default_model_reads_settings() -> None:
    captured: dict[str, object] = {}

    class _FakeChatGroq:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    with patch("agent.factory.ChatGroq", _FakeChatGroq):
        default_model()
    assert captured["model"] == "openai/gpt-oss-20b"
    assert "api_key" in captured
