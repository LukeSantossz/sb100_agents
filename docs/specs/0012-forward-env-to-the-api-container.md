# SPEC: fix(docker): forward .env to the containers, which today ignore all but five variables

## Problem

`docker compose --profile app` passes five environment variables to the API
container and `.env` is in `.dockerignore`, so every other setting falls back to
its class default inside the container: verification always returns the neutral
`0.5`, `OLLAMA_TIMEOUT` is 240 whatever `.env.example` ships, and `AGENT_ENABLED`
cannot be turned on at all.

## Design Decision

Add `env_file` to the `api` and `gradio` services, marked `required: false`, and
drop from `environment:` the two entries that are operator settings rather than
container facts. Compose reads `env_file` from the host at up time, so
`.dockerignore` is irrelevant and no secret enters the image. Three entries stay
in `environment:`, which wins over `env_file`, because they are not the
operator's to set: `QDRANT_URL` names a service on the compose network rather
than localhost, `OLLAMA_HOST` keeps the inline override in SETUP 9.1 working, and
`JWT_SECRET_KEY` must keep failing loudly through `:?`. The agent settings are
added to `.env.example` in the same change, since forwarding a variable nobody
knows exists fixes half the problem.

## Alternatives Considered

- **Enumerate every variable in `environment:`.** This is how the list reached
  five: #91 added `JWT_SECRET_KEY` so the container would boot, correctly, and
  nothing since revisited the rest while `Settings` grew to around thirty fields.
  The same omission recurs on the next field added and fails silently, which is
  the failure being fixed.
- **Mount `.env` into the image.** It would put a signing key in a layer, and
  `.dockerignore` excludes it for that reason.
- **`env_file: .env` without `required: false`.** `.env` is gitignored, so a
  clean clone has none and compose would refuse to start over a file the
  repository never ships. Measured: with `required: false` and no `.env`,
  `docker compose config` succeeds and renders only the three authoritative
  variables.

## Scope

- Includes: `env_file` on `api` and `gradio`; `CHAT_MODEL` and `EMBED_MODEL`
  removed from the `api` `environment:` block so `.env` can reach them; the agent
  settings block added to `.env.example`; tests in `tests/test_compose_config.py`
  covering forwarding, precedence and the no-`.env` case; the README limitation
  removed.
- Does NOT include: the SQLite bind mount, which is its own issue; any change to
  `Settings`, to `.dockerignore`, or to the Qdrant service; turning
  `AGENT_ENABLED` on.

## Acceptance Criteria

- `dotenv_values_reach_the_api_container`: with a `.env` setting
  `VERIFICATION_PROVIDER=ollama` and `OLLAMA_TIMEOUT=540`, the rendered `api`
  environment carries both.
- `container_network_settings_win_over_the_dotenv`: with a `.env` setting
  `QDRANT_URL=http://localhost:6333`, the rendered `api` environment still has
  `http://qdrant:6333`.
- `config_succeeds_without_a_dotenv`: with no `.env` in the project directory,
  `docker compose config` exits 0 and the `api` environment carries exactly
  `QDRANT_URL`, `OLLAMA_HOST` and `JWT_SECRET_KEY`.
- `missing_secret_still_fails_loudly`: `docker compose config` with no
  `JWT_SECRET_KEY` still exits non-zero with the `:?` message.
- `env_example_documents_the_agent_settings`: `.env.example` names
  `AGENT_ENABLED`, `AGENT_PROVIDER` and `INTENT_THRESHOLD`.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

Rendered with `docker compose --project-directory <dir> -f <dir>/docker-compose.yml
--profile infra --profile app config --format json`, Docker Compose v5.1.4, with
`JWT_SECRET_KEY` set in the process environment. With a `.env` carrying
`VERIFICATION_PROVIDER=ollama`, `OLLAMA_TIMEOUT=540`, `AGENT_ENABLED=true`,
`CHAT_MODEL=llama3.1:8b` and `QDRANT_URL=http://localhost:6333`, the `api`
environment renders all four of the first values and `QDRANT_URL=http://qdrant:6333`.

## Risks and Assumptions

- Assumption: `environment:` takes precedence over `env_file:` in Compose.
  Measured above rather than assumed, and asserted by a test.
- Assumption: `required: false` is available. It needs Compose 2.24 or newer;
  this repository is on v5.1.4 and `SETUP.md` requires v2 or newer. An older
  Compose fails at `config` time with a parse error, loudly.
- What would invalidate this spec: moving the database path into `.env`, which
  would make `env_file` carry a host path into a container that cannot use it.
  The SQLite issue must set its path in `environment:` for that reason.
