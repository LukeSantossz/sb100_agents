# SmartB100 — Agentic Migration Roadmap

Living document. It organizes the project's recorded decisions (the ADRs under
[`docs/adr/`](./adr/)) and the open GitHub Issues backlog into delivery **Waves**. The ADRs
remain the durable, authoritative decision records; this file is the operational plan that
sequences the work and is updated as Waves progress.

## Current State (2026-08-28)

- **Product:** MVP-complete RAG monolith (`/chat`: embed → search → generate → entropy-score),
  actively hardened. See the README Project Status.
- **Migration in progress (Wave A landed, flag still off):** ADR-0008 (deepagents/LangGraph as the orchestration
  substrate) and ADR-0009 (hosted Groq as the agent reasoning model, since superseded in practice by ADR-0013's
  configurable provider with a local default) are **Accepted**; a go/no-go spike
  (#163) proved the substrate. The `agent/` package now exists and Wave A slices **A1 (#170), A2 (#171),
  and A3 (#172) are merged**: the `search_corpus` tool boundary, the agent-backed `/chat` handler behind
  the `agent_enabled` flag (default off, legacy path preserved per ADR-0005), and the agricultural intent
  filter (ADR-0010). **A4 (#173, bound the agent loop) is merged** (ADR-0012), with its thresholds and bounds
  calibrated against the live environment afterwards (ADR-0015). A5 is satisfied for the score itself —
  the entropy Hallucination Score wraps the agent answer — while the retry/fallback gate behavior is
  deferred to Wave C (see the Wave C list).
- **Taxonomy:** the ADRs reference "Wave A" but never define the wave set. This document defines it.

## The Wave Model

Each Wave delivers an observable outcome and is decomposed into thin, independently shippable
slices (TDD + Spec Gate per `.standards`). Waves are ordered; the **Continuous Track** runs
alongside all of them.

| Wave | Outcome | Grounding |
|------|---------|-----------|
| **A — Agentic core** | `/chat` runs through a bounded `deepagents` agent behind an `agent/` boundary, driven by the configured agent provider, with retrieval as a tool and an agricultural intent filter. | ADR-0008, ADR-0009 (superseded on the model by ADR-0013); README "LangGraph migration" |
| **B — Retrieval quality** | The agent's retrieval tool gains source citations, score threshold/filters, corpus management, hybrid search (RRF), reranking, and per-user ACL. | ADR-0008 ("retrieval, hybrid search, reranking, ACL"); README "Hybrid search" |
| **C — Verification & trust** | Answers carry claim-level verification and per-message quality signals; the verification gate wraps the agent path. | ADR-0002; README "Claim verification" |
| **D — Conversation UX & streaming** | Durable history, SSE streaming, feedback, and export over the agentic `/chat`. | ADR-0005/0008 ("SSE slice", #132) |

### Continuous Track (not a Wave)

Runs in parallel and is not gated by the Waves: security hardening, the quality gate, observability,
eval robustness, and standalone bugfixes/features. See the mapping table for the issue list.

---

## Wave A — Agentic core

**Goal:** replace the hand-rolled synchronous chat loop with a `deepagents` agent, isolated behind an
`agent/` package, invoked synchronously (`graph.invoke(...)`) so the ADR-0005 synchronous `/chat`
contract is preserved. The Goal was written against a hosted Groq model per ADR-0009; ADR-0013 later
made the provider configurable and moved the default to a local Ollama model, and the slices below
were delivered against that. No existing issue covers Wave A — its slices need
new issues created.

| Slice | Scope | Notes |
|-------|-------|-------|
| **A1 — `agent/` scaffold + `search_corpus` tool** | Create the `agent/` package boundary; wrap the existing retrieval (`retrieval.search_context`) as a `deepagents` tool; build the agent via `create_deep_agent(model=ChatGroq(...), tools=[search_corpus])`; unit-test the wiring with a stubbed model. `/chat` unchanged. | De-risked by spike #163. Foundational; unblocks the rest. **Merged (#170).** |
| **A2 — Route `/chat` through the agent** | Add the agentic handler invoked via synchronous `graph.invoke(...)`; map agent output → `ChatResponse`; keep the legacy path switchable behind config during rollout. | Preserves ADR-0005. **Merged (#171).** |
| **A3 — Agricultural intent filter** | Cheap pre-flight classification to deflect off-domain questions before entering the agent loop. | README "agricultural intent filter". **Merged (#172, ADR-0010).** |
| **A4 — Bound the agent loop** | Enforce a recursion limit and a per-run token budget to respect Groq free-tier limits and control latency. | ADR-0009 explicitly defers this to "a later Wave A slice"; ADR-0012 realizes it and ADR-0015 calibrates the bounds. **Merged (#173).** |
| **A5 — Preserve the verification gate** | Ensure the entropy hallucination score still wraps the agent's final answer (deep claim-verification is Wave C). | ADR-0002 contract kept. **Score wrapping done; retry/fallback gate deferred to Wave C.** |

**Done when:** `/chat` answers are produced by the agent, bounded and intent-filtered, with the
existing verification score intact, behind the `agent/` boundary.

## Wave B — Retrieval quality

Better tools for the agent. Most slices already have issues.

- **#123** — source citations (`source_file` + score) in `ChatResponse` and UI *(F1; unblocks #125, #126)*
- **#126** — minimum score threshold + per-document filter in `search_context` *(shares signature with #123)*
- **#128 / #129** — corpus management endpoints + `POST /documents` ingestion *(shared router)*
- **#105 / #106 / #100** — chunker respects `settings.embed_model`; nomic task prefixes; single-PDF indexing
- **Hybrid search (RRF)** — dense + sparse vectors with reciprocal-rank fusion *(README pending; new issue)*
- **Reranking** — re-score retrieved chunks before handing context to the agent *(ADR-0008; new issue)*
- **ACL enforcement** — per-user/document access control inside retrieval *(ADR-0008; new issue)*

**Done when:** the agent's retrieval tool returns cited, filtered, hybrid-ranked, access-controlled context.

## Wave C — Verification & trust

- **#102** — neutral 0.5 fallback when samples partially fail *(removes the silent "trustworthy 0.0")*
- **#125** — per-message quality indicators (badge + empty-context warning)
- **Claim verification** — atomic decomposition + RAG fact-checking of the answer *(README pending; new issue)*
- Wire the verification gate into the agentic path.

**Done when:** answers expose claim-level trust signals grounded in the corpus.

## Wave D — Conversation UX & streaming

- **#130** (+ bug **#98**) — persist history in Conversation/Message; paginated `GET /conversations`
- **#132** — SSE streaming on `/chat/stream` *(ADR-0008 "SSE slice"; resolve the gate-vs-stream contract)*
- **#131** — per-response 👍/👎 feedback *(depends on #130)*
- **#127** — export conversation as Markdown/JSON
- Bugfixes **#99 / #97 / #95** — retry duplication, LRU eviction order, whitespace/atomic buffer

**Done when:** conversations are durable, streamed, rateable, and exportable over the agentic `/chat`.

---

## Continuous Track

Schedulable anytime; not blocked by the Waves.

- **Security hardening:** #111, #112, #113, #114, #115, #116, #117, #118, #119
  *(#111/#118 harden the agentic **CI** workflows; #113 also intersects Wave A — the agent path must sanitize history)*
- **Quality gate & tests:** #133 (70% coverage + full mypy strict), #121 (tautological tests)
- **Eval & robustness chores:** #120, #122
- **Observability:** #45 (Langfuse) — LangGraph-native, so it lands naturally with Wave A tracing
- **Standalone feature:** #124 (auth account management — change password / delete account)

---

## Full Issue → Wave Mapping

| Wave | Issues |
|------|--------|
| A — Agentic core | *(new issues to be created: A1–A5)* |
| B — Retrieval quality | #123, #126, #128, #129, #105, #106, #100 *(+ hybrid search, reranking, ACL: new issues)* |
| C — Verification & trust | #102, #125 *(+ claim verification: new issue)* |
| D — Conversation UX & streaming | #130, #98, #132, #131, #127, #99, #97, #95 |
| Continuous — security | #111, #112, #113, #114, #115, #116, #117, #118, #119 |
| Continuous — quality/test/eval | #133, #121, #120, #122 |
| Continuous — observability | #45 |
| Continuous — standalone feature | #124 |

## Sequencing Notes

- **Wave A is the gate for the agentic story.** Start with **A1** (the proven spike, smallest slice).
- **Wave B item #123** is the highest-value retrieval slice and unblocks #125 (Wave C) and #126.
- **Wave D #130** unblocks #131; **#98** is the bug that #130's feature resolves — do them together.
- **Watch overlaps:** #98↔#130 (history), #105↔#129 (chunker globals), #133↔#121 (coverage), #113↔Wave A (history sanitization).

## References

- Decisions: [`docs/adr/`](./adr/) — ADR-0008 (substrate), ADR-0009 (agent model), ADR-0002 (entropy),
  ADR-0005 (synchronous `/chat`).
- Backlog: GitHub Issues (`gh issue list --state open`).
- Status: README "Project Status".
