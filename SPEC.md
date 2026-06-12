# SPEC: fix(docker): pass JWT_SECRET_KEY to the compose api/gradio containers

## Problem

The `api` and `gradio` compose services declare no `JWT_SECRET_KEY` (`docker-compose.yml:48-52`, `81-82`), but both import `core.config`, whose `Settings()` raises at import when the key is empty or `< 32` chars (`core/config.py:66-76`). The documented `docker compose --profile infra --profile app up -d` flow therefore crash-loops both containers before serving a request.

## Design Decision

Pass the secret explicitly to both services with the fail-fast form `JWT_SECRET_KEY=${JWT_SECRET_KEY:?JWT_SECRET_KEY must be set in the host environment or .env}`. Compose substitutes the value from the host environment or the auto-loaded `./.env` file; if it is unset, `docker compose ... up`/`config` aborts immediately with that message instead of starting a container that will crash on import. Both `api` and `gradio` get it because both import `core.config` at startup (the UI reads `settings.chat_timeout`), so both validate the key. The deeper question of why the UI imports the signing secret at all is a larger refactor and is out of scope here.

## Alternatives Considered

1. **`env_file: .env` on each service.** Rejected: it injects the *entire* `.env` (including `GROQ_API_KEY`, `OPENROUTER_API_KEY`, and any future secret) into both containers, widening secret exposure beyond what each needs, and it silently no-ops (empty value) when the key is absent rather than failing loudly. The explicit `${VAR:?msg}` form passes only this one variable and fails fast.
2. **Hardcode a default secret in the compose file.** Rejected: that re-introduces exactly the published-secret vulnerability just removed in #109.
3. **Generate a secret in an entrypoint script at container start.** Rejected: ephemeral per-restart secrets invalidate all previously issued tokens on every restart and add tooling; operators should own a stable secret.

## Scope

- **Includes:** add `JWT_SECRET_KEY=${JWT_SECRET_KEY:?...}` to the `environment:` of both the `api` and `gradio` services in `docker-compose.yml`.
- **Does NOT include:** removing the UI's dependency on `core.config` / the signing secret; the Qdrant exposure hardening (#112); passing Groq/OpenRouter keys to containers; any change to `core/config.py` validation; SHA-pinning or image-tag changes.

## Acceptance Criteria

- `compose_config_api_environment_contains_jwt_secret` — with `JWT_SECRET_KEY` set, `docker compose --profile infra --profile app config` shows the `api` service environment carrying `JWT_SECRET_KEY` with the provided value.
- `compose_config_gradio_environment_contains_jwt_secret` — same for the `gradio` service.
- `compose_config_fails_when_jwt_secret_unset` — with `JWT_SECRET_KEY` absent from the environment and no `.env`, `docker compose --profile app config` exits non-zero with the `:?` message.
- No regression: existing tests stay green (`pytest tests/ --ignore=tests/test_integration.py`).

## Reproducibility

- Versions: Docker Compose v2, on the dev host.
- Red (before): `docker compose --profile infra --profile app up -d` → `api`/`gradio` exit on `Settings` ValidationError (crash-loop).
- Green (after): `JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))") docker compose --profile app config` prints both services with the variable; unsetting it makes `config` abort.
- TDD category B (compose has no in-process harness): red/green captured via `docker compose config` output in the PR Evidence; an optional pytest may shell out to `docker compose config` and assert the variable is present, marked infra-dependent.

## Risks and Assumptions

- Assumption: compose auto-loads `./.env` for variable substitution and reads host env — standard Compose v2 behavior. Invalidated only if the project disables env-file interpolation.
- Assumption: both containers need the key because both import `core.config` — confirmed (`ui/chat_ui.py:38`, `api/main.py`). If the UI is later decoupled from the signing secret, the `gradio` entry can be dropped.
- Risk: operators who never set `JWT_SECRET_KEY` will now see compose abort; this is the intended fail-loud behavior and pairs with #109 (empty example) and the inline generation command.
