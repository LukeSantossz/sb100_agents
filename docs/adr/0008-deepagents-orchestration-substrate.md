# Deepagents on LangGraph as the agent orchestration substrate

SmartB100 is migrating `/chat` to an agentic pipeline. We adopt LangChain's `deepagents`
(built on LangGraph) as the orchestration harness: it supplies a planning/todo tool
(`write_todos`), context-isolated sub-agents (`task`), and a virtual filesystem on top of
LangGraph's durable runtime (checkpointing, streaming, human-in-the-loop). All usage is
isolated behind an `agent/` package so the harness can be swapped without touching domain code.

## Status

Accepted.

## Considered Options

- **Deepagents on LangGraph (chosen)**: batteries-included primitives (planning, sub-agents,
  virtual filesystem, human-in-the-loop) over a standard `CompiledStateGraph`; model-agnostic
  (`model: str | BaseChatModel`). The go/no-go spike (#163) confirmed it compiles with a
  pre-initialized `ChatGroq` and drives a tool-calling loop that grounds its answer.
- **Raw LangGraph**: more explicit branching/retry control and a more stable API, but we would
  reimplement planning, sub-agents, and the filesystem ourselves. Kept as the documented fallback
  if deepagents' API churn becomes a liability.
- **Extend the hand-rolled synchronous loop**: rejected — reinventing an agent harness, with no
  built-in checkpointing, streaming, or human-in-the-loop, and no path to sub-agent decomposition.

## Consequences

- `deepagents` is an orchestration harness, **not** a RAG system: retrieval, hybrid search,
  reranking, ACL enforcement, evaluation, and observability must be supplied around it (the
  subsequent Wave A slices do exactly this).
- New dependencies (`deepagents`, `langgraph`, `langchain-core`) plus transitive `langchain`
  provider packages (`langchain-anthropic`, `langchain-google-genai`, and their SDKs) enlarge the
  dependency tree; versions are pinned, and the unused provider SDKs are a candidate for trimming.
- `deepagents` iterates fast (≈8 minor releases in 6–8 months), so the version is pinned and every
  use is confined to the `agent/` package; raw LangGraph remains the contained fallback.
- The compiled graph is driven synchronously via `graph.invoke(...)`, preserving the synchronous
  `/chat` handler (ADR-0005); native async/streaming is reserved for the SSE slice (issue #132).
