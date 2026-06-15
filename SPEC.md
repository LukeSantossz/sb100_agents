# SPEC: fix(chat): scope the session buffer to the authenticated user (IDOR)

## Problem

The in-memory session cache `_sessions` (`api/routes/chat.py:41`) is keyed only by the client-supplied `req.session_id`, so any authenticated user who sends another user's `session_id` shares that user's `ConversationBuffer` — reading their history (it enters the LLM context via `buffer.to_messages()`) and writing into it (poisoning via `buffer.add`) — a Broken Access Control / IDOR (OWASP A01).

## Design Decision

Namespace the cache by the authenticated identity: thread `current_user` into `_get_or_create_buffer` and key the cache by the composite `f"{current_user.id}:{session_id}"`. Each user gets a disjoint session space, so passing another user's `session_id` only ever resolves to the caller's own (empty) buffer — never the victim's. A composite key is chosen over an owner-check-with-403 because it leaks nothing (no existence oracle) and is the minimal change. The public `session_id` field and the `ChatRequest`/`ChatResponse` contract are unchanged.

## Alternatives Considered

1. **Store the owner with the buffer and raise 403/404 on mismatch.** Rejected: heavier, and a 403-vs-404 distinction is an existence oracle for other users' `session_id`s; namespacing closes the vector without leaking.
2. **Require a server-assigned, unguessable `session_id`.** Rejected: it does not enforce isolation (a stolen/guessed id still works) and pushes security to the client; the server must scope by identity.
3. **Persist every turn to the per-user `Conversation`/`Message` tables now and drop the in-memory cache.** Rejected: that is the larger #130/#98 work (schema migration, rehydration); the IDOR must be closed surgically first.

## Scope

- **Includes:** pass `current_user` to `_get_or_create_buffer`; key `_sessions` by `f"{current_user.id}:{session_id}"`; changes confined to `api/routes/chat.py`.
- **Does NOT include:** rate-limiting `/chat` (#110); the LRU-eviction-order bug (#97); whitespace/atomic buffer-add (#95); persisting history to SQLite (#98, #130); any change to the `session_id` schema or the request/response contract.

## Acceptance Criteria

- `same_session_id_different_users_get_independent_buffers` — two users with the same `session_id` resolve to different `ConversationBuffer` instances.
- `same_user_same_session_id_reuses_buffer` — the same user + `session_id` resolves to the same buffer (multi-turn continuity preserved).
- `cache_key_includes_authenticated_identity` — the `_sessions` key carries `current_user.id`, not just `session_id`.
- `cross_user_access_does_not_leak_history` — a user sending the victim's `session_id` gets an empty buffer (no victim turns in `to_messages()`), and the attacker's writes never appear in the victim's buffer.
- No regression: existing tests pass (`pytest tests/ --ignore=tests/test_integration.py`).

## Reproducibility

- Versions: Python 3.12, on the dev host.
- Unit (no infra): `uv run pytest tests/test_chat_concurrency.py tests/test_integration.py -v` — call `_get_or_create_buffer` with two distinct user ids and the same `session_id` and assert distinct, isolated buffers; an endpoint-level test (with `verify_token` overridden per user) asserts a second user cannot read the first user's history.

## Risks and Assumptions

- Assumption: `current_user.id` is the stable primary key (`database/models.py`); it is used as the namespace. `username` would also work, but `id` is the stable PK.
- Assumption: `chat()` already receives `current_user` via `Depends(verify_token)` (confirmed, `api/routes/chat.py:92`) — only the cache key changes.
- Risk: sessions cached under the old key scheme become unreachable after deploy (the cache is in-memory and volatile) — acceptable; nothing persistent is lost.
