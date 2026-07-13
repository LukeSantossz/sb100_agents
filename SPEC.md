# SPEC: chore(agent): calibrate the domain gate and loop bounds before enabling the agent

## Problem

The agent's three safety knobs — `intent_threshold`, `agent_recursion_limit`, and
`agent_token_budget` — hold guessed defaults that were never measured, and the token
budget may be inert because it is unknown whether Groq reports `total_tokens` where
`agent/limits.py` reads it; `agent_enabled` cannot be turned on responsibly until these
are calibrated against the live environment with evidence.

## Design Decision

Add a reproducible harness, `eval/calibrate_agent.py`, that reuses the existing `eval/`
provider plumbing to produce three measurements against the live environment, in this
order: (1) a Groq probe that captures one real `on_llm_end` `LLMResult` and confirms
whether `total_tokens` is reported where `TokenBudgetHandler._extract_total_tokens`
reads it; (2) an `intent_threshold` sweep over corpus-derived in-domain positives
(reusing `eval/generate_questions.py`) and LLM-generated out-of-domain negatives,
scoring each with the same `retrieval.top_similarity` signal the gate uses, and
reporting leakage (false positives) and over-block (false negatives) across candidate
thresholds; (3) a loop-bounds measurement that runs the real compiled agent over the
in-domain questions and records, per run, the exact number of LangGraph super-steps
(counted from `graph.stream(..., stream_mode="updates")`) and the cumulative
`total_tokens` (a non-raising metering callback). The harness freezes its evidence to a
committed fixture; guard tests assert the chosen defaults hold on that frozen evidence
without any live service; the defaults land in `core/config.py`; and ADR-0013 records
the methodology, the evidence, and the chosen values. If the Groq probe shows
`total_tokens` reported elsewhere (e.g. `usage_metadata` on the `AIMessage`),
`_extract_total_tokens` is fixed test-first as part of this change, since an inert token
budget is a correctness defect in the bound.

## Alternatives Considered

- **Few-shot topic classifier for the gate** (SetFit or embeddings + logistic
  regression): the ADR-0010 escalation path. Rejected for now — it adds a labeled
  training set, a model artifact, and a dependency; it is taken only if the score gate
  proves inadequate, which this calibration is what measures. Escalation stays available
  if the sweep cannot separate positives from negatives at an acceptable operating point.
- **Hand-written out-of-domain negatives fixture**: simplest and deterministic, but a
  static hardcoded list is not reproducible and drifts from the corpus; rejected in favor
  of LLM-generated negatives produced by the same reproducible machinery as the positives.
- **Leave the defaults as guesses and enable the agent**: zero work, but it defeats the
  ADR-0010 requirement, risks leaking out-of-domain traffic into a paid loop or
  over-blocking valid questions, and leaves the token budget possibly inert. Rejected.
- **Estimate tokens locally with a tokenizer instead of trusting the provider**: would
  make the budget provider-independent, but it double-counts prompt construction the
  provider already meters and diverges from actual billing; rejected in favor of first
  confirming the provider's own report, which is what the runtime bound consumes.

## Scope

- Includes:
  - `eval/calibrate_agent.py`: the harness (Groq probe, threshold sweep, loop-bounds
    measurement), reusing `eval/` provider plumbing and `eval/generate_questions.py`.
  - Generation of LLM-based out-of-domain negatives (non-agricultural prompt), reproducible.
  - A committed evidence fixture (frozen `(score, label)` pairs plus step/token
    distributions and the captured Groq `LLMResult` shape) for offline guard tests.
  - Guard tests that run in CI without Qdrant or Groq.
  - Updated defaults for `intent_threshold`, `agent_recursion_limit`, `agent_token_budget`
    in `core/config.py`.
  - A test-first fix to `agent/limits.py::_extract_total_tokens` **only if** the probe
    shows Groq reports `total_tokens` in a location the current extractor misses.
  - ADR-0013 plus a README Engineering Decisions row.
