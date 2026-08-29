# SPEC: fix(verification): do not report a grounded answer when sampling partially failed

## Problem

When the verification provider fails some but not all sample calls,
`compute_entropy_score` computes entropy over the surviving samples, and with the
default of two samples a single failure leaves one sample, one cluster, and a
score of `0.0`, which the gate reads as a confidently grounded answer.

## Design Decision

Entropy over one sample is not a low value, it is no value: a distribution needs
at least two observations. `compute_entropy_score` raises
`InsufficientSamplesError` when fewer than two came back, and the gate maps it to
the neutral score exactly as it already maps a missing API key, with a warning
rather than a traceback because it is a degraded path and not a crash. A run that
loses some samples but keeps at least two still scores, because the entropy over
those is real information; losing that would make a flaky provider silently
disable verification, which is the same class of failure pointed the other way.

## Alternatives Considered

- **Return the neutral score for any partial failure**, not only below two. It is
  what the issue proposes first, and it is safer in the sense that fewer numbers
  are trusted. Rejected because entropy over two of three samples is a real
  measurement, and discarding it means one flaky call turns verification off
  while still reporting a number that looks deliberate.
- **Have `_generate_samples` re-raise on any failure.** The tolerance exists on
  purpose, so one 429 does not fail the whole request, and removing it would turn
  a degraded score into a 503 for the user.
- **Return `0.5` directly from `compute_entropy_score`.** The neutral score is the
  gate's policy and its constant. Duplicating the value in the entropy module
  puts the same decision in two places, and the entropy module has no business
  deciding what a caller does when it cannot answer.

## Scope

- Includes: `InsufficientSamplesError` in `verification/entropy.py`, raised below
  two samples; both gate entry points mapping it to `NEUTRAL_SCORE`; a warning
  when samples are lost but enough remain; tests.
- Does NOT include: changing `entropy_num_samples`, the partial-failure tolerance
  in `_generate_samples`, retry policy, or the clustering threshold.

## Acceptance Criteria

- `one_surviving_sample_does_not_score_zero`: with two requested and one failing,
  `compute_entropy_score` raises rather than returning `0.0`.
- `the_gate_returns_the_neutral_score`: `evaluate` and `score_context` both return
  `0.5` in that case, and the answer is still delivered.
- `two_surviving_samples_still_score`: with three requested and one failing, a
  real entropy value is returned and a warning records the loss.
- `no_surviving_samples_still_propagates`: the existing behaviour when every call
  fails is unchanged.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_verification.py -v`, with the provider
sample function patched to fail a chosen number of calls.

## Risks and Assumptions

- Assumption: two samples is the floor for a meaningful distribution. It follows
  from the definition; `entropy_num_samples` is already validated `>= 2`.
- What would invalidate this spec: a scoring method that does not need multiple
  samples, which would remove the failure mode rather than change its threshold.
