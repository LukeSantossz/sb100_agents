"""Calibration harness for the agent's safety knobs (issue #192, SPEC).

Produces evidence, against the live environment, for three settings that ship as
guessed defaults and gate whether ``agent_enabled`` can be turned on:

- ``intent_threshold`` (domain gate, ADR-0010): swept over corpus-derived in-domain
  positives and LLM-generated out-of-domain negatives, scored with the same
  ``retrieval.top_similarity`` signal the gate uses.
- ``agent_recursion_limit`` and ``agent_token_budget`` (ADR-0012): measured by running
  the real compiled agent over the in-domain questions.

A token-report probe first confirms the configured provider reports ``total_tokens`` where
``agent/limits.py`` reads it (``llm_output`` for Groq, message ``usage_metadata`` for Ollama,
per ADR-0013) — the token budget is inert otherwise. The agent runs on whatever
``agent_provider`` selects; the default local Ollama model has no rate limit, so runs are
paced only by local inference.

This module keeps its pure, deterministic math (threshold metrics and selection) free of
heavy or networked imports so the guard tests can exercise it without Qdrant or a model.
Live-measurement functions import their dependencies lazily, inside the function body.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ARCHIVES_DIR = _PROJECT_ROOT / "archives"
# Default to the committed guard-test fixture so a recalibration updates the very evidence the
# guard tests and config defaults are checked against, not a gitignored scratch file.
_DEFAULT_EVIDENCE_PATH = _PROJECT_ROOT / "tests" / "fixtures" / "calibration_evidence.json"

_DEFAULT_SEED = 42
_QUESTIONS_PER_CHUNK = 10
_NEGATIVE_BATCH = 15
# A generous default safety factor over the observed p95 for the loop bounds.
_BOUND_SAFETY_FACTOR = 1.5

_OUT_OF_DOMAIN_PROMPT = """You are writing test questions for a DELIBERATELY NON-agricultural domain.
Generate {num_questions} clear, natural questions in Portuguese (pt-BR) about everyday topics that have
NOTHING to do with agriculture, farming, agronomy, soil, crops, livestock, irrigation, or rural life.
Spread them across varied domains such as: law, human medicine, football, pop music, web programming,
personal finance, dessert cooking, tourism, video games, and world history.

Return ONLY a JSON array of strings, no explanations.
Format: ["question 1", "question 2", ...]

