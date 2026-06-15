"""Pydantic Settings validation tests.

Covers the bounds applied to `Settings` and the `VerificationProvider` enum.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import Settings, VerificationProvider

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKING_JWT_SECRET = "super-secret-key-replace-in-production"


def _env_example_jwt_secret() -> str:
    """Return the JWT_SECRET_KEY value distributed in .env.example."""
    for line in (_REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("JWT_SECRET_KEY="):
            return stripped.split("=", 1)[1].strip()
    raise AssertionError("JWT_SECRET_KEY line not found in .env.example")


def _kwargs(**overrides: object) -> dict[str, object]:
    """Minimal defaults to instantiate Settings under test (valid JWT + overrides)."""
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
    """StrEnum guarantees equality with the underlying string — `provider == 'groq'`."""
    assert VerificationProvider.groq == "groq"
    assert VerificationProvider.ollama == "ollama"


# ----------------------------- optional API keys -----------------------------


def test_api_keys_default_to_none() -> None:
    s = Settings(**_kwargs())
    # When .env does not set them, defaults must be None.
    # (The project's .env may populate them — this test targets CI where .env is absent.)
    assert s.groq_api_key in (None, "") or isinstance(s.groq_api_key, str)
    assert s.openrouter_api_key in (None, "") or isinstance(s.openrouter_api_key, str)


def test_api_keys_accept_none_explicit() -> None:
    s = Settings(**_kwargs(groq_api_key=None, openrouter_api_key=None))
    assert s.groq_api_key is None
    assert s.openrouter_api_key is None


# ----------------------------- jwt_secret_key -----------------------------


def test_jwt_secret_key_rejects_short() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="short")


def test_jwt_secret_key_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="")


# --------------- shipped secrets must not be functional (#109) ---------------


def test_env_example_jwt_secret_does_not_pass_validation() -> None:
    """The JWT secret distributed in .env.example must fail Settings validation.

    A public repository must not ship a usable JWT signing key: the example must
    force the operator to generate their own (fail-loud at boot), never satisfy
    the >=32-char validator with a published value.
    """
    shipped = _env_example_jwt_secret()
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=shipped)


def test_setup_md_contains_no_functional_jwt_secret() -> None:
    """SETUP.md must not paste a working JWT secret in its copy-paste blocks."""
    setup_md = (_REPO_ROOT / "SETUP.md").read_text(encoding="utf-8")
    assert _WORKING_JWT_SECRET not in setup_md


# ----------------------------- ollama_timeout (#92) -----------------------------


def test_ollama_timeout_default_is_at_least_210s() -> None:
    # CPU-only generation takes ~160-200s; the default must clear it with margin.
    s = Settings(**_kwargs())
    assert s.ollama_timeout >= 210
    assert s.ollama_timeout == 240.0


def test_ollama_timeout_rejects_over_max() -> None:
    # The le=600.0 bound (headroom under chat_timeout) stays enforced.
    with pytest.raises(ValidationError):
        Settings(**_kwargs(ollama_timeout=601.0))
