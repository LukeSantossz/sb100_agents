# SPEC: fix(generation): survive CPU-only Ollama latency — raise the timeout default and catch httpx timeouts

Resolves #92 (raise `ollama_timeout` default above CPU-only generation time) and #101 (capture Ollama/httpx timeouts in `generate`'s except). They are two halves of the same failure mode — a CPU-only generation that exceeds the timeout — so they share one design and PR.

## Problem

- **#92:** `ollama_timeout` defaults to `120.0s` (`core/config.py:61`), but documented CPU-only generation takes ~160-200s, so `/chat` systematically times out and returns 503 on CPU hosts running defaults.
- **#101:** when a timeout does occur, the `httpx.ReadTimeout`/`ConnectTimeout` raised through the Ollama client is not a subclass of any type in `generate`'s except tuple (`generation/llm.py:188-193` catches `ollama.RequestError`, `ollama.ResponseError`, builtin `TimeoutError`, `ConnectionError`), so the dominant CPU-only failure escapes unlogged — `generation.llm.failure` never fires for it.

## Design Decision

1. **#92:** raise the `ollama_timeout` default to `240.0s` — above the documented ~200s upper bound with margin, comfortably under both the existing `chat_timeout` (600s, the UI/API request budget) and the field's `le=600.0` bound. Operators on GPU can lower it via `OLLAMA_TIMEOUT`; add that knob to `.env.example` (currently undocumented) so the value is discoverable.
2. **#101:** add `httpx.TimeoutException` and `httpx.RequestError` to `generate`'s except tuple (importing `httpx` in `generation/llm.py`). These are the precise types the Ollama client propagates on timeout/connection failure; the handler keeps its current shape — log `generation.llm.failure` with context, then re-raise (the route maps it to a 503). The dead builtin `TimeoutError`/`ConnectionError` entries are kept only if still reachable; otherwise removed to avoid implying coverage that does not occur.

## Alternatives Considered

1. **Timeout value — keep 120s and only document the limitation.** Rejected: it leaves the default-config CPU path systematically broken; the whole point is that defaults should work on the documented CPU target.
2. **Timeout value — set it to 600s (= `chat_timeout`).** Rejected: too loose. A genuinely stuck generation should fail with headroom below the outer request budget (which also has to cover the verification gate's extra calls), not race it.
3. **Exceptions — catch broad `Exception` in `generate`.** Rejected: violates the "catch the narrowest type" convention and would swallow programming errors. `httpx.TimeoutException`/`RequestError` name the real failure precisely.

## Scope

- **Includes:** change the `ollama_timeout` default in `core/config.py`; document `OLLAMA_TIMEOUT` in `.env.example`; add `httpx.TimeoutException`/`httpx.RequestError` to the except tuple in `generation/llm.generate` (with `import httpx`), preserving the log-and-re-raise behavior.
- **Does NOT include:** changing `chat_timeout`, `ollama_embed_timeout`, or the entropy/verification timeouts; altering the route's 503 mapping (`api/routes/chat.py`); touching `core/ollama_clients.py` client construction beyond what the new default implies; the 503-detail leak (#114) or rate-limit (#110).

## Acceptance Criteria

- `ollama_timeout_default_is_at_least_210s` — `Settings(jwt_secret_key=<valid>).ollama_timeout >= 210` (concretely `== 240.0`).
- `ollama_timeout_still_respects_upper_bound` — a value `> 600` is still rejected (the `le=600.0` bound is unchanged).
- `generate_logs_and_reraises_on_httpx_timeout` — when `_ollama_chat` raises `httpx.ReadTimeout`, `generate` emits `generation.llm.failure` and re-raises (today it escapes unlogged).
- `generate_logs_and_reraises_on_httpx_request_error` — same for `httpx.ConnectError`.
- `generate_still_logs_on_ollama_response_error` — existing `ollama.ResponseError` handling is preserved (no regression).
- No regression: existing `tests/test_llm.py` and `tests/test_config.py` continue to pass.

## Reproducibility

- Versions: Python 3.12, httpx 0.28+, ollama 0.6.1, on the dev host.
- Unit (no infra): `uv run pytest tests/test_llm.py tests/test_config.py -v`, patching `_ollama_chat` to raise `httpx.ReadTimeout`/`httpx.ConnectError` and asserting the log record + re-raise; asserting the default value via `Settings`.
- Manual (infra-dependent, optional): on a CPU-only host, a real `/chat` call now completes (≤240s) instead of 503-ing at 120s. Recorded as "verified locally against live Ollama; not reproducible in CI".

## Risks and Assumptions

- Assumption: the Ollama client propagates `httpx.TimeoutException`/`RequestError` on timeout/connection failure (per #101's analysis) — the unit tests pin this by patching `_ollama_chat` to raise those types; if the library wraps them in `ollama.ResponseError`, the existing branch already covers it and the new branch is harmless.
- Assumption: 240s sits safely below the outer `chat_timeout` (600s) even accounting for the verification gate's multiple generations per request — true, since the budget is per outer request and each Ollama call is bounded independently.
- Risk: a higher timeout means a stuck backend ties up a worker longer; acceptable trade-off versus systematic false 503s, and bounded well under `chat_timeout`.