JSON array with {num_questions} questions:"""

# Admitting a question iff score >= threshold reproduces every ROC operating point when
# the candidate thresholds are the observed scores themselves.
_ADMIT_EPSILON = 1e-9


@dataclass(frozen=True)
class ScoredQuestion:
    """One calibration question with its corpus similarity score and true label.

    ``in_domain`` is the ground truth: ``True`` for an agricultural (positive) question
    that the gate should admit, ``False`` for an out-of-domain (negative) one it should
    deflect.
    """

    score: float
    in_domain: bool


@dataclass(frozen=True)
class ThresholdMetrics:
    """Gate behavior at one candidate ``threshold`` over a labeled score set.

    ``tpr`` is the fraction of in-domain questions admitted (higher is less over-block);
    ``fpr`` is the fraction of out-of-domain questions admitted (the leakage rate).
    """

    threshold: float
    tpr: float
    fpr: float
    n_pos: int
    n_neg: int


def threshold_metrics(scored: list[ScoredQuestion], threshold: float) -> ThresholdMetrics:
    """Measure admit-rate on each class at ``threshold`` (admit iff score >= threshold)."""
    positives = [q for q in scored if q.in_domain]
    negatives = [q for q in scored if not q.in_domain]
    if not positives or not negatives:
        raise ValueError(
            "calibration needs at least one in-domain and one out-of-domain question; "
            f"got {len(positives)} positive(s) and {len(negatives)} negative(s)"
        )
    admitted_positives = sum(1 for q in positives if q.score >= threshold)
    admitted_negatives = sum(1 for q in negatives if q.score >= threshold)
    return ThresholdMetrics(
        threshold=threshold,
        tpr=admitted_positives / len(positives),
        fpr=admitted_negatives / len(negatives),
        n_pos=len(positives),
        n_neg=len(negatives),
    )


def _candidate_thresholds(scored: list[ScoredQuestion]) -> list[float]:
    """The distinct observed scores, ascending — the ROC operating points of this set."""
    return sorted({q.score for q in scored})


def select_threshold_youden(scored: list[ScoredQuestion]) -> float:
    """Return the threshold maximizing Youden's J (tpr - fpr).

    Ties break toward the higher threshold, which admits less leakage — the gate's job is
    to keep out-of-domain traffic out of the paid agent loop.
    """
    best_threshold = 0.0
    best_j: float | None = None
    for candidate in _candidate_thresholds(scored):
        metrics = threshold_metrics(scored, candidate)
        youden_j = metrics.tpr - metrics.fpr
        if (
            best_j is None
            or youden_j > best_j
            or (youden_j == best_j and candidate > best_threshold)
        ):
            best_j = youden_j
            best_threshold = candidate
    return best_threshold


def threshold_at_max_fpr(scored: list[ScoredQuestion], max_fpr: float) -> float:
    """Return the lowest threshold whose leakage (fpr) stays at or below ``max_fpr``.

    Among the thresholds meeting the ceiling, prefer the highest true-positive rate; break
    ties toward the lowest threshold (least restrictive that still complies). When no
    observed score meets the ceiling, return a threshold just above the maximum score,
    which admits nothing (fpr = 0).
    """
    best_threshold: float | None = None
    best_tpr: float | None = None
    for candidate in _candidate_thresholds(scored):
        metrics = threshold_metrics(scored, candidate)
        if metrics.fpr > max_fpr:
            continue
        if (
            best_tpr is None
            or metrics.tpr > best_tpr
            or (
                metrics.tpr == best_tpr
                and best_threshold is not None
                and candidate < best_threshold
            )
        ):
            best_tpr = metrics.tpr
            best_threshold = candidate
    if best_threshold is None:
        return max(q.score for q in scored) + _ADMIT_EPSILON
    return best_threshold


# --------------------------------------------------------------------------------------
# Live measurement. These functions reach the configured model provider (Groq or local
# Ollama) and the vector store (Qdrant); their heavy dependencies are imported lazily so
# the pure math above stays importable in CI without those services.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentProbeResult:
    """What a single real call to the configured agent model reports about token usage.

    ``total_tokens_via_runtime`` is the count the live ``TokenBudgetHandler`` would
    accumulate from this call — the number the budget actually enforces against. A
    non-positive value means the budget is inert for this provider. ``llm_output`` and
    ``usage_metadata`` are captured raw so a missed location can be diagnosed.
    """

    total_tokens_via_runtime: int
    llm_output: dict[str, Any] | None
    usage_metadata: dict[str, Any] | None


def probe_agent_token_report() -> AgentProbeResult:
    """Make one real call to the configured agent model and report the token total the budget sees.

    Uses ``default_model()`` so it probes whatever ``agent_provider`` selects, and reuses
    ``TokenBudgetHandler`` as the meter (a budget large enough never to fire), so the measured
    total is exactly what the runtime accumulates in ``on_llm_end`` — not a parallel
    reimplementation that could read a different field.
    """
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult

    from agent.factory import default_model
    from agent.limits import TokenBudgetHandler

    captured: dict[str, LLMResult] = {}

    class _CaptureLLMResult(BaseCallbackHandler):
        def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
            captured["result"] = response

    model = default_model()
    message = model.invoke(
        "Reply with the single word: ok.",
        config={"callbacks": [_CaptureLLMResult()]},
    )

    result = captured.get("result")
    meter = TokenBudgetHandler(budget=10**12)
    if result is not None:
        meter.on_llm_end(result)
    return AgentProbeResult(
        total_tokens_via_runtime=meter.total,
        llm_output=result.llm_output if result is not None else None,
        usage_metadata=getattr(message, "usage_metadata", None),
    )


@dataclass(frozen=True)
class AgentRunMeasurement:
    """One real agent run: the super-steps and tokens it consumed, and whether it was cut off."""

    question: str
    steps: int
    total_tokens: int
    hit_recursion_limit: bool


@dataclass(frozen=True)
class CalibrationEvidence:
    """Everything one calibration run measured, ready to serialize and freeze as a fixture."""

    embed_model: str
    agent_model: str
    scored: list[ScoredQuestion]
    runs: list[AgentRunMeasurement]
    probe_total_tokens: int


def generate_in_domain_questions(num: int, *, seed: int, model: str | None = None) -> list[str]:
    """Derive ``num`` in-domain questions from the ingested corpus via the eval generator.

    Seeded chunk shuffling keeps the run reproducible while sampling across the corpus
    rather than always drawing from its first pages.
    """
    import random

    from eval.generate_questions import (
        DEFAULT_GROQ_MODEL,
        collect_files,
        extract_text,
        generate_questions_groq,
    )

    model = model or DEFAULT_GROQ_MODEL
    files = collect_files(str(_ARCHIVES_DIR))
    text = "\n\n".join(extract_text(path) for path in files)
    chunks = [chunk for chunk in _split_chunks(text) if chunk.strip()]
    random.Random(seed).shuffle(chunks)

    questions: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if len(questions) >= num:
            break
        for question in generate_questions_groq(chunk, _QUESTIONS_PER_CHUNK, model):
            key = question.lower().strip()
            if key not in seen:
                seen.add(key)
                questions.append(question)
    return questions[:num]


def _split_chunks(text: str) -> list[str]:
    from eval.generate_questions import split_into_chunks

    return split_into_chunks(text)


def generate_out_of_domain_questions(
    num: int, *, model: str | None = None, seed: int | None = None
) -> list[str]:
    """Generate ``num`` deliberately non-agricultural questions via Groq.

    ``seed`` (when set) is passed to Groq for best-effort determinism, varied per batch so the
    batches differ. LLM generation is not guaranteed reproducible, so the frozen fixture — not a
    live regeneration — is the authoritative calibration evidence.
    """
    import os

    from groq import Groq

    from eval.generate_questions import DEFAULT_GROQ_MODEL, parse_questions_json

    model = model or DEFAULT_GROQ_MODEL
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    questions: list[str] = []
    seen: set[str] = set()
    max_rounds = (num // _NEGATIVE_BATCH) + 4
    for round_index in range(max_rounds):
        if len(questions) >= num:
            break
        want = min(_NEGATIVE_BATCH, num - len(questions))
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": _OUT_OF_DOMAIN_PROMPT.format(num_questions=want)}
            ],
            temperature=0.7,
            max_tokens=2000,
            seed=None if seed is None else seed + round_index,
        )
        content = (response.choices[0].message.content or "").strip()
        for question in parse_questions_json(content):
            key = question.lower().strip()
            if key not in seen:
                seen.add(key)
                questions.append(question)
    return questions[:num]


def _warm_embedder(timeout: float = 60.0) -> None:
    """Load the embedding model with a generous timeout before the sweep.

    The runtime embed client uses an aggressive ~5s timeout (``ollama_embed_timeout``),
    which the ~8s cold-start of ``nomic-embed-text`` trips; warm calls are ~1.5s. A one-off
    client with a long timeout loads the model so the runtime path scores without timing out.
    """
    from ollama import Client as OllamaClient

    from core.config import settings

    OllamaClient(timeout=timeout).embeddings(model=settings.embed_model, prompt="warm up")


def score_questions(questions: list[str], *, in_domain: bool) -> list[ScoredQuestion]:
    """Score each question with the gate's own signal: top corpus cosine similarity."""
    from retrieval import generate_embedding, top_similarity

    scored: list[ScoredQuestion] = []
    for question in questions:
        similarity = top_similarity(generate_embedding(question))
        if similarity is None:
            continue
        scored.append(ScoredQuestion(score=float(similarity), in_domain=in_domain))
    return scored


