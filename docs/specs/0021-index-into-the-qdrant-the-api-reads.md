# SPEC: fix(ingest): index into the Qdrant server and collection the API reads

## Problem

`scripts/ingest.py` writes to a Qdrant URL, API key and collection name hardcoded in
`database/semantic_chunker.py`, while the API reads all three from `Settings`, so an
operator who sets `QDRANT_URL`, `QDRANT_API_KEY` or `COLLECTION_NAME` in `.env`, as
the Remote Mode section of `SETUP.md` tells them to, indexes into one place and
queries another.

## Design Decision

The `--qdrant-url`, `--api-key` and `--collection` flags of both subcommands default
to `settings.qdrant_url`, `settings.qdrant_api_key` and `settings.collection_name`,
read when `main()` builds its parser rather than when the module is imported. The
flags stay authoritative when given. The module globals keep their role as the values
`process_folder` and `search` read, and their import-time values come from the same
settings, so nothing in the module names a second default. This is the same shape
spec 0020 gave the embedding model: one source, read at call time, with the CLI as
the only override.

## Alternatives Considered

- **Leave the defaults and document the flags.** No code change, and the defect
  stays: the README and `SETUP.md` tell the operator to configure `.env`, and the one
  command that writes the corpus would still be the one place that ignores it.
- **Replace the globals with resolver functions, as `resolve_embed_model()` does.**
  More uniform with spec 0020, and it touches every one of the dozen call sites that
  read `COLLECTION_NAME`, plus the tests that read it, to fix a bug that lives in two
  argparse defaults. The globals are already overwritten by `main()` on every CLI run;
  only their source was wrong.
- **Read `os.environ` directly in the chunker.** It would skip `.env`, which
  `Settings` loads and the process environment does not, so the native run the README
  documents would still miss the value.

## Scope

- Includes: the argparse defaults of `index` and `search` in
  `database/semantic_chunker.py`; the import-time values of `QDRANT_URL`,
  `QDRANT_API_KEY` and `COLLECTION_NAME`; tests for both subcommands.
- Does NOT include: making `EMBED_DIM` configurable; any change to the query path in
  `retrieval/`; de-duplicating chunks on re-index (#128); the ingest-over-HTTP
  endpoint (#129); the README and `SETUP.md` text, which already describe the fixed
  behaviour.

## Acceptance Criteria

- `the_index_command_targets_the_configured_qdrant`: with the three settings changed,
  `main(["index", path])` hands `process_folder` the configured URL, key and
  collection.
- `the_search_command_targets_the_configured_qdrant`: the same for
  `main(["search", query])`.
- `the_cli_flags_still_win`: `--qdrant-url`, `--api-key` and `--collection` override
  the settings.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`, `ruff check .`,
  `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_semantic_chunker.py -v`.

Found by indexing a clean clone into a collection other than the default:
`COLLECTION_NAME=archives_e2e` in `.env` was ignored by `scripts/ingest.py`, and only
`--collection archives_e2e` reached it.

## Risks and Assumptions

- Assumption: no caller relies on the chunker defaulting to `http://localhost:6333`
  while `Settings` names another host. `Settings` defaults to the same URL, key and
  collection, so with no `.env` the behaviour is unchanged.
- Assumption: `Settings` is importable wherever the chunker runs. It already is:
  `resolve_embed_model()` reads it, and it fails without `JWT_SECRET_KEY`, which the
  README already requires before indexing.
