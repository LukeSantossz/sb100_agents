# Configurable model provider with a local Ollama default for the agent

ADR-0009 drives the deep agent with a hosted Groq model (`openai/gpt-oss-20b`), rejecting a
local Ollama model because CPU latency made an agent loop "unusable" and rejecting
`llama-3.3-70b-versatile` because it emits function-call syntax Groq rejects (`tool_use_failed`).
Measurement while preparing the loop-bounds calibration (#192) then showed the hosted free-tier
path is not viable at all: a single deep-agent call is ~9822 tokens — the `deepagents` scaffolding
prompt dominates; our own `AGENT_INSTRUCTIONS` is ~131 — which exceeds the free-tier **8000 TPM**
cap on `gpt-oss-20b`/`gpt-oss-120b` (HTTP 413), and the only free model whose TPM (12000) would fit,
`llama-3.3-70b-versatile`, is the very model ADR-0009 already rejected for `tool_use_failed`.

We therefore add an `agent_provider` setting (`groq | ollama`) selected in `agent/factory.py`, and
default it to **`ollama`** with `agent_model = "qwen2.5:7b"`. A feasibility probe confirmed
`qwen2.5:7b` (and `qwen2.5:3b`) issue valid `search_corpus` tool calls through Ollama. Running
locally removes the TPM ceiling; the hosted Groq path stays one setting away for a future paid tier.
This amends ADR-0009's default provider/model; ADR-0009 already anticipated it ("the provider and
model stay configurable, keeping ... the local-on-GPU path open without code changes").

## Status

Accepted. Amends ADR-0009 (agent provider/model default). `agent_enabled` remains `False`, so no
current runtime behavior changes; this sets the default for when the agent path is turned on.

## Considered Options

- **Local Ollama `qwen2.5:7b`, provider-configurable (chosen)**: no hosted rate limit; valid Groq-free
  tool-calling verified by probe; keeps the Groq path behind a setting. Cost: CPU-bound latency —
  ADR-0009's original concern — so multi-step runs are slower; #192 measures whether this is acceptable
  and bounds the loop. `qwen2.5:3b` is the lighter fallback if latency dominates.
- **Keep hosted `gpt-oss-20b` on the free tier**: rejected — the ~9822-token deep-agent call exceeds
  the 8000 TPM cap, so essentially every query 413s.
- **`llama-3.3-70b-versatile` on Groq (fits TPM 12000)**: rejected — `tool_use_failed` (re-confirmed
  this cycle; already recorded in ADR-0009).
- **Paid Groq tier with `gpt-oss-20b`**: viable and keeps the ADR-0009 model with valid tool-calling,
  but is a billing decision the user declined in favor of the local path. Remains available by setting
  `agent_provider=groq`.

## Consequences

- The agent path is offline again by default (local model + local embeddings + local Qdrant), reversing
  the ADR-0009 network dependency for the default configuration; `GROQ_API_KEY` is needed only when
  `agent_provider=groq`.
- Token accounting is provider-neutral: `agent/limits.py::_extract_total_tokens` now falls back to the
  message's standardized `usage_metadata["total_tokens"]` (where Ollama reports usage) when the
  Groq/OpenAI-style `llm_output` block is absent, so the ADR-0012 token budget stays live for Ollama.
- New dependency `langchain-ollama` (`ChatOllama`); the embedder already used Ollama, so no new service.
- CPU latency is a real cost the calibration must weigh: if `qwen2.5:7b` agent runs prove too slow, the
  documented alternatives are `qwen2.5:3b` or a paid Groq tier — both reachable via configuration alone.
- The `agent/` boundary is unchanged, so the provider seam does not leak into domain modules.