def measure_agent_run(question: str, *, recursion_ceiling: int) -> AgentRunMeasurement:
    """Run the real agent once and record super-steps (stream updates) and total tokens.

    Reuses the runtime's own input builder and token accounting so the measurement matches
    what the deployed ``invoke_agent`` path consumes. A generous ``recursion_ceiling`` lets a
    run reveal its true step need; a run that still hits it is flagged rather than silently
    truncating the evidence.
    """
    from langgraph.errors import GraphRecursionError

    from agent.factory import get_agent
    from agent.limits import TokenBudgetHandler
    from agent.runner import _build_input
    from core.schemas import ExpertiseLevel, UserProfile

    graph = get_agent()
    meter = TokenBudgetHandler(budget=10**12)
    profile = UserProfile(name="calibration", expertise=ExpertiseLevel.intermediate)
    config = {"recursion_limit": recursion_ceiling, "callbacks": [meter]}
    graph_input = _build_input(question, [], profile)

    steps = 0
    hit_limit = False
    try:
        for _update in graph.stream(graph_input, config, stream_mode="updates"):
            steps += 1
    except GraphRecursionError:
        hit_limit = True
    return AgentRunMeasurement(
        question=question,
        steps=steps,
        total_tokens=meter.total,
        hit_recursion_limit=hit_limit,
    )


