# SPEC: fix(ui): authenticate the Gradio UI and isolate session state per user

Resolves #89 (send JWT from the UI) and #96 (isolate ChatSession per Gradio user). The two are one change: a correct authentication flow requires per-browser state to hold each user's token, so they share a single design and PR.

## Problem

The Gradio UI never sends an `Authorization` header (`ui/chat_ui.py:102-106`) and has no login flow, so since the JWT gate every `POST /chat` returns 401 and the UI is unusable (#89). Separately, a single module-level `ChatSession` is created once in `create_interface` (`ui/chat_ui.py:290`) and shared by every browser connection, so all users share one `session_id`/history and "New Session" resets everyone — a cross-user context/privacy leak (#96).

## Design Decision

Replace the shared module-level `ChatSession` with a per-browser `gr.State` holding the authenticated session: `{ "token": str | None, "session_id": str, "api_url": str }`, initialised per connection via `interface.load` (fresh `uuid4` session_id, no token). Add a login row (username + password + "Log in" button) that calls `POST /auth/token` (OAuth2 password form) and stores the returned `access_token` in that state. `send_message` becomes a pure function of `(state, message, name, expertise)` that attaches `Authorization: Bearer <token>` and targets the state's `session_id`; on `401` it clears the token in the returned state and surfaces "log in again". Because `gr.State` is per-session in Gradio, two browsers get independent tokens and `session_id`s, which is exactly the #96 fix.

## Alternatives Considered

1. **Keep one module-level `ChatSession`, just add a global token.** Rejected: a module global is shared across all connections, so user B would send with user A's token — this is the #96 leak made worse (auth confusion), not a fix.
2. **Auto-login the container with a single service account (env credentials).** Rejected: the UI is multi-user; collapsing everyone onto one identity defeats per-user auth, audit logging (#116), and the IDOR scoping (#108). Each browser must authenticate as its own user.
3. **Store the token in a browser cookie / `gr.BrowserState`.** Rejected for this change: heavier, persists secrets client-side across reloads, and is unnecessary for the in-session fix; `gr.State` (in-memory, per connection) is the minimal correct primitive. Can be revisited if "stay logged in" is requested.

## Scope

- **Includes:** a login row and handler hitting `POST /auth/token`; a per-session `gr.State` carrying `{token, session_id, api_url}`; `send_message`/`send_with_retry`/`respond` threaded through that state; `Authorization: Bearer` on `/chat`; 401 → clear token and prompt re-login; removal of the shared module-level `ChatSession` instance; per-session `session_id` generation; reset/"New Session" operating on the per-session state only.
- **Does NOT include:** a registration form in the UI (registration stays API-side via `/auth/register` / SETUP; UI account self-service is #124); token refresh / "remember me" persistence (no tracked issue — a deliberate non-goal); rate-limit UX for `/chat` (#110); the server-side session→user binding (#108); or any API-side change (API-side auth hardening is tracked separately, e.g. #115). The UI continues to call existing endpoints only.

## Acceptance Criteria

- `login_exchanges_credentials_for_token` — the login handler POSTs username/password to `/auth/token` and stores the returned `access_token` in the session state.
- `send_message_attaches_bearer_token` — with a token in state, the `/chat` request carries `Authorization: Bearer <token>`.
- `send_message_without_token_does_not_call_chat` — with no token, the UI returns a "please log in" message and makes no `/chat` request.
- `http_401_clears_token_state` — a 401 from `/chat` clears the token in the returned state so the user is prompted to authenticate again.
- `each_session_state_is_independent` — two freshly initialised session states have distinct `session_id`s and independent tokens (no shared module-level `ChatSession`).
- `login_failure_surfaces_friendly_message` — invalid credentials (401 from `/auth/token`) yield a friendly message and leave the token unset.
- No regression: existing `tests/test_chat_ui.py` continues to pass (adapted to the new signatures where they assert call shape).

## Reproducibility

- Versions: gradio 6.13.0, httpx 0.28+, on the dev host.
- Unit: `uv run pytest tests/test_chat_ui.py -v` (mock `httpx.Client` to assert header and call shape).
- Manual (infra-dependent, recorded in PR Evidence): start API + UI, register a user via the API, log in through the UI, ask a question (200 with answer); open a second browser session, log in as a different user, confirm the two histories and `session_id`s are independent and "New Session" affects only the caller. Marked: "verified locally against live API; not reproducible in CI".

## Risks and Assumptions

- Assumption: `POST /auth/token` accepts the OAuth2 password form and returns `{access_token, token_type}` — confirmed (`api/routes/auth.py:155-192`). Invalidated if the token contract changes.
- Assumption: `gr.State` is per-connection in this Gradio version — standard behavior; the manual two-session check is the guard.
- Risk: the existing chat_ui tests assert the old `send_message(message, name, expertise)` signature; they must be updated to the state-threaded signature in the same PR (not deleted), which is in scope.
- Risk: tokens live in server-side `gr.State` for the UI process lifetime; acceptable for an in-session tool. Note in the PR that persistence/refresh is deliberately out of scope.
