# Agricultural domain gate via corpus retrieval score

The agentic `/chat` path must stay isolated to the agricultural domain. We add a cheap pre-flight
domain gate, isolated behind `agent/intent.py`, that runs before the deep-agent loop: it embeds the
user question with the local embedder and measures the single best cosine similarity against the
indexed corpus (`top_similarity`, Qdrant `limit=1`). Below a configurable threshold the request is
deflected with a fixed out-of-domain answer; otherwise it proceeds to the agent. The corpus is the
domain reference, so the gate is a *coverage proxy* for "agricultural intent" rather than a topic
classifier. A few-shot topic classifier is the documented escalation.

## Status

Accepted.

## Considered Options

- **Retrieval-score gate (chosen)**: the indexed corpus is the domain reference; one embed plus a
  top-1 vector search yields the relevance signal. No labels, no new dependency, deterministic, and it
  scales with the ~500-document ingestion target because Qdrant owns the index. It is a recognized
  cheap pattern — semantic routing / an input topic guardrail — and a score-based variant of Corrective
  RAG's relevance grading (replacing per-document LLM grading with the retrieval score).
- **Few-shot topic classifier (SetFit or embeddings + logistic regression)**: classifies "agricultural
  vs not" independent of corpus coverage, but needs a labeled set, a model artifact, and a new
  dependency. Kept as the escalation path, taken only if measurement shows the score gate leaks topic
  or over-blocks.
- **Cheap LLM judge (a Groq yes/no call before the loop)**: robust to phrasing but adds an online,
  paid, non-deterministic call before the very loop we are trying to avoid spending on, and needs
  `GROQ_API_KEY`. Rejected.
- **Embedding similarity to a corpus centroid or hardcoded anchors**: a global centroid blurs across a
  diverse corpus and hardcoded anchors drift and need upkeep. Rejected in favor of querying the index
  directly.
- **Prompt-level refusal (instruct the agent to refuse off-topic)**: zero infrastructure but does not
  deflect before the loop, is unreliable, and does not strictly isolate the domain. Rejected.

## Consequences

- The gate measures corpus *coverage*, not literal topic. A genuinely agricultural question absent from
  the corpus is deflected — acceptable for a grounded assistant that could not answer it anyway.
- `intent_threshold` is configurable and must be calibrated against a labeled probe set before the
  agent path is enabled in any real environment (the pre-enablement checklist alongside #177 and #178).
  ADR-0006-style operational care applies: the nomic task-prefix change (#106) would shift the
  similarity scale and force recalibration.
- The gate fails open: on an embedding/search error or an empty result it proceeds to the agent and
  logs the failure, preferring availability over hard-blocking on infra trouble or misconfiguration.
- It adds one embed plus one top-1 search per in-domain request, duplicating the agent's own retrieval.
  Accepted; not optimized now.
- All usage is isolated behind `agent/intent.py`, so the classifier escalation can replace it without
  touching domain modules.
