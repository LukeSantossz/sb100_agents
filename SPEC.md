# SPEC: fix(verification): degrade to neutral 0.5 when the verifier API key is missing

## Problem
When the configured verifier provider (groq/openrouter) has no API key, `compute_entropy_score`
returns 0.0 — reported to the user as "fully grounded/trustworthy" — instead of the neutral 0.5.

## Design Decision
Raise a dedicated `MissingVerifierKeyError` from `compute_entropy_score`'s two missing-key branches
(`verification/entropy.py`). Both gate paths (`evaluate`, `score_context`) catch it specifically, log
a warning, and return `NEUTRAL_SCORE`. This short-circuits to neutral without entering the retry loop —
consistent with how the gate already treats a verifier that cannot run — and keeps the missing-key case
off the broad `except`'s traceback log.

## Alternatives Considered
1. Return 0.5 directly from entropy — rejected: it flows through `evaluate`'s threshold comparison, so at
   a threshold < 0.5 it would spuriously retry and replace the answer with FALLBACK_MESSAGE; it also puts
   the gate's neutral-policy concept inside entropy.
2. Leave as-is — rejected: violates the AC (reports a confident 0.0 for an unverifiable answer).

## Scope
- Includes: `verification/entropy.py` (new `MissingVerifierKeyError`, raise in the two missing-key
  branches, docstring); `verification/gate.py` (narrow `except MissingVerifierKeyError` in `evaluate` and
  `score_context` → warning log + `NEUTRAL_SCORE`, before the existing broad except).
- Does NOT include: present-key behavior; the ollama provider (needs no key); the retry/threshold logic.

## Acceptance Criteria
- compute_entropy_score_raises_missing_key_error_when_groq_key_absent
- compute_entropy_score_raises_missing_key_error_when_openrouter_key_absent
- evaluate_returns_neutral_score_when_verifier_key_missing
- score_context_returns_neutral_score_when_verifier_key_missing
- gate_logs_warning_not_traceback_when_verifier_key_missing
- verification_with_present_key_unchanged

## Reproducibility
`pytest tests/test_verification.py -m "not requires_infra"`
Versions: as pinned in uv.lock (groq, openai, ollama).

## Risks and Assumptions
- Assumption: no caller depends on the current 0.0 missing-key return.
- ollama needs no key, so its path is unaffected.
