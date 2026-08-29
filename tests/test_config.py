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
    """Minimal defaults to instantiate Settings under test (valid JWT + overrides).

    ``_env_file=None`` detaches the instance from the repository's ``.env``. Without it
    these tests assert what the developer's local file happens to say rather than what
    ``Settings`` declares: copying ``.env.example`` is step one of the documented setup,
    and any value in it that differs from a pinned default turned this file red for a
    reason that has nothing to do with the code.
    """
    base: dict[str, object] = {
        "_env_file": None,
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


def test_ollama_timeout_default_is_at_least_210s(monkeypatch: pytest.MonkeyPatch) -> None:
    # CPU-only generation takes ~160-200s; the default must clear it with margin.
    #
    # The variable is cleared first because several eval/ modules call load_dotenv() at
    # import time, so running the whole suite copies the developer's .env into os.environ.
    # Without this the test asserts what that file says rather than what Settings declares,
    # and goes red the moment .env.example ships a tuned value. It does ship one: the
    # shipped value has to clear a cold start and the declared default does not.
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
    s = Settings(**_kwargs())
    assert s.ollama_timeout >= 210
    assert s.ollama_timeout == 240.0


def test_ollama_timeout_rejects_over_max() -> None:
    # The le=600.0 bound (headroom under chat_timeout) stays enforced.
    with pytest.raises(ValidationError):
        Settings(**_kwargs(ollama_timeout=601.0))


# ----------------------------- chat_rate_limit (#110) -----------------------------


def test_chat_rate_limit_rejects_empty() -> None:
    # An empty CHAT_RATE_LIMIT must fail at startup, not on the first /chat call.
    with pytest.raises(ValidationError):
        Settings(**_kwargs(chat_rate_limit=""))


def test_chat_rate_limit_rejects_malformed() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(chat_rate_limit="not-a-limit"))


def test_chat_rate_limit_accepts_valid_slowapi_format() -> None:
    s = Settings(**_kwargs(chat_rate_limit="10/second"))
    assert s.chat_rate_limit == "10/second"


# ----------------------------- unknown .env keys (#166) -----------------------------


def test_settings_loads_when_env_has_unknown_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A .env carrying keys not declared on Settings must not abort startup.

    `.env.example` ships `OLLAMA_HOST` (read by the `ollama` library directly) and the
    `EVAL_*` keys (used by `eval/`), none of which are Settings fields. Settings must own
    only its own fields and ignore the rest instead of refusing to boot.
    """
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    valid_jwt = "test-jwt-secret-key-for-tests-only-32-chars-minimum"
    (tmp_path / ".env").write_text(
        f"JWT_SECRET_KEY={valid_jwt}\n"
        "OLLAMA_HOST=http://host.docker.internal:11434\n"
        "EVAL_USERNAME=foo\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    s = Settings()

    assert s.jwt_secret_key == valid_jwt


def test_settings_still_rejects_invalid_declared_field_with_unknown_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring unknown keys must not weaken field validation: an empty JWT still fails."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "JWT_SECRET_KEY=\nOLLAMA_HOST=http://host.docker.internal:11434\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()


# ----------------------------- agent_model (#170) -----------------------------


def test_agent_model_default() -> None:
    s = Settings(**_kwargs())
    assert s.agent_model == "qwen2.5:7b"


def test_agent_provider_defaults_to_ollama() -> None:
    s = Settings(**_kwargs())
    assert s.agent_provider == "ollama"


def test_agent_model_defaults_to_groq_model_when_provider_is_groq() -> None:
    s = Settings(**_kwargs(agent_provider="groq"))
    assert s.agent_model == "openai/gpt-oss-20b"


def test_explicit_agent_model_overrides_the_provider_default() -> None:
    s = Settings(**_kwargs(agent_provider="groq", agent_model="llama-3.1-8b-instant"))
    assert s.agent_model == "llama-3.1-8b-instant"


def test_agent_num_ctx_default_exceeds_the_deep_agent_prompt() -> None:
    # The deep-agent call is ~9.8k tokens (deepagents scaffolding); the default local context
    # window must be comfortably larger so Ollama does not truncate the system/tool prompt.
    s = Settings(**_kwargs())
    assert s.agent_num_ctx >= 12288


def test_agent_provider_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(agent_provider="bogus"))


def test_agent_enabled_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_ENABLED", raising=False)
    s = Settings(**_kwargs())
    assert s.agent_enabled is False


# ----------------------------- intent filter (#172) -----------------------------


def test_intent_filter_enabled_defaults_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTENT_FILTER_ENABLED", raising=False)
    s = Settings(**_kwargs())
    assert s.intent_filter_enabled is True


def test_intent_threshold_default_is_calibrated_value(monkeypatch: pytest.MonkeyPatch) -> None:
    # Calibrated on the corpus (ADR-0015): 0.80 admits 96.7% in-domain / leaks 3.3% out-of-domain.
    monkeypatch.delenv("INTENT_THRESHOLD", raising=False)
    s = Settings(**_kwargs())
    assert s.intent_threshold == 0.80


def test_intent_threshold_rejects_below_zero() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(intent_threshold=-0.01))


def test_intent_threshold_rejects_above_one() -> None:
    with pytest.raises(ValidationError):
        Settings(**_kwargs(intent_threshold=1.01))


def test_intent_threshold_accepts_boundaries() -> None:
    assert Settings(**_kwargs(intent_threshold=0.0)).intent_threshold == 0.0
    assert Settings(**_kwargs(intent_threshold=1.0)).intent_threshold == 1.0