def run_calibration(
    *,
    num_positives: int,
    num_negatives: int,
    recursion_ceiling: int,
    num_agent_runs: int | None = None,
    seed: int = _DEFAULT_SEED,
) -> CalibrationEvidence:
    """Probe the agent model, score both question classes, and measure the agent over the positives.

    ``num_agent_runs`` bounds how many in-domain questions feed the agent measurement; ``None``
    measures every positive. The intent sweep always scores all questions.
    """
    from core.config import settings

    probe = probe_agent_token_report()
    if probe.total_tokens_via_runtime <= 0:
        # Fail before spending the agent runs: a zero here means the same extractor would read
        # zero for every run, so agent_token_budget would be "calibrated" from inert accounting.
        raise RuntimeError(
            "token accounting is inert: the agent model reported no total_tokens where the runtime "
            "budget reads it. Fix the provider or _extract_total_tokens before calibrating."
        )
    positives = generate_in_domain_questions(num_positives, seed=seed)
    negatives = generate_out_of_domain_questions(num_negatives, seed=seed)
    _warm_embedder()
    scored = score_questions(positives, in_domain=True) + score_questions(
        negatives, in_domain=False
    )

    to_measure = positives if num_agent_runs is None else positives[:num_agent_runs]
    runs: list[AgentRunMeasurement] = []
    for index, question in enumerate(to_measure):
        try:
            runs.append(measure_agent_run(question, recursion_ceiling=recursion_ceiling))
            logger.info("calibrate.agent_run.done", extra={"index": index, "of": len(to_measure)})
        except Exception as exc:
            # A failed run (e.g. a transient local-model load error) yields no valid sample;
            # drop it but log it so the dropped count stays visible, not silently shrinking evidence.
            logger.warning("calibrate.agent_run.dropped", extra={"index": index, "error": str(exc)})

    return CalibrationEvidence(
        embed_model=settings.embed_model,
        agent_model=settings.agent_model,
        scored=scored,
        runs=runs,
        probe_total_tokens=probe.total_tokens_via_runtime,
    )


def evidence_to_dict(evidence: CalibrationEvidence, *, seed: int) -> dict[str, Any]:
    """Serialize evidence to the frozen-fixture schema the guard tests consume."""
    return {
        "metadata": {
            "embed_model": evidence.embed_model,
            "agent_model": evidence.agent_model,
            "seed": seed,
            "generated_via": "eval/calibrate_agent.py",
        },
        "scored": [{"score": s.score, "in_domain": s.in_domain} for s in evidence.scored],
        "runs": [
            {
                "question": r.question,
                "steps": r.steps,
                "total_tokens": r.total_tokens,
                "hit_recursion_limit": r.hit_recursion_limit,
            }
            for r in evidence.runs
        ],
        "probe": {"total_tokens_via_runtime": evidence.probe_total_tokens},
    }


