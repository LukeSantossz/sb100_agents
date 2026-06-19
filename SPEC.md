# SPEC: chore(agent): validate a hosted Groq model can drive a deepagents loop (substrate spike)

## Problem

Before migrating `/chat` to a LangChain `deepagents` orchestrator, we have not proven that the
chosen agent model can reliably drive an agentic tool-calling loop, and the whole approved
migration rests on that unproven assumption.

## Design Decision

The agent's reasoning model is a **hosted Groq** model (`langchain-groq` / `ChatGroq`), because
the development machine has no GPU and a larger *local* model on CPU is too slow for an agent
loop that makes several model calls per query. Run a throwaway go/no-go spike that builds a
minimal `deepagents` agent — a `ChatGroq` instance plus a single `search_corpus` tool over a
**canned corpus** — and records whether the model issues a correct tool call and grounds its
answer in the returned chunks. A canned corpus is used so the spike needs only a Groq key, not
Qdrant/Docker. The spike's *durable* outputs that merge to `main` are only the pinned
dependencies (`deepagents`, `langchain-groq`, transitively `langgraph`/`langchain-core`) resynced
into `requirements.txt`, and two ADRs: **(a)** deepagents/LangGraph as the orchestration
substrate; **(b)** a hosted Groq model for the agent/generation tier, extending the multi-provider
dispatch of ADR-0004 to generation (embeddings stay local on Ollama, so ADR-0003 holds for
retrieval and for the System-1 fast path). The prototype script is throwaway: it lives under
`spikes/` during the spike and is removed before merge; no production code path
(`api/`, `generation/`, `retrieval/`, `verification/`) is touched.

## Alternatives Considered

- **Larger local Ollama model (the originally-selected option).** Rejected: the development
  machine has no GPU; the existing 3B local model already takes minutes per answer on CPU, and an
  agent loop multiplies model calls, making a 7–14B local model unusable here. Recorded as the
  preferred path again if/when GPU hardware is available.
- **Claude / Anthropic hosted.** Rejected for now: higher quality but a paid dependency; recorded
  as the documented quality-upgrade path for the deliberative tier, swappable behind the same
  `agent/` boundary.
- **Run the local model on a remote GPU server.** Rejected for now: adds infrastructure and
  operations overhead disproportionate to a go/no-go spike; revisit at deployment time.
- **Adopt raw LangGraph instead of deepagents.** Rejected for now: the user chose deepagents and
  its built-in planning/sub-agent/filesystem primitives match the target capabilities; raw
  LangGraph is recorded in ADR (a) as the fallback if deepagents' fast-moving API becomes a
  liability, kept contained by the `agent/` package boundary.

## Scope

- Includes:
  - Add `deepagents` and `langchain-groq` as pinned runtime dependencies in `pyproject.toml`,
    refresh `uv.lock`, and regenerate `requirements.txt` via `uv export --frozen --no-dev`.
  - A throwaway `spikes/deepagents_smoke.py` that builds `create_deep_agent(model=ChatGroq(...), tools=[search_corpus], system_prompt=...)`,
    invokes it on a representative agronomy question, and prints the tool calls and the final answer.
  - Select the Groq model and record the choice (spike outcome: `openai/gpt-oss-20b` works;
    `llama-3.3-70b-versatile` rejected — it emits malformed tool-call syntax, `tool_use_failed`).
  - ADR (a) deepagents/LangGraph substrate and ADR (b) hosted Groq agent model, linked from the
    README Engineering Decisions index.
  - Capture the prototype run transcript and exact versions as reproducibility evidence.
- Does NOT include:
  - Any change to `api/routes/chat.py` or the existing RAG pipeline (no `AGENT_MODE`, no router,
    no flip — A1/A3/A8).
  - Real Qdrant retrieval, hybrid search, reranking, citations, sub-agents, planning, eval, or
    governance (A1–A7).
  - Changing `settings.chat_model` or adding an `agent_model` setting (production wiring is A1).
  - Merging the prototype script to `main` (removed before merge).
  - Pruning the transitive provider packages that `deepagents`/`langchain` pull in (tracked as a
    follow-up if they prove unnecessary).

## Acceptance Criteria

- `uv_export_matches_requirements`: after adding the dependencies, `uv export --frozen --no-dev`
  produces a `requirements.txt` identical to the committed file (CI `validate-requirements` stays green).
- `deepagents_builds_with_chatgroq`: `create_deep_agent` accepts a `ChatGroq` instance as `model`
  and returns a compiled graph without error (verified: prints `WIRING OK`).
- `groq_model_issues_correct_tool_call`: on the representative question, the Groq model emits a
  `search_corpus` tool call with a non-empty query and the loop completes.
- `answer_is_grounded_in_returned_chunks`: the final answer reflects the canned chunk content
  (planting window and row spacing) and cites the source file.
- `no_go_path_is_documented_if_unreliable`: if the Groq model does not issue a reliable tool call,
  the failure modes and fallbacks (different Groq model / Claude / GPU server) are recorded and the
  wave is marked paused — the spike still "passes" by producing a decision.
- `adrs_exist_and_are_linked`: ADR (a) and ADR (b) exist under `docs/adr/` and appear in the README
  Engineering Decisions table.
- `production_pipeline_unchanged`: `git diff main` touches no file under `api/`, `generation/`,
  `retrieval/`, `verification/`, `memory/`, `core/` except dependency manifests.

## Reproducibility

- Prerequisite: a Groq API key (free at `https://console.groq.com`) exported as `GROQ_API_KEY`.
- Command: `uv run python spikes/deepagents_smoke.py` (the script sets the model temperature to
  `0` for a deterministic tool-call check and prints the tool calls and the final answer).
- Versions to record in the PR Evidence: `deepagents` (0.6.11), `langgraph` (1.2.6),
  `langchain-core` (1.4.8), `langchain-groq` (1.1.3), `groq` (0.37.1), and the exact Groq model tag.

## Risks and Assumptions

- Assumption: a Groq-served model in the candidate set issues valid tool calls. Spike outcome:
  `openai/gpt-oss-20b` does; `llama-3.3-70b-versatile` does not (malformed syntax → `tool_use_failed`).
- Assumption: `deepagents` accepts a pre-initialized `ChatGroq` (`model: str | BaseChatModel`),
  confirmed by the official API reference and by the `WIRING OK` build check.
- Trade-off (honest): using a hosted model for the agent tier means the agentic path is no longer
  fully offline and depends on network + a Groq key; this is consistent with the project already
  defaulting to Groq for verification, and embeddings/retrieval stay local.
- Risk: Groq free-tier rate limits and possible model deprecation; mitigated by keeping the model
  configurable and the provider swappable behind the `agent/` boundary.
- Invalidation: if no Groq model issues reliable tool calls, the substrate choice must be revisited
  (different model or Claude) before A1 — this spike exists to surface that early and cheaply.
- Risk: `deepagents`' fast-moving API (≈8 minors in 6–8 months); mitigated by pinning the version
  and isolating all usage behind the future `agent/` package (recorded in ADR (a)).
