# SPEC: fix(chat): keep the active session when the cache is full

## Problem

`_get_or_create_buffer` enforces the cache size limit before it looks the session
up, so at capacity a request for an existing session evicts an entry it did not
need to, and a request for the session that happens to be least recently used
evicts and silently replaces that user's own conversation with an empty buffer.

## Design Decision

Look up first, evict only when an insertion is actually going to happen. A hit
refreshes recency and returns without touching any other entry, which is what an
LRU is supposed to do. A miss evicts down to `_SESSION_MAX_SIZE - 1` before
inserting, so the cache still never exceeds its bound. Nothing else about the
structure changes: the TTL sweep stays where it is, the lock still covers the
whole operation, and the key stays namespaced by user id.

## Alternatives Considered

- **Keep the order and skip eviction when the key is present.** It fixes the
  unnecessary eviction but not the worse half: if the requested key is itself the
  least recently used, it is still evicted before the lookup can find it, and the
  user still loses their history. Half a fix for the same edit.
- **Refresh the timestamp before evicting, so the caller's entry is never
  oldest.** It works by accident rather than by construction, and it leaves the
  eviction running on hits, which is the behaviour that has no reason to exist.

## Scope

- Includes: reordering lookup and eviction in `_get_or_create_buffer`; tests for
  a hit at capacity, for the caller being the least recently used entry, and for
  the bound still holding.
- Does NOT include: the TTL sweep, the cache size or TTL values, persistence of
  history, or any change to `ConversationBuffer`.

## Acceptance Criteria

- `a_hit_at_capacity_evicts_nothing`: with the cache full, requesting an existing
  session returns the same buffer object and leaves every other entry present.
- `the_caller_is_never_evicted_by_its_own_request`: with the cache full and the
  caller's session the least recently used, the returned buffer still holds the
  history it had.
- `a_miss_at_capacity_stays_within_the_bound`: inserting a new session at
  capacity leaves exactly `_SESSION_MAX_SIZE` entries and drops the oldest.
- `a_hit_refreshes_recency`: after a hit, the session is no longer the eviction
  candidate.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_chat_session_cache.py -v`, with
`_SESSION_MAX_SIZE` monkeypatched to a small value so capacity is reachable in a
test rather than after a thousand sessions.

## Risks and Assumptions

- Assumption: eviction to `_SESSION_MAX_SIZE - 1` before an insert is equivalent
  to the previous bound. The previous loop ran `while len >= MAX`, which also
  left room for one, so the ceiling is unchanged.
- What would invalidate this spec: persisting history (#98), which would make an
  eviction lose nothing and reduce this to a pure performance question.
