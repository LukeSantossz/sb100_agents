# SPEC: fix(ci): run the integration suite in CI by marker, not path exclusion (#104)

## Problem

The CI test job runs `pytest tests/ --ignore=tests/test_integration.py`, yet every test in `tests/test_integration.py` mocks all external services (`generate_embedding`, `search_context`, `generate`, `verify_and_generate`, and the JWT gate via a `verify_token` override) and needs no real Ollama/Qdrant/SQLite. These are the only tests covering the success path (HTTP 200) of `POST /chat` — the RAG pipeline, multi-turn history, the `hallucination_score` contract, expertise adaptation, the structured access log, and (since #108) cross-user session isolation. Because they are excluded, a regression in the `chat()` handler can pass CI green. The same `--ignore` command is copied into the developer docs, perpetuating the exclusion.

## Design Decision

Exclude tests from CI by intent, not by file path. Register a `requires_infra` pytest marker for tests that genuinely need a live external service, and change the CI test job to `pytest tests/ -m "not requires_infra"`. No current test needs infra, so nothing is marked and the full suite — including `test_integration.py` — runs in CI; the marker gives any future infra-bound test a self-documenting home that CI skips. The developer docs are updated to the same command so they stop advertising the path exclusion.

## Alternatives Considered

1. **Drop the `--ignore` and run `pytest tests/` with no marker.** Rejected: it fixes today's exclusion but leaves no mechanism for a genuinely infra-bound test later, so the next such test would again be excluded by an ad-hoc `--ignore`.
2. **Split a separate `integration` CI job for `test_integration.py`.** Rejected: the tests need no infra, so a second job adds cost and config for no isolation benefit; one suite is simpler.
3. **Stand up real Ollama/Qdrant services in CI.** Rejected (out of scope): the success path is already covered by mocks; standing up services is a heavier, slower change unrelated to closing the coverage gap.

## Scope

- **Includes:** register the `requires_infra` marker in `pyproject.toml`; change the CI test command in `.github/workflows/ci.yml` to `-m "not requires_infra"`; update the test command in `README.md`, `CONTRIBUTING.md`, and `.github/workflows/claude-auto.yml` to match; a unit test asserting the marker is registered.
- **Does NOT include:** marking any existing test `requires_infra` (none require infra); adding real services to CI; changing the coverage threshold or which tests exist.

## Acceptance Criteria

- `requires_infra_marker_is_registered` — the `requires_infra` marker is declared in the pytest configuration, so `-m "not requires_infra"` selects without an unknown-marker warning.
- The CI test job runs `pytest tests/ -m "not requires_infra"` (no `--ignore=tests/test_integration.py`), so `test_integration.py` is collected and run.
- The developer docs (`README.md`, `CONTRIBUTING.md`) and `claude-auto.yml` no longer instruct `--ignore=tests/test_integration.py`.
- No regression: the full suite passes under the new selection.

## Reproducibility

- Versions: Python 3.12, pytest, on the dev host.
- `uv run pytest tests/ -m "not requires_infra"` collects and passes `test_integration.py` (no infra needed); `uv run pytest --markers` lists the registered `requires_infra` marker.

## Risks and Assumptions

- Assumption: no current test needs a live service (confirmed — `test_integration.py` mocks every external call). A future infra-bound test must carry `@pytest.mark.requires_infra` to stay out of the default CI selection.
- Risk: none functional; this widens CI coverage. Coverage rises (more code exercised), staying above the `--cov-fail-under=23` gate.
