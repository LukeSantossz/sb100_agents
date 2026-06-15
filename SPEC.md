# SPEC: fix(chat): rate-limit POST /chat per authenticated user (DoS / cost amplification)

## Problem

`POST /chat` — the system's most expensive endpoint (each call fans out to Ollama generations plus, by default, multiple paid Groq/OpenRouter verification calls) — has no rate limit, while `/auth/*` already use slowapi; a 7-day token lets one authenticated user loop `/chat` and exhaust the paid quota and saturate local inference (OWASP A04 / CWE-770).

## Design Decision

Apply slowapi's `@limiter.limit` to `chat()` with a **per-user** key derived from the authenticated request, not the client IP. A module-level `_rate_limit_key(request)` reads the bearer token from the `Authorization` header and returns its JWT `sub` (username); it falls back to `get_remote_address` when no valid token is present (those requests are 401'd by `verify_token` anyway). The limit is configurable via a new `chat_rate_limit` setting (default `"30/minute"`); exceeding it returns 429 (slowapi's handler is already registered for `/auth`). `chat()` gains the `request: Request` parameter slowapi requires.

## Alternatives Considered

1. **Per-IP limit (slowapi's default `get_remote_address`).** Rejected: many users behind one NAT share a limit and one user across IPs evades it; the expensive resource is per-identity, so the key must be the user.
2. **A daily paid-provider call budget / shedding the entropy gate under load.** Deferred (not this PR): a global cost-budget is a larger quota subsystem; the surgical, high-value fix is the per-user request rate limit. Recorded as future hardening.
3. **Shorten the token TTL to bound abuse.** Rejected: wrong layer (auth lifetime ≠ request throttling) and it would not bound burst cost within a single session.

## Scope

- **Includes:** a per-user `@limiter.limit` on `POST /chat` keyed by the JWT subject (IP fallback); the `request: Request` parameter on the handler; a configurable `chat_rate_limit` setting documented in `.env.example`; 429 on exceed. Changes confined to `api/routes/chat.py`, `core/config.py`, `.env.example`.
- **Does NOT include:** the IDOR per-user session scoping (#108); a daily/global paid-provider budget or load-shedding of the entropy gate (future hardening, no dedicated issue); any change to token TTL or the `/auth` limits; async cancellation of timed-out work (related to #99).

## Acceptance Criteria

- `rate_limit_key_returns_jwt_subject` — `_rate_limit_key` returns the token's `sub` for an authenticated request; two users yield different keys, the same user the same key.
- `rate_limit_key_falls_back_to_ip_without_token` — with a missing/invalid `Authorization` header, the key is the client address (no exception).
- `chat_is_decorated_with_a_per_user_limit` — `POST /chat` enforces `settings.chat_rate_limit` rather than the default IP limiter.
- `exceeding_the_limit_returns_429` — the (N+1)-th request within the window returns 429.
- No regression: existing tests pass (`pytest tests/ --ignore=tests/test_integration.py`).

## Reproducibility

- Versions: Python 3.12, slowapi (already a dependency), on the dev host.
- Unit (no infra): `uv run pytest tests/test_auth.py tests/test_integration.py -v` — assert `_rate_limit_key` on a crafted token; drive `TestClient` against `/chat` (external services mocked, `verify_token` overridden) with a low `chat_rate_limit` and assert the (limit+1)-th call returns 429.

## Risks and Assumptions

- Assumption: the slowapi `limiter` and its 429 handler are app-wired (confirmed — `/auth` uses `@limiter.limit`, `api/dependencies.py:27`); only a newly decorated route is added.
- Assumption: decoding the JWT in the key function uses the same `settings.jwt_secret_key`/`ALGORITHM` as `verify_token`; an invalid token falls back to IP rather than raising inside the limiter.
- Risk: slowapi's default in-memory storage is per-process, so in a multi-worker deployment the limit is per worker; acceptable for the current single-process target, with a shared store (e.g. Redis) as a future scaling concern.
