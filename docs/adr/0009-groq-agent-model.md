# Hosted Groq model for the agent reasoning tier

The deep agent needs a model that is strong and reliable at tool-calling. The development
machine has no GPU, and the local 3B chat model already takes minutes per answer on CPU — an
agent loop, which makes several model calls per query, is unusable locally. We therefore drive
the agent with a hosted **Groq** model — `openai/gpt-oss-20b` by default — extending the
multi-provider dispatch of ADR-0004 from verification to the generation/agent tier. Embeddings
and the System-1 fast path stay local, so ADR-0003 still holds for retrieval.

## Status

Superseded by ADR-0013 for the model choice. Measurement while preparing the loop-bounds
calibration showed a single deep-agent call costs about 9.8k tokens, over the free-tier 8000
TPM cap on `gpt-oss-20b`, so the hosted default this record chose is not reachable on the tier
it assumed. ADR-0013 makes the provider configurable and moves the default to a local Ollama
model. Everything below stands as approved and is still the reasoning ADR-0013 builds on,
including why `llama-3.3-70b-versatile` was rejected.

## Considered Options

- **Hosted Groq, `openai/gpt-oss-20b` (chosen)**: Groq is already the default verification
  Provider, so it is not a new vendor; it is fast and has a free tier. Spike #163 confirmed
  `openai/gpt-oss-20b` issues valid `search_corpus` tool calls and grounds its answer.
  Escalation path for harder reasoning: `openai/gpt-oss-120b` or `qwen/qwen3-32b`.
- **`llama-3.3-70b-versatile` on Groq**: rejected — spike #163 showed it emits malformed
  function-call syntax that Groq's parser rejects (`tool_use_failed`), making it unreliable in
  the loop despite forming the correct query.
- **Larger local Ollama model**: rejected — no local GPU; CPU latency makes an agent loop
  unusable. Recorded as the preferred path again if/when GPU hardware is available.
- **Claude / Anthropic hosted**: rejected for now — higher quality but a paid dependency;
  recorded as the documented quality-upgrade path, swappable behind the `agent/` boundary.

## Consequences

- The agentic path is no longer fully offline: it requires network access and a `GROQ_API_KEY`.
  This is consistent with the project already defaulting to Groq for verification (ADR-0004); the
  System-1 fast path and embeddings remain local and offline.
- The agent model id must be a tool-calling-capable Groq model; an invalid or deprecated id fails
  the call (validate against Groq's catalog — the same operational footgun noted in ADR-0004).
- The provider and model stay configurable, keeping both the Claude quality-upgrade path and the
  local-on-GPU path open without code changes to domain modules.
- Groq free-tier rate limits apply; agent loops must be bounded (recursion limit, per-run token
  budget) in a later Wave A slice to stay within limits and control latency.