- Does NOT include:
  - Flipping `agent_enabled` to `True` (a separate decision after these values land).
  - Replacing the retrieval-score gate with a topic classifier (ADR-0010 escalation).
  - Any change to `agent/intent.py`, `agent/runner.py`, or the gate/runtime logic beyond
    the possible `_extract_total_tokens` fix.
  - Streaming, retrieval, or generation changes; anything in the open backlog (#95–#133).
  - Tuning `entropy_num_samples`, `hallucination_threshold`, or any non-agent knob.

## Acceptance Criteria

- `groq_probe_reports_total_tokens_as_positive_int`: the probe captures a real
  `on_llm_end` `LLMResult` from `ChatGroq(settings.agent_model)` and asserts a positive
  integer `total_tokens` is present at the location the runtime reads.
- `extract_total_tokens_reads_the_real_groq_shape`: a unit test builds an `LLMResult` in
  the exact shape the probe captured and asserts `_extract_total_tokens` returns the
  positive total (this test is the red step of the fix if the probe reveals a missed
  location; otherwise it locks the confirmed shape).
- `chosen_threshold_separates_frozen_probe_within_targets`: on the frozen evidence, the
  selected `intent_threshold` yields true-positive rate ≥ 0.90 and false-positive
  (leakage) rate ≤ 0.05; if no threshold meets both, the harness reports it and the ADR
  records the ADR-0010 escalation decision instead of forcing a value.
- `recursion_limit_default_is_at_least_frozen_p95_steps`: the configured
  `agent_recursion_limit` is ≥ the frozen p95 observed super-steps, and ≥ the observed
  maximum, and no calibration run raised `GraphRecursionError` at the chosen limit.
- `token_budget_default_is_at_least_frozen_p95_tokens`: the configured
  `agent_token_budget` is ≥ the frozen p95 observed per-run `total_tokens`, and ≥ the
  observed maximum.
- `guard_tests_pass_without_live_services`: the guard suite runs under
  `pytest -m "not requires_infra"` with no Qdrant or Groq reachable.

## Reproducibility

- Command: `python eval/calibrate_agent.py --num-questions 60 --num-negatives 60`
  (run from an environment with `GROQ_API_KEY` set, Qdrant reachable at
  `settings.qdrant_url`, and the corpus already ingested into `settings.collection_name`).
- Seed: `random.seed(42)`, matching the existing eval pipeline, for question sampling and
  any ordering.
- Relevant versions: Python 3.12; dependencies pinned by `uv.lock`; embedding model
  `nomic-embed-text`; agent model `openai/gpt-oss-20b` on Groq.
- Note: the `intent_threshold` scale is tied to the embedding model and its task prefixes;
  the pending `#106` nomic task-prefix change would shift the scale and require rerunning
  the sweep (per ADR-0010). The frozen fixture records the embed model it was produced with.

## Risks and Assumptions

- Assumption: the live corpus in Qdrant is representative enough that corpus-derived
  positives reflect real in-domain traffic. Invalidated if the corpus is near-empty or
  skewed; the harness prints the positive/negative counts so a degenerate run is visible.
- Assumption: Groq reports usage deterministically enough that a p95 over ~60 runs is a
  stable bound. Invalidated by high variance; the harness prints the full distribution so
  an unstable measurement is visible before a value is chosen.
- Risk: the sweep may fail to separate positives from negatives at the target operating
  point, meaning the score gate is inadequate. This does not invalidate the spec — the
  acceptance criterion routes that outcome to the documented ADR-0010 escalation decision.
- Risk: running ~60 live agent turns consumes Groq quota and wall-clock; the harness is a
  manual, seeded, one-off tool, not part of CI, so this cost is paid only intentionally.
- Assumption: `graph.stream(..., stream_mode="updates")` yields one item per LangGraph
  super-step, making it an exact `recursion_limit` unit. Invalidated only by a LangGraph
  semantics change; the no-`GraphRecursionError` criterion cross-checks the chosen limit.
