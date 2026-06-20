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
