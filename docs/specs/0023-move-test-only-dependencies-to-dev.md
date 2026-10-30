# SPEC: build(deps): move test-only dependencies out of the runtime install

## Problem

`pytest` is declared as a runtime dependency in `pyproject.toml`, so
`uv export --no-dev` in `Dockerfile.api` ships it, with `pluggy` and `iniconfig`, in
the API image. `types-requests` is declared and installed by the CI typecheck job, but
no module under version control imports `requests`. `.gitignore` lists
`.python-version`, a file the repository tracks, so the rule contradicts the tree.

## Scope

- Includes: `pytest` moved to the `dev` extra; `types-requests` removed from
  `pyproject.toml`, `uv.lock` and the CI mypy install line; the `.python-version` line
  removed from `.gitignore`.
- Does NOT include: any other dependency, version bump or Dependabot PR; the pillow
  advisory blocked by the gradio cap.

## Acceptance Criteria

- `runtime_export_has_no_test_runner`: `uv export --locked --no-dev` lists no
  `pytest`, `pluggy` or `iniconfig`.
- `nothing_imports_requests`: `git grep -nE "^\s*(import|from) requests"` finds nothing.
- `python_version_is_not_ignored`: `git check-ignore .python-version` exits non-zero.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`, `ruff check .`,
  `ruff format --check .` and the CI mypy invocation all pass after `uv sync --extra dev`.
