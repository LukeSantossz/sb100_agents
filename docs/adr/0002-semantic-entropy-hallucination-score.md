# Semantic entropy for the hallucination score

SmartB100 must flag low-confidence answers without any labeled training data. We score
hallucination by generating N candidate answers, clustering them by embedding similarity, and
computing normalized Shannon entropy over the clusters — disagreement between candidates is the
signal — producing a continuous `0.0`–`1.0` Hallucination Score.

## Status

Accepted.

## Considered Options

- **Semantic entropy (chosen)**: unsupervised, continuous score derived from candidate
  disagreement; no labeled data needed.
- **Binary classifier**. Rejected — requires labeled training data the project does not have.
- **LLM-as-judge flag**. Rejected — a single judge yields a brittle binary verdict and adds a
  second opaque model call without a calibrated continuous score.

## Consequences

- No labeled data is required; the score is continuous and threshold-tunable.
- Cost scales with sample count: each verification runs N extra generations, synchronously in
  the request path. Raising N trades latency for resolution.
- At the default of 2 samples the score is effectively a binary agree/disagree signal; graded
  behavior needs N > 2. This coupling between sample count and score resolution is a known
  tuning consideration.
