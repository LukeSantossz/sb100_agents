# Bound the agent loop with a recursion limit and a soft token budget

The agentic `/chat` loop (`agent/runner.py`) must be bounded so a looping or verbose agent cannot
exceed Groq free-tier limits, inflate latency, or surface a runaway as an unhandled exception. We
bound each run at two levels, both configured from `settings` and both terminating gracefully with a
fallback answer rather than an error. A recursion/step limit is passed to LangGraph via
`graph.invoke(input, config={"recursion_limit": settings.agent_recursion_limit})`; exceeding it
raises `langgraph.errors.GraphRecursionError`, which `invoke_agent` catches. A per-run token budget is
enforced by a LangChain callback handler that accumulates per-call token usage on `on_llm_end` and
raises `TokenBudgetExceededError` once the cumulative total crosses `settings.agent_token_budget`; the
handler is passed through the same `graph.invoke` config. Both bounds resolve to the same graceful
`AgentOutcome` fallback. The token cap is a post-call soft cap: it stops the run before the next step
but cannot preempt an in-flight model call.

## Status

Accepted. Realizes the loop-bounding that ADR-0009 explicitly deferred to "a later Wave A slice"
(Wave A / A4, issue #173).

## Considered Options

- **Recursion limit + soft cumulative token cap via callback (chosen)**: the recursion limit is the
  native LangGraph step bound; the callback handler is the only place cumulative token usage across all
  calls in a run is observable. Together they bound both step count and total tokens, and both fail into
  one graceful fallback. The token cap is soft (post-call) and depends on the provider reporting usage,
  so the handler fails open (counts zero + logs) when usage is absent, matching the `agent/intent.py`
  fail-open posture.
- **Per-call model `max_tokens` + recursion limit only**: bounds each call's output and the step count
  but never enforces a single per-run token number and ignores input tokens, so it does not satisfy the
  "per-run token budget" requirement. Rejected.
- **Recursion limit alone as a token proxy**: a single step can emit arbitrarily many tokens, so step
  count is not a token budget. Rejected.
- **Preemptive mid-call interruption**: would cap tokens within an in-flight call, but is not achievable
  without streaming-level interception and adds disproportionate complexity over a post-call soft cap.
  Rejected.

## Consequences

- Both bounds are configurable (`agent_recursion_limit`, `agent_token_budget`) and must be calibrated
  against Groq free-tier limits before the agent path is enabled — part of the pre-enablement checklist
  alongside ADR-0010 (`intent_threshold`), #177, and #178.
- The token cap is soft: a single call can overshoot the budget by up to that call's output before the
  next-step abort fires. Accepted; a hard preemptive cap is out of scope.
- The handler depends on ChatGroq reporting token usage to `on_llm_end`. If a provider omits usage, the
  budget silently does not bind (fail-open), so the assumption must be validated against a live Groq call
  before enablement rather than trusted from unit tests alone.
- Both bounds are isolated behind `agent/` (`agent/limits.py` and `agent/runner.py`), so `/chat`
  (`api/routes/chat.py`) is unchanged: a bounded run returns a normal `ChatResponse` carrying the
  fallback answer, not a 503.
