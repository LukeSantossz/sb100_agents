# Calibrated agent domain-gate threshold and loop bounds

The agent's three safety knobs shipped as guessed defaults: `intent_threshold=0.3` (ADR-0010
domain gate), `agent_recursion_limit=25`, and `agent_token_budget=100000` (ADR-0012 loop bounds).
`intent_threshold=0.3` was far too low — on the nomic-embed-text similarity scale essentially
every question scores above 0.3, so the gate leaked all out-of-domain traffic. We calibrated all
three against the live environment (the local `qwen2.5:7b` agent from ADR-0013, `nomic-embed-text`
embeddings, the 521-chunk corpus) with a reproducible harness, `eval/calibrate_agent.py`, and set
evidence-backed defaults.

## Status

Accepted. `agent_enabled` remains `False` — flipping it is a separate decision; this only makes the
knobs defensible for when it is turned on.

## Method and evidence

- **`intent_threshold` → 0.80.** Scored 60 corpus-derived in-domain positives (via
  `eval/generate_questions.py`) and 60 LLM-generated out-of-domain negatives with the gate's own
  `retrieval.top_similarity` signal. Distributions: positives `[0.760, 0.896]` (median 0.842),
  negatives `[0.688, 0.817]` (median 0.762) — overlapping only in ~0.76–0.82. At **0.80** the gate
  admits **96.7%** of in-domain questions and leaks **3.3%** of out-of-domain ones (TPR 0.967, FPR
  0.033), meeting the target operating point (TPR ≥ 0.90, FPR ≤ 0.05). The score gate separates
  adequately, so the ADR-0010 escalation to a few-shot topic classifier is **not** taken.
- **`agent_recursion_limit` → 15** and **`agent_token_budget` → 30000.** Ran 12 real agent turns on
  in-domain questions, counting LangGraph super-steps (`graph.stream(stream_mode="updates")`) and
  cumulative `total_tokens` (the runtime `TokenBudgetHandler` as a non-raising meter). Observed:
  steps max 9 (p95 8; almost all runs used 6), tokens max 19663 (p95 17752). Defaults set to ≈1.5×
  the observed max as a runaway backstop with headroom; no run hit the ceiling.
- **Token accounting confirmed live.** The probe verified `qwen2.5:7b` reports `total_tokens` via the
  message `usage_metadata` the budget reads (the fallback added in ADR-0013), so the budget is not
  inert for the local provider.

The measured evidence is frozen at `tests/fixtures/calibration_evidence.json`; guard tests assert
each default still respects it (threshold within TPR/FPR targets; bounds ≥ frozen p95 and max),
running offline in CI with no live services.

## Considered Options

- **Evidence-backed defaults from a reproducible harness (chosen)**: replaces guesses with measured
  values and a committed fixture that guards against regressions. Reproducible via
  `python eval/calibrate_agent.py`.
- **Keep the guessed defaults**: rejected — `intent_threshold=0.3` leaked 100% of out-of-domain
  traffic into the agent loop, defeating ADR-0010.
- **Escalate the gate to a few-shot classifier (ADR-0010)**: unnecessary — the retrieval-score gate
  separates the classes at an acceptable operating point. Remains the documented path if the corpus
  or embedding model changes degrade separation.
- **Tighten the bounds to exactly the observed max**: rejected — a 12-run sample is small, so a 1.5×
  safety factor guards against unseen longer runs while still tightening the cost/runaway backstop.

## Consequences

- The domain gate now actually gates: ~3.3% of out-of-domain questions still leak (the negatives
  scoring 0.80–0.817) and ~3.3% of in-domain questions are over-blocked (positives below 0.80) — an
  acceptable trade recorded here, adjustable via `INTENT_THRESHOLD`.
- The `intent_threshold` value is tied to the `nomic-embed-text` similarity scale; the pending
  nomic task-prefix change (#106) would shift it and require rerunning the sweep (ADR-0010). The
  fixture records the embed model it was produced with.
- The loop bounds are calibrated for `qwen2.5:7b`; a different agent model needs a fresh run. On the
  local provider tokens are free, so `agent_token_budget` is a runaway/time backstop rather than a
  cost cap; both bounds stay configurable and terminate into the ADR-0012 graceful fallback.
