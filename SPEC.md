# SPEC: fix(eval): authenticate run_evaluation.py calls to /chat

## Problem

`call_chat_api` POSTs `/chat` with no `Authorization` header (`eval/run_evaluation.py:71-75`), so since the JWT gate every question returns 401 → recorded as `sb100_success: False`. The unauthenticated `/health` preflight (`:192`) still passes, so the run reports "API available", produces an all-failed dataset, and (today) deletes the checkpoint — the evaluation pipeline silently yields empty results.

## Design Decision

Authenticate once at startup and reuse the token for every `/chat` call. Read credentials from the environment — `EVAL_API_TOKEN` if provided (used directly), otherwise `EVAL_USERNAME` + `EVAL_PASSWORD` exchanged for a token via `POST /auth/token`. Attach `Authorization: Bearer <token>` to every `/chat` request in `call_chat_api`. If no credentials are configured, or the token exchange fails, abort before processing any question with a clear message and a non-zero exit — never start a run that can only produce 401s. The token is obtained in `run_evaluation_async` (where the `AsyncClient` and `/health` preflight already live) and threaded into `call_chat_api`.

## Alternatives Considered

1. **Hardcode evaluation credentials in the script or a committed config.** Rejected: ships a secret in a public repo (the class of bug #109 just fixed). Credentials must come from the environment.
2. **Relax `/chat` to allow unauthenticated calls from eval (e.g. an eval bypass header).** Rejected: punches a hole in the exact security gate the audit is closing (#108/#110 build on it); a bypass path is a liability far larger than the eval inconvenience.
3. **Make `/health` require auth so the preflight fails loudly instead.** Rejected: out of scope and wrong layer — `/health` is intentionally unauthenticated for liveness probes (`docker-compose.yml` healthcheck); the fix is to authenticate `/chat`, not to break liveness.

## Scope

- **Includes:** read `EVAL_API_TOKEN` or `EVAL_USERNAME`/`EVAL_PASSWORD` from env; obtain a bearer token (direct or via `/auth/token`) at startup; send `Authorization: Bearer` on every `/chat` call; abort early (non-zero exit, clear message) when credentials are missing or the token exchange fails; document the new env vars in `.env.example` / `eval/README.md`.
- **Does NOT include:** the checkpoint-integrity fixes (#94, #103, #107 — separate PR, though they compose); token refresh during long runs (no tracked issue — a deliberate non-goal); authenticating the other eval stages (`generate_questions.py`, `collect_references.py`, `judge.py`), which use external-provider API keys, not `/chat` (no tracked issue); or any API-side change (API-side auth hardening is tracked separately, e.g. #115).

## Acceptance Criteria

- `call_chat_api_sends_bearer_token` — the `/chat` POST carries `Authorization: Bearer <token>`.
- `missing_credentials_aborts_before_any_request` — with neither `EVAL_API_TOKEN` nor `EVAL_USERNAME`/`EVAL_PASSWORD` set, the run exits non-zero and makes no `/chat` request.
- `token_exchange_failure_aborts_early` — a 401 from `/auth/token` aborts with a clear message and a non-zero exit, before processing questions.
- `explicit_token_is_used_directly` — when `EVAL_API_TOKEN` is set, no `/auth/token` call is made and that token is used.
- No regression: existing `tests/test_eval.py` continues to pass.

## Reproducibility

- Versions: httpx 0.28+, Python 3.12, on the dev host.
- Unit: `uv run pytest tests/test_eval.py -v` with a mocked `AsyncClient` asserting the header and the abort paths.
- Manual (infra-dependent): with API running and `EVAL_USERNAME`/`EVAL_PASSWORD` for a registered user, run `python eval/run_evaluation.py` on a ~10-question dataset → results show `sb100_success: True`. Recorded as "verified locally against live API; not reproducible in CI".

## Risks and Assumptions

- Assumption: `POST /auth/token` returns `{access_token, token_type}` for valid credentials — confirmed (`api/routes/auth.py:155-192`). The `/auth/token` rate limit (`5/15 minutes`) is not a concern: eval logs in once per run.
- Assumption: a registered evaluation user exists in the target API's DB — operator responsibility, documented in `eval/README.md`.
- Risk: long runs could outlive token expiry (`ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7`, 7 days) — far longer than any eval run, so refresh is unnecessary now; note it as a future concern.
