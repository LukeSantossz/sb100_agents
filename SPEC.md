# SPEC: feat(agent): agricultural intent filter before the agent loop

## Problem

When the agentic `/chat` path is enabled, every question — including ones unrelated to the
indexed agricultural corpus — enters the deep-agent loop, spending model and tool calls on
out-of-domain queries the assistant is not meant to answer.

## Design Decision

Add a cheap pre-flight domain gate on the agent path, in a new `agent/intent.py`, invoked
before `invoke_agent`. It embeds the user question with the existing local embedder and measures
the single best cosine similarity against the indexed corpus via a new `top_similarity` helper in
`retrieval/vector_store.py` (Qdrant query with `limit=1`). If that score is below a configurable
threshold, the request short-circuits with a fixed out-of-domain answer and never enters the loop;
otherwise it proceeds unchanged. The corpus is the domain reference — no hardcoded anchors and no
labels — so the gate stays aligned with whatever is ingested and scales to the project's ~500-document
target. This is a deliberately cheap, single-step gate (a "semantic routing" / input topic guardrail,
per `llm-wiki/wiki/transformacao-queries.md` and `llm-wiki/wiki/salvaguardas-llm.md`); a few-shot topic
classifier is the documented escalation if measurement shows the score gate is insufficient.

## Alternatives Considered

- **Few-shot topic classifier (SetFit or embeddings + logistic regression).** Truly classifies
  "agricultural vs not" independent of corpus coverage, but requires a labeled example set, a model
  artifact, and a new dependency. Rejected as premature before measurement justifies it; recorded as
  the escalation path.
- **Cheap LLM judge (a Groq yes/no call before the loop).** Robust to phrasing, but adds an online,
  paid, non-deterministic call before the very loop we are trying to avoid spending on, needs
  `GROQ_API_KEY`, and complicates network-free testing. Rejected.
- **Embedding similarity to a corpus centroid or hardcoded anchors.** Corpus-derivable, but a global
  centroid blurs across ~500 diverse documents (weak separation) and hardcoded anchors drift and need
  manual upkeep. Rejected: the retrieval-score gate reuses the corpus index directly with no extra
  reference to maintain.
- **Prompt-level refusal (instruct the agent to refuse off-topic).** Zero infrastructure, but does not
  deflect before the loop (no cost saved), is less reliable, and does not strictly isolate the domain.
  Rejected.

## Scope

Includes:

- `agent/intent.py`: `DomainDecision` (frozen dataclass: `in_domain: bool`, `score: float | None`),
  `classify_domain(question: str) -> DomainDecision`, and the user-facing constant
  `OUT_OF_DOMAIN_MESSAGE = "Só respondo sobre temas agrícolas cobertos pela base de documentos. Reformule sua pergunta nesse domínio."`
  (Portuguese, per the user-facing-copy assumption below).
- `retrieval/vector_store.py`: `top_similarity(embedding: list[float]) -> float | None` — Qdrant query
  with `limit=1`, returns the top point's score, or `None` when no points are returned.
- `core/config.py`: `intent_filter_enabled: bool = True` and `intent_threshold: float` validated to
  `0.0..1.0`, with a provisional permissive default (`0.3`).
- `api/routes/chat.py`: in the agent branch, before `invoke_agent`, call `classify_domain` when
  `intent_filter_enabled`; emit a structured `chat.intent` log (in_domain, score, threshold, username);
  on out-of-domain, return `OUT_OF_DOMAIN_MESSAGE` with `hallucination_score = 0.0`, record the turn in
  the conversation buffer, and skip the loop.
- Export the new symbols from `agent/__init__.py`.
- Network-free unit tests for `classify_domain` and `top_similarity`, and route tests for the
  short-circuit and pass-through behaviour.

Does NOT include:

