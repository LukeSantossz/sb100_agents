# SPEC: ci(workflows): check out the .standards submodule so the path guard runs in CI

## Problem
The standards path guard (`tests/test_claude_md_paths.py`) self-skips in CI because the workflow checks out the repository without the `.standards` submodule, so a broken standards reference in `CLAUDE.md` or `CONTRIBUTING.md` passes unnoticed.

## Design Decision
Enable submodule checkout on the `test` job's `actions/checkout` step with `submodules: recursive`, so the existing guard executes against the real `.standards` tree. Add a regression test that parses `.github/workflows/ci.yml` and asserts the `test` job's checkout step keeps submodule checkout enabled, so the enabling input cannot be silently removed.

## Alternatives Considered
- Enable submodule checkout on every job's checkout, not just `test`: rejected — only the `test` job runs pytest; `lint`, `typecheck`, and `validate-requirements` do not need the submodule, and a broader change widens surface for no benefit.
- Use `submodules: true` instead of `recursive`: equivalent today (the framework has no nested submodules), but `recursive` is future-proof if the framework later nests a submodule, at no extra cost for the current single-level case.
- Drop the skip guard in `test_claude_md_paths.py` and require the submodule unconditionally: rejected — it would false-fail in any environment that intentionally checks out without submodules (documented in the test's docstring) and does not address the CI config, which is the actual gap.

## Scope
- Includes: one `submodules: recursive` input on the `test` job checkout in `.github/workflows/ci.yml`; a new test asserting that input remains; this SPEC.
- Does NOT include: changing other jobs' checkout; pinning actions by commit SHA (issue #118); altering the guard test's logic; any runtime or application code; adding project dependencies.

## Acceptance Criteria
- ci_test_job_checks_out_submodules: parsing `ci.yml`, the `test` job's checkout step sets `submodules` to a value that enables checkout.
- regression_fails_without_config: the new test fails if the `submodules` input is removed from the `test` job.
- guard_runs_when_submodule_present: `tests/test_claude_md_paths.py` collects and passes (does not skip) when `.standards` is checked out.

## Reproducibility
- New CI guard (PyYAML is a transitive project dependency, present once project deps are installed):
  `uv run --no-project --with pytest --with pyyaml pytest tests/test_ci_submodule_checkout.py -o "addopts=" -v`
- Standards path guard:
  `uv run --no-project --with pytest pytest tests/test_claude_md_paths.py -o "addopts=" -v`
- Versions: `actions/checkout@v4`; pytest 9.x; PyYAML 6.0.3 (pinned in `uv.lock`).

## Risks and Assumptions
- Assumption: `LukeSantossz/my-framework` is and remains public, so the default `GITHUB_TOKEN` can clone the submodule in CI (verified: repository visibility is public). If it becomes private, the checkout needs a token with read access to that repository, which this change does not cover.
- Assumption: PyYAML stays available in the CI `test` environment via the project dependency tree (gradio depends on PyYAML). If that transitive dependency disappears, the new test errors on import and PyYAML would then need to be added to the dev extra.
- Assumption: the framework has no nested submodules today (verified); `recursive` remains correct if that ever changes.
