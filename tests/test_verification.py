"""Tests for the verification/ module.

Covers numerical stability (epsilon in cosine) and error handling in sample
dispatch, provider response access, and the gate.
"""

from typing import Any
from unittest.mock import patch

import pytest

from core.schemas import ChatResponse, ExpertiseLevel, UserProfile
from verification import entropy as entropy_module
from verification import gate as gate_module
from verification.entropy import (
    _cluster_responses,
    _compute_similarity,
    _generate_one_ollama,
    _generate_samples,
    compute_entropy_score,
)


def _profile() -> UserProfile:
    return UserProfile(name="tester", expertise=ExpertiseLevel.beginner)


# ----------------------------- epsilon in cosine -----------------------------


def test_compute_similarity_handles_zero_vector() -> None:
    with patch.object(entropy_module, "embed_text", side_effect=[[0.0] * 8, [1.0] * 8]):
        score = _compute_similarity("zero text", "real text")
    assert score == 0.0


def test_compute_similarity_returns_unit_for_identical_vectors() -> None:
    vec = [0.1, 0.2, 0.3]
    with patch.object(entropy_module, "embed_text", side_effect=[vec, vec]):
        score = _compute_similarity("a", "a")
    assert score == pytest.approx(1.0, abs=1e-9)


def test_cluster_responses_caches_embeddings_per_unique_text() -> None:
    """Local cache avoids re-embedding the same text during clustering."""
    call_count = {"n": 0}
    embeddings = {
        "A": [1.0, 0.0],
        "B": [0.0, 1.0],
        "C": [0.7, 0.7],
    }

    def fake_embed(model: str, text: str) -> list[float]:
        call_count["n"] += 1
        return embeddings[text]

    with patch.object(entropy_module, "embed_text", side_effect=fake_embed):
        clusters = _cluster_responses(["A", "B", "C"], threshold=0.99)

    # 3 unique texts → at most 3 embed_text calls (cache avoids repeats)
    assert call_count["n"] == 3
    assert len(clusters) == 3  # A, B, C distinct with a high threshold


# ----------------------------- missing API key warns -----------------------------


def test_compute_entropy_score_raises_when_groq_key_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "groq"),
        patch.object(entropy_module.settings, "groq_api_key", None),
        caplog.at_level("WARNING", logger="verification.entropy"),
        pytest.raises(entropy_module.MissingVerifierKeyError),
    ):
        compute_entropy_score("q", "c")
    assert any("missing_api_key" in record.message for record in caplog.records)


def test_compute_entropy_score_raises_when_openrouter_key_missing() -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "openrouter"),
        patch.object(entropy_module.settings, "openrouter_api_key", None),
        pytest.raises(entropy_module.MissingVerifierKeyError),
    ):
        compute_entropy_score("q", "c")


# ----------------------------- unknown provider raises -----------------------------


def test_compute_entropy_score_raises_for_unknown_provider() -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "deepseek"),
        pytest.raises(ValueError, match="Unknown verification provider"),
    ):
        compute_entropy_score("q", "c")


# ----------------------------- sampling prompt language -----------------------------


def test_build_messages_uses_english_labels() -> None:
    messages = entropy_module._build_messages("q", "ctx")
    assert messages[0]["content"] == (
        "You are an assistant specialized in agronomy. Answer concisely."
    )
    assert messages[1]["content"] == "Context:\nctx\n\nQuestion: q"


def test_build_messages_without_context_passes_question_through() -> None:
    messages = entropy_module._build_messages("q", "")
    assert messages[1]["content"] == "q"


# ----------------------------- _generate_samples failure modes -----------------------------


