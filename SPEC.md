# SPEC: feat(agent): support a configurable local Ollama model provider for the deep agent

## Problem

The deep agent cannot run on the free Groq tier — its ~9822-token calls exceed the 8000 TPM
cap on `gpt-oss-20b`, and `llama-3.3-70b` (which would fit) fails Groq tool-calling — so the
agent is unusable without a paid tier, and the #192 loop-bounds calibration is blocked on a
runnable agent.

## Design Decision

Introduce an `agent_provider` setting (`groq | ollama`) that selects how `agent/factory.py`
builds the deep agent's chat model: `ChatOllama(model=settings.agent_model)` for the local
path, `ChatGroq(...)` for the hosted path. Default to `ollama` with `agent_model = "qwen2.5:7b"`
so the agent is runnable out of the box (no TPM limit); a feasibility probe confirmed qwen2.5
emits valid `search_corpus` tool calls. Extend `agent/limits.py::_extract_total_tokens` to fall
back to the generation message's standardized `usage_metadata["total_tokens"]` when
`llm_output["token_usage"]` is absent, so the token budget stays live for Ollama (which reports
usage there, not in the Groq-style `llm_output`). Add `langchain-ollama` as a dependency. Groq
behavior is unchanged when `agent_provider = groq`.

## Alternatives Considered

- **Hard-switch the agent to Ollama with no provider seam**: fewer settings, but it deletes the
  Groq path, so moving to a paid Groq tier later would be new work. Rejected — the seam is cheap
  and keeps both options.
- **Switch the Groq model to `llama-3.3-70b-versatile`**: fits the TPM (12000) but emits
  Llama-native `<function=…>` tool calls that Groq rejects with `400 tool_use_failed`. Rejected —
  it breaks the agent's tool use (verified this session).
- **Pay for a higher Groq tier and keep `gpt-oss-20b`**: keeps the ADR-0009 model and its valid
  tool calls, but is a billing decision the user declined in favor of local.
- **Read Ollama's `eval_count`/`prompt_eval_count` directly in the extractor**: works, but couples
  the extractor to Ollama's raw fields; the LangChain-standard `usage_metadata.total_tokens` is
  provider-neutral and already populated for both Groq and Ollama, so it is the smaller, more
  durable change.

## Scope

- Includes:
  - `agent_provider` setting in `core/config.py` (validated `groq | ollama`), default `ollama`;
    `agent_model` default changed to `qwen2.5:7b` (the local default).
  - `agent/factory.py`: build `ChatOllama` or `ChatGroq` from `agent_provider`.
  - `langchain-ollama` added to `pyproject.toml` + lock/requirements regenerated.
  - `_extract_total_tokens` fallback to `usage_metadata["total_tokens"]` for the Ollama shape.
  - ADR for the local-provider decision (amends ADR-0009's hosted-only assumption) + README row.
- Does NOT include:
  - The #192 calibration (thresholds/bounds), its harness, or flipping `agent_enabled`.
  - Any change to the domain gate, retrieval, generation, or the legacy `/chat` path.
  - Provider auto-detection or per-request provider switching (one process-wide setting only).
  - Model quality tuning, prompt changes, or `deepagents` version changes.

## Acceptance Criteria

- `agent_provider_defaults_to_ollama` and `agent_model_defaults_to_qwen`: the new defaults hold.
- `agent_provider_rejects_unknown_value`: a value outside `{groq, ollama}` fails validation at boot.
- `default_model_builds_chatollama_when_provider_is_ollama`: with `agent_provider=ollama`, the
  factory constructs the Ollama chat model with `settings.agent_model` (asserted via an injected fake).
- `default_model_builds_chatgroq_when_provider_is_groq`: the Groq path is unchanged and still
  passes the api key and model (existing behavior preserved).
- `extract_total_tokens_reads_ollama_usage_metadata_shape`: an `LLMResult` in the real ChatOllama
  shape yields the correct positive total through the runtime budget path.
- `extract_total_tokens_still_reads_groq_llm_output_shape`: the existing Groq extraction is unbroken.
- `deep_agent_runs_search_corpus_on_qwen` (requires_infra): the compiled agent on `qwen2.5:7b`
  issues a real `search_corpus` tool call and returns a grounded answer.

## Reproducibility

- Provider selection: set `AGENT_PROVIDER=ollama` (default) or `AGENT_PROVIDER=groq` in `.env`.
- Local run prerequisites: Ollama serving `qwen2.5:7b` (`ollama pull qwen2.5:7b`), Qdrant up with
  the corpus ingested.
- Dependency: `langchain-ollama==1.1.0` (latest on PyPI at spec time), resolved via
  `uv lock` and exported with `uv export --frozen --no-dev -o requirements.txt`.
- Versions pinned by `uv.lock`; Python 3.12.

## Risks and Assumptions

- Assumption: `ChatOllama` exposes `bind_tools` compatibly with `deepagents.create_deep_agent`,
  so the deep agent's tool loop works unchanged. Invalidated if deepagents rejects the model; the
  `requires_infra` end-to-end test is the guard, and qwen2.5 tool-calling is already probed.
- Assumption: ChatOllama populates `usage_metadata.total_tokens` on `on_llm_end`. Invalidated if it
  reports usage only elsewhere; the captured-shape test settles it during implementation and the
  extractor is adjusted to the real field before the token budget is trusted for Ollama.
- Risk: local qwen2.5:7b is slower and less capable than a hosted model, so multi-step runs may take
  more steps or loop; this is exactly what #192 then measures and bounds. Out of scope here.
- Risk: changing the default provider changes what happens when `agent_enabled` is later turned on.
  `agent_enabled` stays `False` here, so no runtime behavior changes for current users on this change.
