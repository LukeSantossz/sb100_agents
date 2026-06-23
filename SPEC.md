# SPEC: feat(chat): route /chat through the deepagents agent synchronously with the verification gate

Wave A slices A2 (#171) and A5 (#174), merged into one slice per the design decision below.

## Problem

`/chat` runs a fixed hand-rolled pipeline (embed → search → generate → entropy-score); the Wave A
agent built in A1 (#170) exists but nothing invokes it, so users cannot get answers produced by the
autonomous agent, and the migration risks losing the hallucination trust signal on the agent path.

## Design Decision

Add an agent-backed path to the synchronous `/chat` handler, gated behind a new `agent_enabled`
setting (default OFF). When ON, the handler delegates to a new `agent.runner.invoke_agent`, which
drives the compiled graph via `graph.invoke(...)` (preserving ADR-0005) and returns the final answer
plus the context the agent retrieved through `search_corpus`; the existing semantic-entropy gate
then scores that `(question, context)` so the agent answer carries a `hallucination_score`
(ADR-0002). A2 and A5 are delivered as one slice because verifying the agent answer (A5) is the only
honest way to ship the agent path — a placeholder score would be the "silent 0.0 = trustworthy"
anti-pattern (#102). All `deepagents`/LangGraph specifics stay inside `agent/` (ADR-0008); the legacy
path is byte-unchanged.

## Alternatives Considered

- **Agent path with a placeholder score, A5 done later.** Rejected: shipping an agent answer whose
  trust signal is a fixed 0.0/0.5 placeholder is the silent-trust anti-pattern the gate exists to
  prevent (#102); A5 explicitly depends on A2, so merging them removes a throwaway intermediate state.
- **Runner returns a finished `ChatResponse` (agent/ calls verification).** Rejected: couples the
  `agent/` boundary to `verification/`, leaking the ADR-0008 isolation and making both units harder to
  test in isolation. Orchestration stays in the handler; `agent/` only produces answer + context.
- **Add a `sources` field to `ChatResponse` now.** Rejected: structured citations (`source_file` +
  score) are deferred to Wave B (#123), and `search_corpus` (A1) returns joined text only; the answer
  is grounded via the tool, but the public contract stays `{answer, hallucination_score}`.
- **Strategy-pattern chat service for legacy vs agent.** Rejected: requires refactoring the working
  legacy path, which is out of scope and risky for a flag-gated rollout.

## Scope

- **Includes:**
  - New `agent_enabled: bool = False` setting in `core/config.py`.
  - New `agent/runner.py`: `invoke_agent(question, history, profile) -> AgentOutcome(answer, context)`
    — builds the graph input from history + the user question (with a short profile preamble for tone
    parity), invokes the compiled graph synchronously, and extracts the final answer (last `AIMessage`)
    and the concatenated `search_corpus` tool context (all `ToolMessage` contents).
  - New `verification/gate.py::score_context(question, context) -> float`: returns the neutral `0.5`
    when `context` is empty/whitespace (nothing to verify); otherwise wraps `compute_entropy_score`
    with the existing neutral-0.5 fallback on verifier failure. The legacy `evaluate` is untouched.
  - `api/routes/chat.py`: branch on `settings.agent_enabled`. ON → `invoke_agent` → score
    (`score_context` when `verification_enabled`, else `0.0`) → `ChatResponse`; shared auth,
    rate-limit, and post-success buffer update. OFF → legacy path unchanged.
  - Tests covering both flag states with a stubbed agent graph and a stubbed verifier (no network).
  - Closes #171 and #174.
- **Does NOT include:**
  - Structured source citations (`source_file` + score) and any `ChatResponse` schema change — Wave B (#123).
  - Conversation-history sanitization on the agent path — #113 (Continuous/security); intersection noted only.
  - Recursion-limit / token-budget bounding of the agent loop — A4 (#173).
  - Agricultural intent filter before the loop — A3 (#172).
  - Flipping `agent_enabled` to ON by default, or any production rollout decision.
  - Regenerate-on-high-score / fallback-message retry loop of the legacy gate (legacy-`generate`-specific;
    the agent runs its own loop).

## Acceptance Criteria

- `flag_off_leaves_legacy_pipeline_unchanged`: with `agent_enabled=False`, the existing `/chat`
  behavior and all current `/chat` tests pass unchanged.
- `flag_on_returns_agent_produced_answer`: with `agent_enabled=True`, `POST /chat` returns the answer
  produced by the agent (stubbed graph) rather than the legacy `generate` output.
- `agent_path_carries_gate_score_when_verification_enabled`: with the flag ON and
  `verification_enabled=True`, the response `hallucination_score` is the value from
  `score_context` (stubbed verifier).
- `agent_path_returns_zero_score_when_verification_disabled`: with the flag ON and
  `verification_enabled=False`, `hallucination_score == 0.0` and the verifier is not called.
- `verifier_failure_falls_back_to_neutral_score`: when `compute_entropy_score` raises, `score_context`
  returns `0.5` and the agent answer is still returned.
- `empty_agent_context_falls_back_to_neutral_score`: when the agent made no `search_corpus` call
  (no context), the path returns the neutral `0.5` score.
- `runner_extracts_final_answer_and_concatenated_tool_context`: `invoke_agent` returns the last
  `AIMessage` content as `answer` and all `search_corpus` `ToolMessage` contents joined as `context`.
- `handler_remains_synchronous`: the `chat` handler is a plain `def` (no `async`), preserving ADR-0005.
- `agent_invocation_failure_returns_503_without_leaking_internal_detail`: when `invoke_agent` raises,
  the handler returns HTTP 503 with a generic detail (no `str(e)`), logging the traceback.

## Reproducibility

- Environment: Python 3.13 (`.python-version`), deps via `uv sync --extra dev`.
- Pinned: `deepagents>=0.6.11`, `langchain-groq`, `langgraph` (as in `uv.lock`).
- Targeted tests: `uv run --extra dev pytest tests/test_agent.py tests/test_chat.py -o addopts= -v`.
- Full gate (no infra): `uv run --extra dev pytest -m "not requires_infra" -q`,
  `ruff check .`, `ruff format --check .`, `mypy agent api/routes/chat.py verification/gate.py`.
- No randomness in tests: the agent graph and the entropy verifier are stubbed; no network calls.
- Manual smoke (optional, not in CI): set `GROQ_API_KEY` and `AGENT_ENABLED=true`, then
  `POST /chat` and expect an agent-produced, gate-scored answer.

## Risks and Assumptions

- Assumption: the compiled graph returns `{"messages": [...]}` with `ToolMessage`s named
  `search_corpus` and a final `AIMessage`; the runner's extraction is validated against the real
  graph output during TDD. What invalidates the spec: a different output shape would change the
  runner's extraction contract.
- Assumption: `compute_entropy_score(question, context)` is a faithful trust signal for the agent's
  retrieved context even though the agent, not the verifier, authored the answer (consistent with the
  legacy gate, which already scores `(question, context)` independently of the answer text).
- Assumption: passing prior turns and a short profile preamble into the graph input yields tone
  parity with the legacy `generate(profile=...)`; deep prompt tuning is out of scope.
- Risk: with the flag OFF (default) the agent path is never exercised in CI beyond unit tests with a
  stubbed graph; real Groq behavior is validated only by the optional manual smoke. Mitigation: the
  flag defaults OFF, so this cannot regress the live legacy path.
- ADR note for the Gate: this slice instantiates ADR-0005 (synchronous `/chat`), ADR-0008
  (deepagents behind `agent/`), and ADR-0002 (entropy gate); no new hard-to-reverse decision emerges,
  so no new ADR is proposed. Promote later if implementation surfaces one.
