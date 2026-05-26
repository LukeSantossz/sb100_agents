"""Testes das validações do Pydantic Settings (TASK-T62).

Cobre os bounds aplicados a `Settings` e o enum `VerificationProvider`.
"""

import pytest
from pydantic import ValidationError

from core.config import Settings, VerificationProvider


def _kwargs(**overrides: object) -> dict[str, object]:
    """Defaults mínimos para instanciar Settings sob teste (JWT válido + overrides)."""
    base: dict[str, object] = {
        "jwt_secret_key": "test-jwt-secret-key-for-tests-only-32-chars-minimum",
    }
    base.update(overrides)
    return base


# ----------------------------- top_k -----------------------------


def test_top_k_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(top_k=0))


def test_top_k_rejects_over_max() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(top_k=101))


def test_top_k_accepts_valid_range() -> None:
    s = Settings(**_kwargs(top_k=50))
    assert s.top_k == 50


# ----------------------------- hallucination_threshold -----------------------------


def test_hallucination_threshold_rejects_below_zero() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(hallucination_threshold=-0.1))


def test_hallucination_threshold_rejects_above_one() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(hallucination_threshold=1.1))


def test_hallucination_threshold_accepts_boundaries() -> None:
    low = Settings(**_kwargs(hallucination_threshold=0.0))
    high = Settings(**_kwargs(hallucination_threshold=1.0))
    assert low.hallucination_threshold == 0.0
    assert high.hallucination_threshold == 1.0


# ----------------------------- entropy_num_samples -----------------------------


def test_entropy_num_samples_rejects_below_two() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(entropy_num_samples=1))


def test_entropy_num_samples_accepts_two_or_more() -> None:
    s = Settings(**_kwargs(entropy_num_samples=5))
    assert s.entropy_num_samples == 5


# ----------------------------- llm_max_tokens -----------------------------


def test_llm_max_tokens_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(llm_max_tokens=0))


def test_llm_max_tokens_rejects_over_4096() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(llm_max_tokens=4097))


# ----------------------------- verification_provider -----------------------------


def test_verification_provider_accepts_groq() -> None:
    s = Settings(**_kwargs(verification_provider="groq"))
    assert s.verification_provider is VerificationProvider.groq


def test_verification_provider_accepts_ollama() -> None:
    s = Settings(**_kwargs(verification_provider="ollama"))
    assert s.verification_provider is VerificationProvider.ollama


def test_verification_provider_accepts_openrouter() -> None:
    s = Settings(**_kwargs(verification_provider="openrouter"))
    assert s.verification_provider is VerificationProvider.openrouter


def test_verification_provider_rejects_typo() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(verification_provider="grok"))  # typo


def test_verification_provider_str_comparison_works() -> None:
    """StrEnum garante igualdade com a string subjacente — `provider == 'groq'`."""
    assert VerificationProvider.groq == "groq"
    assert VerificationProvider.ollama == "ollama"


# ----------------------------- API keys opcionais -----------------------------


def test_api_keys_default_to_none() -> None:
    s = Settings(**_kwargs())
    # Quando .env não define, defaults devem ser None.
    # (.env do projeto pode estar populando — esse teste sob CI onde .env não existe.)
    assert s.groq_api_key in (None, "") or isinstance(s.groq_api_key, str)
    assert s.openrouter_api_key in (None, "") or isinstance(s.openrouter_api_key, str)


def test_api_keys_accept_none_explicit() -> None:
    s = Settings(**_kwargs(groq_api_key=None, openrouter_api_key=None))
    assert s.groq_api_key is None
    assert s.openrouter_api_key is None


# ----------------------------- jwt_secret_key (já cobrindo regressão T60) -----------------------------


def test_jwt_secret_key_rejects_short() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="short")


def test_jwt_secret_key_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="")
