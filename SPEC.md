# SPEC: feat(agent): scaffold agent/ package with deepagents + search_corpus tool

## Problem
The agentic-RAG migration (ADR-0008/0009) has no code yet: there is no `agent/` package and nothing
uses the pinned `deepagents` dependency, so `/chat` cannot be driven by an agent.

## Design Decision
Add an `agent/` package that isolates all `deepagents` usage behind a small boundary (ADR-0008):

- `search_corpus(query)` — a tool that composes the existing retrieval (`generate_embedding` →
  `search_context`) and returns the joined context **text**.
- `default_model()` — builds a `ChatGroq` from `settings`, using a new `agent_model` field
  (default `openai/gpt-oss-20b`, per ADR-0009) and the existing `groq_api_key`.
- `create_agent(model=None)` — when `model is None`, uses `default_model()`; assembles
  `create_deep_agent(model, tools=[search_corpus], system_prompt=AGENT_INSTRUCTIONS)` and returns the
  compiled graph. (`deepagents` 0.6.11 names this parameter `system_prompt`.)

`/chat` is unchanged in this slice; the agent is wired into `/chat` in A2 (#171). The model is
injectable so unit tests compile the graph without network access.

## Alternatives Considered
- Surface `source_file` + score from the tool now — rejected: that is Wave B (#123 source citations);
  it would extend the retrieval contract and creep A1's scope. The tool returns plain text, matching
  today's `search_context`.
- Construct `ChatGroq` inside the factory with no injection seam — rejected: it forces tests to
  monkeypatch the constructor and couples graph compilation to a real model. `create_agent(model=None)`
  with an injectable model is the cleaner, network-free test seam.
- Use raw LangGraph instead of `deepagents` — rejected: ADR-0008 already chose `deepagents`; raw
  LangGraph is the documented fallback, not this slice.

## Scope
- Includes: the `agent/` package (`tools.py`, `factory.py`, `prompt.py`, `__init__.py`); the
  `search_corpus` tool; `default_model()` and `create_agent(model=None)`; a new `agent_model`
  setting; a minimal `AGENT_INSTRUCTIONS`; graceful in-tool error handling (log + informative
  message); unit tests for the tool, the factory/graph compilation, and the settings default; a
  documented (uncommitted) manual Groq smoke for go/no-go re-verification.
- Does NOT include: routing `/chat` through the agent (A2, #171); the agricultural intent filter
  (A3, #172); loop bounding (A4, #173); verification-gate integration (A5, #174); source_file/score
  citations (Wave B, #123); any change to `/chat`, retrieval, generation, or verification modules.

## Acceptance Criteria
- `search_corpus_returns_context_text`: `search_corpus("q")` composes `generate_embedding` +
  `search_context` (both mocked) and returns the joined chunk text.
- `search_corpus_handles_empty_results`: with no chunks retrieved, it returns an explicit
  "no relevant context" sentinel string.
- `search_corpus_degrades_on_retrieval_error`: when retrieval raises, it logs the error
  (`logger.exception`) and returns an informative message instead of propagating.
- `create_agent_compiles_graph_with_injected_model`: `create_agent(model=<stub>)` returns a compiled
  graph with `search_corpus` registered, without network access.
- `default_model_reads_settings`: `default_model()` builds the `ChatGroq` with `settings.agent_model`
  and `settings.groq_api_key` (asserted via a monkeypatched constructor; no network).
- `chat_unchanged`: the existing `/chat` test suite still passes.

## Reproducibility
- `uv run --extra dev pytest tests/test_agent.py -o addopts= -v`
- Full gate: `uv run --extra dev pytest -m "not requires_infra" -o addopts= -q`,
  `uv run --extra dev ruff check .`, `uv run --extra dev ruff format --check .`,
  `uv run --extra dev mypy agent`.
- Manual go/no-go smoke (optional, not committed, not in CI): set `GROQ_API_KEY`, build with
  `create_agent()` and `.invoke(...)` a sample agricultural question; expect a `search_corpus` tool
  call and a grounded answer. Versions: deepagents 0.6.11, langchain-groq 1.1.3, Python 3.12.

## Risks and Assumptions
- Verified against the installed packages: `create_deep_agent(model, tools, system_prompt=...)`
  returns a `CompiledStateGraph`; `ChatGroq` accepts `model`/`api_key` (aliases of
  `model_name`/`groq_api_key`); `GenericFakeChatModel` is the network-free test stub.
- Assumption: a stub `BaseChatModel` lets `create_deep_agent` compile the graph without network. If
  deepagents requires a richer model to compile, the test injects a minimal fake chat model that
  implements the interface deepagents touches at build time.
- Assumption: graceful in-tool error handling (log + message) is preferred over propagation. What
  would invalidate it: if A2 needs hard retrieval failures surfaced as HTTP errors, the tool's error
  contract is revisited there.
