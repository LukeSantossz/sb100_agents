# SPEC: feat(agent): bound the agent loop with recursion limit and token budget

## Problem

The agent loop (`agent/runner.py`) runs with no explicit step or token bound, so a looping or
verbose agent can exceed Groq free-tier limits and inflate latency, and a runaway loop surfaces as
an unhandled exception rather than a graceful answer.

## Design Decision

Bound the run at two levels, both configured from `settings` and both terminating gracefully.
(1) Recursion/step limit: `invoke_agent` passes `config={"recursion_limit": settings.agent_recursion_limit}`
to `graph.invoke`; a `langgraph.errors.GraphRecursionError` is caught and converted to a fallback
`AgentOutcome`. (2) Per-run token budget: a LangChain callback handler accumulates per-call token
usage (`on_llm_end`) and raises `TokenBudgetExceeded` once the cumulative count crosses
`settings.agent_token_budget`; `invoke_agent` passes it via `config={"callbacks": [handler]}` and
catches the raise into the same fallback. The token cap is a post-call soft cap (it stops the next
step; it cannot preempt an in-flight call).

## Alternatives Considered

1. Per-call model `max_tokens` + recursion limit only (no cumulative counting) — rejected: does not
   enforce a single per-run token number (AC #2) and ignores input tokens.
2. Recursion limit alone as a token proxy — rejected: one step can emit arbitrarily many tokens, so
   step count is not a token budget.
3. Preemptive mid-call interruption — rejected: not achievable without streaming-level interception;
   disproportionate complexity over a post-call soft cap.

## Scope

- Includes:
  - `core/config.py`: `agent_recursion_limit` (int, bounded) and `agent_token_budget` (int, bounded).
  - `agent/runner.py`: pass `recursion_limit` + `callbacks` in the `graph.invoke` config; catch
    `GraphRecursionError` and `TokenBudgetExceeded`, return a fallback `AgentOutcome`
    (`answer=AGENT_BOUND_FALLBACK`, `context=""`).
  - New module `agent/limits.py`: `TokenBudgetExceeded` exception + the accumulating callback handler.
  - Update the existing `invoke_agent` stub tests so their `.invoke` accepts the new `config` argument.
- Does NOT include:
  - Any change to `api/routes/chat.py` structure (it already maps `AgentOutcome` to `ChatResponse`).
  - The legacy (non-agent) path.
  - Flipping `agent_enabled` to default-on.
  - Preemptive mid-call token interruption; wiring the retry/fallback verification gate (Wave C).

## Acceptance Criteria

- `invoke_agent_passes_recursion_limit_from_settings_to_graph_config`
- `invoke_agent_returns_fallback_answer_on_graph_recursion_error` (no exception raised)
- `invoke_agent_returns_fallback_answer_when_token_budget_exceeded`
- `token_budget_handler_raises_when_cumulative_usage_exceeds_budget`
- `token_budget_handler_stays_silent_under_budget`
- `token_budget_handler_fails_open_when_usage_absent`
- `settings_reject_out_of_bounds_recursion_limit_and_token_budget`

## Reproducibility

`pytest tests/test_agent.py tests/test_agent_limits.py -m "not requires_infra"`
Versions: langgraph 1.2.6, deepagents 0.6.11, langchain-groq 1.1.3, langchain-core 1.4.8.

## Risks and Assumptions

- Assumption: ChatGroq reports token usage to the callback (`on_llm_end` via `LLMResult.llm_output`).
  If it does not, the handler fails open (counts zero + logs), matching the `agent/intent.py`
  fail-open posture; this must be validated against a live Groq call before the agent path is enabled.
- The token cap is a soft post-call cap; a single call can overshoot by up to one call's output.
- Assumption: `GraphRecursionError` propagates out of the deepagents `graph.invoke`; asserted via stub
  in unit tests, to be confirmed against the real compiled graph before enablement.
- Durable rationale promoted to ADR-0012 at the Gate.
