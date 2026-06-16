# Multi-provider verification dispatch

The hallucination check should not hard-depend on one paid API. The Verification Gate dispatches
candidate-answer sampling across a selectable Provider — Ollama (local default), Groq, or
OpenRouter — behind a single interface.

## Status

Accepted.

## Considered Options

- **Multi-provider dispatch (chosen)**: one interface, Provider selected by configuration;
  the Ollama Provider keeps the whole check runnable offline.
- **OpenAI-only verification**. Rejected — a hard paid dependency on the verification path with
  no offline mode.

## Consequences

- Verification runs offline through the Ollama Provider; Groq and OpenRouter are opt-in for
  speed or quality.
- Each Provider's SDK quirks (parameter names, client construction) live behind the dispatch;
  adding a Provider means encoding its quirks there.
- A misconfigured or invalid model id for a hosted Provider degrades silently to the Neutral
  Score; the configured model id must be verified against the Provider's catalog before
  selecting it. This operational footgun is the cost of the soft dependency.