def _recommend_bound(values: list[int]) -> tuple[int, int, int]:
    """Return (p95, observed_max, recommended) for a list of measured per-run values."""
    import math

    import numpy as np

    observed_max = max(values)
    p95 = int(math.ceil(float(np.percentile(values, 95))))
    recommended = int(math.ceil(max(p95, observed_max) * _BOUND_SAFETY_FACTOR))
    return p95, observed_max, recommended


def main() -> int:
    import argparse
    import json
    import sys

    # Make the project packages (core, agent, retrieval) importable when run as a standalone
    # script; pytest adds the root via pythonpath, but `python eval/calibrate_agent.py` does not.
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Calibrate the agent domain gate and loop bounds")
    parser.add_argument(
        "--num-questions", type=int, default=60, help="in-domain positives to sample"
    )
    parser.add_argument(
        "--num-negatives", type=int, default=60, help="out-of-domain negatives to generate"
    )
    parser.add_argument(
        "--num-agent-runs", type=int, default=12, help="in-domain questions fed to the agent"
    )
    parser.add_argument(
        "--recursion-ceiling", type=int, default=30, help="generous step ceiling for measurement"
    )
    parser.add_argument("--seed", type=int, default=_DEFAULT_SEED, help="seed for chunk sampling")
    parser.add_argument(
        "--output", default=str(_DEFAULT_EVIDENCE_PATH), help="evidence artifact path"
    )
    args = parser.parse_args()

    evidence = run_calibration(
        num_positives=args.num_questions,
        num_negatives=args.num_negatives,
        num_agent_runs=args.num_agent_runs,
        recursion_ceiling=args.recursion_ceiling,
        seed=args.seed,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(evidence_to_dict(evidence, seed=args.seed), handle, ensure_ascii=False, indent=2)

    youden = select_threshold_youden(evidence.scored)
    capped = threshold_at_max_fpr(evidence.scored, max_fpr=0.05)
    # Runs that hit the recursion ceiling are censored (steps/tokens truncated at the ceiling), so
    # they under-report the true need; exclude them from the bound recommendations.
    completed = [r for r in evidence.runs if not r.hit_recursion_limit]
    hit = len(evidence.runs) - len(completed)
    if not completed:
        print(
            f"ERROR: all {hit} agent run(s) hit the recursion ceiling; raise --recursion-ceiling."
        )
        return 1
    steps = [r.steps for r in completed]
    tokens = [r.total_tokens for r in completed]
    steps_p95, steps_max, recursion_limit = _recommend_bound(steps)
    tokens_p95, tokens_max, token_budget = _recommend_bound(tokens)
    n_pos = sum(1 for s in evidence.scored if s.in_domain)
    n_neg = sum(1 for s in evidence.scored if not s.in_domain)

    print(f"\nEvidence written to: {output_path}")
    print(
        f"scored: {n_pos} positives, {n_neg} negatives | agent runs: {len(evidence.runs)} "
        f"({hit} censored, bounds from {len(completed)})"
    )
    print("\n--- intent_threshold ---")
    print(
        f"  Youden's J:              {youden:.4f}  -> {threshold_metrics(evidence.scored, youden)}"
    )
    print(
        f"  max leakage FPR <= 0.05: {capped:.4f}  -> {threshold_metrics(evidence.scored, capped)}"
    )
    print("\n--- agent_recursion_limit ---")
    print(f"  steps p95={steps_p95} max={steps_max} -> recommended {recursion_limit}")
    print("\n--- agent_token_budget ---")
    print(f"  tokens p95={tokens_p95} max={tokens_max} -> recommended {token_budget}")
    print(f"\nprobe total_tokens_via_runtime: {evidence.probe_total_tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