- Calibrating `intent_threshold` against real data. This is a follow-up on the pre-enablement
  checklist (with #177 and #178) that must run before `agent_enabled` goes live in any real
  environment.
- The few-shot classifier escalation (only if measurement demands it).
- Applying the gate to the legacy (non-agent) `/chat` path.
- Reusing `top_similarity` for source citations (#123) or retrieval filtering (#126); those remain
  their own Wave B slices.
- LLM-based relevance grading, query transformation / HyDE, reranking, hybrid search, or web fallback.
- nomic task-prefix changes (#106), which would shift the score scale and force threshold recalibration.

## Acceptance Criteria

- `classify_domain_returns_in_domain_when_top_similarity_at_or_above_threshold`
- `classify_domain_returns_out_of_domain_when_top_similarity_below_threshold`
- `classify_domain_decision_carries_the_measured_score`
- `classify_domain_fails_open_to_in_domain_when_top_similarity_is_none_or_raises` (and logs the failure)
- `top_similarity_returns_top_point_score_for_a_nonempty_result`
- `top_similarity_returns_none_when_no_points_are_returned`
- `chat_agent_path_short_circuits_out_of_domain_without_calling_invoke_agent` (returns the fixed
  message with `hallucination_score == 0.0`)
- `chat_agent_path_records_the_out_of_domain_turn_in_the_buffer`
- `chat_agent_path_proceeds_to_invoke_agent_when_in_domain`
- `chat_intent_decision_is_emitted_as_a_structured_log_field`
- `intent_threshold_rejects_values_outside_0_1`
- `intent_filter_disabled_bypasses_the_gate_and_calls_invoke_agent`

## Reproducibility

- Tests: `pytest tests/ -m "not requires_infra"` — network-free; the embedder, `top_similarity`, and
  `invoke_agent` are stubbed/monkeypatched following the existing test patterns.
- Lint and types: `ruff check .`; `mypy agent/ retrieval/ core/ --strict`.
- Versions: as pinned in `pyproject.toml` / `uv.lock` (Python 3.12+).
- Threshold calibration (manual, infra-bound, out of this slice): embed a small labeled probe set
  (agricultural-in-corpus, agricultural-out-of-corpus, clearly off-domain) against a populated Qdrant
  collection and pick the threshold that best separates by F1 / recall.

## Risks and Assumptions

- Assumption: the Qdrant collection uses cosine similarity and is populated, so `top_similarity`
  returns a comparable `0..1`-range score. An empty or missing collection yields `None`, which the gate
  treats as fail-open (see next point) rather than blocking all traffic.
- Decision: the gate fails open. On any embedding/search error or a `None` top score, `classify_domain`
  returns `in_domain=True` and logs the failure. Rationale: the agent path uses the same retrieval, so
  if it is down the agent itself would fail; availability is preferred over hard-blocking on infra
  trouble or misconfiguration.
- Risk: `intent_threshold` has no empirical basis yet; the provisional permissive default may under-block
  (let some off-domain questions through). Mitigated by the permissive default failing safe for UX,
  structured logs enabling monitoring, and calibration being a gating checklist item before real
  enablement. Escalation to the few-shot classifier is the response if measurement shows topic leakage
  or over-blocking.
- Risk: the gate performs one extra embed + search before the loop, duplicating the agent's own
  retrieval for in-domain requests. Accepted; not optimized in this slice.
- Risk: #106 (nomic task prefixes) would change the similarity scale and require threshold
  recalibration. Flagged.
- Assumption: the off-domain user-facing message is Portuguese (the product targets Brazilian
  agriculture; code, comments, and this SPEC remain English per the standards). Invalidated if the
  product decides on English user-facing copy.
- Assumption: `intent_filter_enabled=True` by default is acceptable because the agent path is itself
  gated by `agent_enabled=False`, so the gate stays dormant until the agent path is enabled.

## Design Decision promotion (Spec Gate)

Promoted at the Gate to [ADR-0010](docs/adr/0010-domain-gate-retrieval-score.md): "Agricultural domain
gate via corpus retrieval score (a coverage proxy), not a topic classifier, with a staged escalation to
a few-shot classifier." The durable rationale lives in the ADR and is indexed by the README Engineering
Decisions section per `docs/adr/0001-decision-records-flow.md`.
