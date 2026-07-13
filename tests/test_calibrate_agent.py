"""Tests for the agent calibration harness (eval/calibrate_agent.py).

Phase 1 covers the pure, deterministic calibration math: threshold metrics
(leakage / over-block) and threshold selection. These use synthetic in-memory
scores and never touch Qdrant or Groq, so they run under the default CI
selection (`-m "not requires_infra"`).
"""

from __future__ import annotations

import pytest

from eval.calibrate_agent import (
    ScoredQuestion,
    probe_groq_token_report,
    run_calibration,
    select_threshold_youden,
    threshold_at_max_fpr,
    threshold_metrics,
)


def _sample() -> list[ScoredQuestion]:
    """Two positives and two negatives with a clean separating gap around 0.5."""
    return [
        ScoredQuestion(score=0.8, in_domain=True),
        ScoredQuestion(score=0.4, in_domain=True),
        ScoredQuestion(score=0.6, in_domain=False),
        ScoredQuestion(score=0.2, in_domain=False),
    ]


def test_threshold_metrics_counts_admissions_at_the_threshold() -> None:
    # Admit iff score >= threshold. At 0.5: positive 0.8 admitted (tp=1/2),
    # negative 0.6 admitted as leakage (fp=1/2).
    metrics = threshold_metrics(_sample(), threshold=0.5)
    assert metrics.tpr == 0.5
    assert metrics.fpr == 0.5
    assert metrics.n_pos == 2
    assert metrics.n_neg == 2


def test_threshold_metrics_admits_all_at_zero_threshold() -> None:
    metrics = threshold_metrics(_sample(), threshold=0.0)
    assert metrics.tpr == 1.0
    assert metrics.fpr == 1.0


def test_threshold_metrics_raises_without_both_classes() -> None:
    positives_only = [ScoredQuestion(score=0.7, in_domain=True)]
    with pytest.raises(ValueError):
        threshold_metrics(positives_only, threshold=0.5)


def test_select_threshold_youden_picks_the_separating_point() -> None:
    # A threshold in (0.6, 0.8] admits both positives... no: 0.8 only above 0.6.
    # Best Youden's J (tpr - fpr) is at a threshold that admits the 0.8 positive
    # while rejecting the 0.6 negative, i.e. in (0.6, 0.8]; J = 0.5 - 0.0 = 0.5.
    chosen = select_threshold_youden(_sample())
    metrics = threshold_metrics(_sample(), chosen)
    assert metrics.fpr == 0.0
    assert metrics.tpr == 0.5


def test_threshold_at_max_fpr_respects_the_leakage_ceiling() -> None:
    # With max_fpr=0.0 no leakage is allowed, so only the 0.6 negative must be
    # excluded; the returned threshold keeps fpr at or below the ceiling.
    chosen = threshold_at_max_fpr(_sample(), max_fpr=0.0)
    metrics = threshold_metrics(_sample(), chosen)
    assert metrics.fpr <= 0.0


# Real llm_output["token_usage"] captured from a live openai/gpt-oss-20b call via
# probe_groq_token_report() (issue #192). This is the ChatGroq response shape the runtime
# budget depends on; a Groq change that moved total_tokens elsewhere would break this and
# CI would catch it. The shape is model-independent across Groq's OpenAI-compatible API.
_REAL_GROQ_TOKEN_USAGE = {
    "completion_tokens": 38,
    "prompt_tokens": 79,
    "total_tokens": 117,
    "completion_time": 0.050069686,
    "completion_tokens_details": {"reasoning_tokens": 28},
    "prompt_time": 0.003808957,
    "prompt_tokens_details": None,
    "queue_time": 0.231608259,
    "total_time": 0.053878643,
}


def test_extract_total_tokens_reads_the_real_groq_shape() -> None:
    from langchain_core.outputs import Generation, LLMResult

    from agent.limits import TokenBudgetHandler

    llm_output = {"token_usage": dict(_REAL_GROQ_TOKEN_USAGE), "model_name": "openai/gpt-oss-20b"}
    result = LLMResult(generations=[[Generation(text="ok")]], llm_output=llm_output)

    handler = TokenBudgetHandler(budget=10**12)
    handler.on_llm_end(result)

    assert handler.total == 117


@pytest.mark.requires_infra
def test_groq_probe_reports_total_tokens_as_positive_int() -> None:
    # The token budget (ADR-0012) is inert unless Groq reports total_tokens where the
    # runtime extractor reads it. The probe makes one real ChatGroq call and reports the
    # count the budget would actually see; a non-positive value means the budget is inert.
    result = probe_groq_token_report()
    assert isinstance(result.total_tokens_via_runtime, int)
    assert result.total_tokens_via_runtime > 0


@pytest.mark.requires_infra
def test_run_calibration_produces_evidence_for_both_classes() -> None:
    # A tiny end-to-end run must score both classes and measure at least one real agent
    # run with a non-trivial step count. This exercises the live path the full run uses.
    evidence = run_calibration(
        num_positives=2, num_negatives=2, num_agent_runs=1, recursion_ceiling=50
    )
    assert any(scored.in_domain for scored in evidence.scored)
    assert any(not scored.in_domain for scored in evidence.scored)
    assert len(evidence.runs) >= 1
    assert all(run.steps >= 1 for run in evidence.runs)
    assert all(run.total_tokens >= 1 for run in evidence.runs)
