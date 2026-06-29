"""Tests for the agricultural domain gate (agent/intent.py, ADR-0010)."""

from unittest.mock import patch

import pytest

from agent.intent import DomainDecision, classify_domain


def test_classify_domain_in_domain_when_score_at_or_above_threshold() -> None:
    with (
        patch("agent.intent.generate_embedding", return_value=[0.1] * 768),
        patch("agent.intent.top_similarity", return_value=0.8),
        patch("agent.intent.settings.intent_threshold", 0.3),
    ):
        assert classify_domain("quando plantar soja?") == DomainDecision(in_domain=True, score=0.8)


def test_classify_domain_out_of_domain_when_score_below_threshold() -> None:
    with (
        patch("agent.intent.generate_embedding", return_value=[0.1] * 768),
        patch("agent.intent.top_similarity", return_value=0.1),
        patch("agent.intent.settings.intent_threshold", 0.3),
    ):
        decision = classify_domain("quem ganhou a copa do mundo?")
    assert decision.in_domain is False
    assert decision.score == 0.1


def test_classify_domain_in_domain_exactly_at_threshold() -> None:
    with (
        patch("agent.intent.generate_embedding", return_value=[0.1] * 768),
        patch("agent.intent.top_similarity", return_value=0.3),
        patch("agent.intent.settings.intent_threshold", 0.3),
    ):
        assert classify_domain("q").in_domain is True


def test_classify_domain_fails_open_and_logs_when_embedding_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch("agent.intent.generate_embedding", side_effect=RuntimeError("ollama down")),
        caplog.at_level("ERROR", logger="agent.intent"),
    ):
        decision = classify_domain("q")
    assert decision.in_domain is True
    assert decision.score is None
    assert any("agent.intent.failure" in r.message for r in caplog.records)


def test_classify_domain_fails_open_when_top_similarity_none() -> None:
    with (
        patch("agent.intent.generate_embedding", return_value=[0.1] * 768),
        patch("agent.intent.top_similarity", return_value=None),
    ):
        decision = classify_domain("q")
    assert decision.in_domain is True
    assert decision.score is None