def test_generate_samples_tolerates_partial_failure() -> None:
    call_count = {"n": 0}

    def fake_fn(q: str, c: str, m: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient")
        return "resp"

    with patch.object(entropy_module, "_generate_one_groq", side_effect=fake_fn):
        samples = _generate_samples("groq", "q", "c", "m", n=3)
    assert samples == ["resp", "resp"]
    assert call_count["n"] == 3


def test_generate_samples_propagates_when_all_fail() -> None:
    with (
        patch.object(entropy_module, "_generate_one_groq", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        _generate_samples("groq", "q", "c", "m", n=2)


# ----------------------------- ollama safe access -----------------------------


def _patch_ollama_client(response: dict[str, Any]) -> Any:
    """Patches ``get_chat_client`` to return a mock whose ``chat`` yields ``response``.

    ``_generate_one_ollama`` consumes the singleton centralized in
    :mod:`core.ollama_clients`; the mock targets the accessor function directly.
    """
    from unittest.mock import MagicMock

    fake = MagicMock()
    fake.chat.return_value = response
    return patch.object(entropy_module, "get_chat_client", return_value=fake)


def test_generate_one_ollama_handles_missing_message_key() -> None:
    bad_response: dict[str, Any] = {}  # no "message" key
    with _patch_ollama_client(bad_response):
        out = _generate_one_ollama("q", "c", "m")
    assert out == ""


def test_generate_one_ollama_handles_missing_content_key() -> None:
    bad_response: dict[str, Any] = {"message": {}}
    with _patch_ollama_client(bad_response):
        out = _generate_one_ollama("q", "c", "m")
    assert out == ""


def test_generate_one_ollama_returns_content() -> None:
    response: dict[str, Any] = {"message": {"content": "hello"}}
    with _patch_ollama_client(response):
        out = _generate_one_ollama("q", "c", "m")
    assert out == "hello"


# ----------------------------- gate fallback -----------------------------


def test_gate_returns_neutral_score_when_entropy_raises() -> None:
    with (
        patch.object(gate_module, "generate", return_value="answer"),
        patch.object(
            gate_module, "compute_entropy_score", side_effect=RuntimeError("entropy down")
        ),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())

    assert isinstance(result, ChatResponse)
    assert result.answer == "answer"
    assert result.hallucination_score == 0.5


def test_gate_returns_clean_answer_when_score_under_threshold() -> None:
    with (
        patch.object(gate_module, "generate", return_value="good answer"),
        patch.object(gate_module, "compute_entropy_score", return_value=0.1),
        patch.object(gate_module.settings, "hallucination_threshold", 0.5),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    assert result.answer == "good answer"
    assert result.hallucination_score == 0.1


def test_fallback_message_is_english() -> None:
    assert gate_module.FALLBACK_MESSAGE == "I cannot answer this topic with confidence."


def test_gate_returns_fallback_message_when_all_retries_exceed_threshold() -> None:
    with (
        patch.object(gate_module, "generate", return_value="high entropy answer"),
        patch.object(gate_module, "compute_entropy_score", return_value=0.9),
        patch.object(gate_module.settings, "hallucination_threshold", 0.5),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    assert result.answer == gate_module.FALLBACK_MESSAGE
    assert result.hallucination_score == 0.9


# ----------------------------- score_context tests -----------------------------


def test_score_context_returns_neutral_when_context_empty() -> None:
    from verification.gate import NEUTRAL_SCORE, score_context

    assert score_context("q", "   ") == NEUTRAL_SCORE


def test_score_context_returns_entropy_value() -> None:
    from unittest.mock import patch

    from verification.gate import score_context

    with patch("verification.gate.compute_entropy_score", return_value=0.3) as m:
        result = score_context("q", "some context")
    assert result == 0.3
    m.assert_called_once_with(question="q", context="some context")


def test_score_context_falls_back_to_neutral_on_error() -> None:
    from unittest.mock import patch

    from verification.gate import NEUTRAL_SCORE, score_context

    with patch("verification.gate.compute_entropy_score", side_effect=RuntimeError("boom")):
        result = score_context("q", "some context")
    assert result == NEUTRAL_SCORE


# ------------------------ missing verifier key degrades to neutral ------------------------


def test_evaluate_returns_neutral_when_verifier_key_missing() -> None:
    """A missing verifier API key degrades to neutral 0.5, not a confident 0.0."""
    with (
        patch.object(gate_module, "generate", return_value="answer"),
        patch.object(gate_module.settings, "verification_provider", "groq"),
        patch.object(gate_module.settings, "groq_api_key", None),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    assert result.answer == "answer"
    assert result.hallucination_score == gate_module.NEUTRAL_SCORE


def test_score_context_returns_neutral_when_verifier_key_missing() -> None:
    with (
        patch.object(gate_module.settings, "verification_provider", "groq"),
        patch.object(gate_module.settings, "groq_api_key", None),
    ):
        result = gate_module.score_context("q", "some context")
    assert result == gate_module.NEUTRAL_SCORE


def test_gate_logs_warning_not_traceback_when_verifier_key_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The missing-key degrade is a config state: a warning, not an ERROR with a traceback."""
    with (
        patch.object(gate_module, "generate", return_value="answer"),
        patch.object(gate_module.settings, "verification_provider", "groq"),
        patch.object(gate_module.settings, "groq_api_key", None),
        caplog.at_level("WARNING", logger="verification.gate"),
    ):
        gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    gate_records = [r for r in caplog.records if r.name == "verification.gate"]
    assert gate_records, "gate must log the missing-key degrade"
    assert all(r.levelname == "WARNING" for r in gate_records)
    assert all(r.exc_info is None for r in gate_records)


# ---------- partial sampling failure must not read as grounded (issue #102) ----------
#
# `_generate_samples` tolerates partial failure on purpose, so one 429 does not fail
# the request. But with the default of two samples, one failure left one sample, one
# cluster, and `_shannon_entropy(clusters, 1)` returns 0.0 by definition. The gate read
# that as a confidently grounded answer and delivered it as trustworthy. Entropy over
# one sample is not a low value, it is no value.


def _failing_then_ok(failures: int):
    """A sample function that raises for the first ``failures`` calls, then succeeds."""
    calls = {"n": 0}

    def _fn(question: str, context: str, model: str) -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise RuntimeError("rate limit")
        return f"resposta {calls['n']}"

    return _fn


def test_one_surviving_sample_raises_instead_of_scoring_zero(monkeypatch) -> None:
    """The defect: two requested, one failed, score 0.0 = 'fully grounded'."""
    monkeypatch.setattr(entropy_module.settings, "verification_provider", "ollama")
    monkeypatch.setattr(entropy_module.settings, "entropy_num_samples", 2)
    monkeypatch.setattr(entropy_module, "_generate_one_ollama", _failing_then_ok(1))

    with pytest.raises(entropy_module.InsufficientSamplesError):
        entropy_module.compute_entropy_score(question="q", context="c")


def test_two_surviving_samples_still_score(monkeypatch) -> None:
    """A real measurement must not be thrown away just because a call was lost.

    Discarding it would let one flaky call silently disable verification, which is
    the same failure this fixes, pointed the other way.
    """
    monkeypatch.setattr(entropy_module.settings, "verification_provider", "ollama")
    monkeypatch.setattr(entropy_module.settings, "entropy_num_samples", 3)
    monkeypatch.setattr(entropy_module, "_generate_one_ollama", _failing_then_ok(1))
    monkeypatch.setattr(entropy_module, "_compute_similarity", lambda *a, **k: 0.0)

    score = entropy_module.compute_entropy_score(question="q", context="c")

    assert 0.0 <= score <= 1.0


def test_every_sample_failing_still_propagates(monkeypatch) -> None:
    """Unchanged behaviour: the last exception reaches the gate."""
    monkeypatch.setattr(entropy_module.settings, "verification_provider", "ollama")
    monkeypatch.setattr(entropy_module.settings, "entropy_num_samples", 2)
    monkeypatch.setattr(entropy_module, "_generate_one_ollama", _failing_then_ok(99))

    with pytest.raises(RuntimeError):
        entropy_module.compute_entropy_score(question="q", context="c")


def test_the_gate_returns_the_neutral_score_on_insufficient_samples(monkeypatch) -> None:
    """The answer is still delivered; only the score degrades."""

    def _raise(**kwargs):
        raise entropy_module.InsufficientSamplesError("1 of 2")

    monkeypatch.setattr(gate_module, "compute_entropy_score", _raise)
    monkeypatch.setattr(gate_module, "generate", lambda **kwargs: "uma resposta")

    response = gate_module.evaluate(
        question="q", context="c", history=[], profile=UserProfile(name="U", expertise="beginner")
    )

    assert response.answer == "uma resposta"
    assert response.hallucination_score == gate_module.NEUTRAL_SCORE


def test_score_context_returns_the_neutral_score_on_insufficient_samples(monkeypatch) -> None:
    """The agent path shares the policy."""

    def _raise(**kwargs):
        raise entropy_module.InsufficientSamplesError("1 of 2")

    monkeypatch.setattr(gate_module, "compute_entropy_score", _raise)

    assert gate_module.score_context("q", "algum contexto") == gate_module.NEUTRAL_SCORE
