"""Testes do módulo verification/ (TASK-T64).

Cobre estabilidade numérica (epsilon na cosseno) e error handling no dispatch
de samples, no acesso a respostas de provider e no gate.
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


# ----------------------------- epsilon na cosseno -----------------------------


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
    """TASK-T68: cache local evita re-embedding do mesmo texto durante o clustering."""
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

    # 3 textos únicos → no máximo 3 chamadas a embed_text (cache evita repetição)
    assert call_count["n"] == 3
    assert len(clusters) == 3  # A, B, C distintos com threshold alto


# ----------------------------- missing API key warns -----------------------------


def test_compute_entropy_score_warns_when_groq_key_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "groq"),
        patch.object(entropy_module.settings, "groq_api_key", None),
        caplog.at_level("WARNING", logger="verification.entropy"),
    ):
        score = compute_entropy_score("q", "c")
    assert score == 0.0
    assert any("missing_api_key" in record.message for record in caplog.records)


def test_compute_entropy_score_warns_when_openrouter_key_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "openrouter"),
        patch.object(entropy_module.settings, "openrouter_api_key", None),
        caplog.at_level("WARNING", logger="verification.entropy"),
    ):
        score = compute_entropy_score("q", "c")
    assert score == 0.0


# ----------------------------- unknown provider raises -----------------------------


def test_compute_entropy_score_raises_for_unknown_provider() -> None:
    with (
        patch.object(entropy_module.settings, "verification_provider", "deepseek"),
        pytest.raises(ValueError, match="Unknown verification provider"),
    ):
        compute_entropy_score("q", "c")


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
    """Patcha ``get_chat_client`` para retornar um mock cujo ``chat`` devolve ``response``.

    Após TASK-T76, ``_generate_one_ollama`` consome o singleton centralizado em
    :mod:`core.ollama_clients`; o mock vai direto na função de acesso.
    """
    from unittest.mock import MagicMock

    fake = MagicMock()
    fake.chat.return_value = response
    return patch.object(entropy_module, "get_chat_client", return_value=fake)


def test_generate_one_ollama_handles_missing_message_key() -> None:
    bad_response: dict[str, Any] = {}  # sem chave "message"
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
        patch.object(gate_module, "generate", return_value="resposta"),
        patch.object(
            gate_module, "compute_entropy_score", side_effect=RuntimeError("entropy down")
        ),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())

    assert isinstance(result, ChatResponse)
    assert result.answer == "resposta"
    assert result.hallucination_score == 0.5


def test_gate_returns_clean_answer_when_score_under_threshold() -> None:
    with (
        patch.object(gate_module, "generate", return_value="resposta ok"),
        patch.object(gate_module, "compute_entropy_score", return_value=0.1),
        patch.object(gate_module.settings, "hallucination_threshold", 0.5),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    assert result.answer == "resposta ok"
    assert result.hallucination_score == 0.1


def test_gate_returns_fallback_message_when_all_retries_exceed_threshold() -> None:
    with (
        patch.object(gate_module, "generate", return_value="resposta alta entropia"),
        patch.object(gate_module, "compute_entropy_score", return_value=0.9),
        patch.object(gate_module.settings, "hallucination_threshold", 0.5),
    ):
        result = gate_module.evaluate(question="q", context="c", history=[], profile=_profile())
    assert result.answer == gate_module.FALLBACK_MESSAGE
    assert result.hallucination_score == 0.9
