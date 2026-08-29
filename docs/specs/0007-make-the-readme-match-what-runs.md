# SPEC: docs: make the README match what actually runs

## Problem

Someone who clones this repository and follows the README cannot get the project
running: the documented indexing command raises `ModuleNotFoundError`, the
documented install misses the tooling the documented test command needs, and the
README claims persistence and a hallucination score that the default
configuration does not deliver.

## Design Decision

Fix the documents against measured behaviour rather than change the code to match
the documents. Every command in the README is executed on a clean checkout first,
and only commands that ran are written down. Where reality is worse than the claim
(a neutral verification score without an API key, conversation history that is not
persisted, a first request that outlives the default Ollama timeout) the claim is
replaced by the measured fact, in the Known Issues section where the standards put
it. Three non-document defects surfaced by that walkthrough are fixed at their
source: a missing `.gitattributes`, which lets a Windows checkout rewrite the
committed hooks to CRLF and turns `tests/test_r2_gate_wiring.py::test_hooks_fail_closed`
red; an `.env.example` Ollama timeout too short for the cold start it is copied
for; and the `Settings` default tests reading the developer's `.env` instead of
the class, which made following the documented setup turn the suite red.

## Alternatives Considered

- **Change the code to match the README.** Persisting conversation history and
  defaulting verification to a keyless provider are product decisions with ADRs
  behind them (ADR-0004, ADR-0007). An audit that quietly re-decides them is a
  larger change than the one asked for, and the README would still be the thing
  that had been wrong.
- **Relax `test_hooks_fail_closed` so CRLF hooks pass.** The test is right: a hook
  bash cannot parse is a gate that does not run. Weakening the assertion hides the
  defect on exactly the platform this repository is developed on.
- **Generate a JWT secret automatically when none is set.** It removes one setup
  step and replaces a fail-loud boot with a signing key that varies per process,
  silently invalidating every issued token on restart.

## Scope

- Includes: `README.md` rewritten against executed commands; `SETUP.md`,
  `CONTRIBUTING.md`, `eval/README.md`, `CONTEXT.md` and `docs/roadmap.md`
  corrected where they contradict the code; `.gitattributes` added to keep shell
  scripts and git hooks LF on every checkout; `.env.example` Ollama timeout raised
  to cover the cold start; `tests/test_config.py` detached from the ambient `.env`
  so it asserts the declared default rather than the developer's file.
- Does NOT include: changes to `api/`, `agent/`, `core/`, `retrieval/`,
  `generation/`, `memory/`, `verification/`, `database/` or `ui/`; new features;
  new test cases; persisting conversation history; changing the default
  verification provider; changing any default in `core/config.py`.

## Acceptance Criteria

- `readme_index_command_runs_on_a_clean_checkout`: the indexing command printed in
  the README completes and the Qdrant collection reports a non-zero point count.
- `readme_test_command_runs_after_the_readme_install_command`: the install command
  the README gives leaves `pytest` able to collect and run with the `addopts` in
  `pyproject.toml`.
- `hooks_stay_lf_on_a_windows_checkout`: `tests/test_r2_gate_wiring.py::test_hooks_fail_closed`
  passes on a Windows working tree with `core.autocrlf=true`.
- `readme_states_no_capability_absent_from_the_code`: no README sentence claims
  persisted conversation history, and the hallucination score is described with
  the provider condition under which it is computed.
- `suite_is_green_with_and_without_a_local_env_file`: `pytest tests/ -m "not requires_infra"`
  passes both on a fresh checkout with no `.env` and after `cp .env.example .env`.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`, `ruff check .`,
  `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

```sh
uv sync --extra dev
docker compose --profile infra up -d
uv run python scripts/ingest.py ./archives/
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
uv run --extra dev pytest tests/ -m "not requires_infra"
```

Measured on Windows 11, Python 3.12.13, Docker 29.5.3, Ollama 0.17.7,
`qdrant/qdrant:latest`, `llama3.2:3b`, `nomic-embed-text`, CPU-only.

## Risks and Assumptions

- Assumption: the corpus in `archives/` is the one the README's numbers describe;
  a different corpus changes the indexing time and the chunk count quoted.
- Assumption: the timings quoted are from one CPU-only host and are labelled as
  such, not offered as a benchmark.
- What would invalidate this spec: a decision to persist conversation history or
  to change the default verification provider, either of which would make the
  corrected README wrong again.
