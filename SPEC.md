# SPEC: perf(agent): cache the compiled agent graph across requests

## Problem
`invoke_agent(..., graph=None)` calls `create_agent()` per request, rebuilding the deep-agent graph
and a fresh `ChatGroq` client on every `/chat` call — per-request latency that must go before
`agent_enabled` is flipped on.

## Design Decision
Add a lazy, double-checked-locking module-level singleton `get_agent()` in `agent/factory.py`
(mirroring the `_sessions_lock` pattern in `api/routes/chat.py`), building via `create_agent()` once
per process. `invoke_agent` calls `get_agent()` when `graph is None`; the `graph=` injection seam is
untouched for network-free tests. A `reset_agent_cache()` clears the singleton (test hygiene + runtime
reconfiguration).

## Alternatives Considered
1. `functools.lru_cache` on a no-arg builder — rejected: can double-build under threadpool concurrency
   and is awkward to reset for tests/reconfiguration.
2. Eager build at import — rejected: constructs the `ChatGroq` client at import time, breaking
   network-free imports/tests and failing without `GROQ_API_KEY`.

## Scope
- Includes: `agent/factory.py` (`get_agent`, `reset_agent_cache`, `_cached_graph`, `_graph_lock`);
  `agent/runner.py` (`invoke_agent` uses `get_agent()` instead of `create_agent()`).
- Does NOT include: `create_agent`'s signature; eager warmup; flipping `agent_enabled`; `/chat` changes.

## Acceptance Criteria
- get_agent_builds_the_graph_at_most_once
- get_agent_returns_the_same_cached_instance
- reset_agent_cache_forces_a_rebuild
- invoke_agent_uses_injected_graph_without_touching_cache
- invoke_agent_uses_cached_graph_when_no_graph_injected

## Reproducibility
`pytest tests/test_agent.py -m "not requires_infra"`
Versions: langgraph 1.2.6, deepagents 0.6.11, langchain-groq 1.1.3.

## Risks and Assumptions
- Double-checked locking prevents double-build under the FastAPI threadpool.
- The cache holds one `ChatGroq` client for the process lifetime; `reset_agent_cache()` handles runtime
  config changes.
