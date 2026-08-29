# SPEC: fix(docker): make the app profile start on a clean clone

## Problem

`docker compose --profile app up` bind-mounts `./smartb100_v2.db`, a path that is
guaranteed absent on a fresh clone because it is gitignored, so Docker creates it
as a directory and the API refuses to start until the operator creates the file
by hand.

## Design Decision

Mount a directory instead of a file. `database/db.py` gains an environment
override for the database path, and the compose services set it to
`/app/data/smartb100_v2.db` with `./data:/app/data` mounted. Docker creating
`./data` as a directory is then correct rather than the bug, and SQLite creates
the file inside it on first boot. The native default is unchanged, so an existing
`./smartb100_v2.db` keeps working and nobody's local database moves. The path is
resolved by a pure function taking the environment as an argument, so it can be
tested without reloading the module that builds the engine at import.

## Alternatives Considered

- **A named volume, as ADR-0014 does for Qdrant.** It solves the same problem and
  for a related reason, but the database stops being inspectable from the host,
  which is a real loss on a single-node development deployment where reading the
  `users` table with any SQLite client is a normal thing to do. Qdrant storage is
  opaque anyway, so the trade is not the same one.
- **Create the file before the mount**, in the documented command or a compose
  init service. Cheapest, and it keeps the trap: the mount is still wrong and the
  workaround is still load-bearing, just hidden one level down.
- **Read the path from `Settings` rather than the environment directly.** It
  would put the knob where every other knob lives, but `database/db.py` does not
  import `core.config` today, and adding that import makes the database layer
  depend on JWT validation passing. The variable is deliberately not in
  `.env.example` either: it is a container fact, set in `environment:` where
  `QDRANT_URL` is, not something an operator tunes.

## Scope

- Includes: `resolve_db_path` in `database/db.py` honouring `SMARTB100_DB_PATH`;
  the compose `api` service switching from the file bind mount to `./data:/app/data`
  plus the path variable; tests for the resolver and the rendered mount; the
  README limitation removed; `SETUP.md` losing the manual pre-step.
- Does NOT include: moving the native default database location; a named volume;
  any change to the schema, to `Settings`, or to the Qdrant service; adding the
  variable to `.env.example`.

## Acceptance Criteria

- `db_path_defaults_to_the_repository_root`: with no override in the environment,
  the resolved path is `<repo>/smartb100_v2.db`, unchanged from today.
- `db_path_honours_the_override`: with `SMARTB100_DB_PATH` set, the resolved path
  is exactly that value.
- `blank_override_is_ignored`: an empty or whitespace-only value falls back to the
  default rather than resolving to the current directory.
- `directory_guard_still_fires`: a path that exists and is a directory still
  raises `RuntimeError` naming the path.
- `compose_mounts_a_directory_not_the_database_file`: the rendered `api` service
  has no bind mount whose target is `/app/smartb100_v2.db`, and has one at
  `/app/data`.
- `compose_points_the_api_at_the_mounted_directory`: the rendered `api`
  environment sets `SMARTB100_DB_PATH` under `/app/data`.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`docker compose --project-directory <dir> -f <dir>/docker-compose.yml --profile
infra --profile app config --format json` with `JWT_SECRET_KEY` set, Docker
Compose v5.1.4. The end-to-end check is `git clone` followed by
`docker compose --profile infra --profile app up -d` with no manual file
creation, which is what the issue asks for.

## Risks and Assumptions

- Assumption: SQLite creates the database file when its parent directory exists.
  The mount guarantees `/app/data` exists before the process starts.
- Assumption: keeping the native default at the repository root is what existing
  operators want. Moving it would orphan every local database silently, which is
  worse than one more path to know about.
- What would invalidate this spec: a decision to run more than one API replica,
  which makes a host directory the wrong place for the database regardless of how
  it is mounted.
