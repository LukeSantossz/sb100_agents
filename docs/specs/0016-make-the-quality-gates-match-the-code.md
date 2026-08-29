# SPEC: chore(quality): raise the coverage floor and type-check every package declared strict

## Problem

The CI coverage gate is `--cov-fail-under=23` while measured coverage is 89.88%,
so a regression could delete most of the tested behaviour and still pass, and CI
type-checks three packages while `pyproject.toml` declares seven strict, so four
of them are never checked anywhere but a developer's machine.

## Design Decision

Raise the floor to 70 and extend the CI mypy invocation to all seven declared
packages. 70 rather than 89 because a gate set at the current measurement turns
red on ordinary variation and teaches people to lower it; 70 is the target the
README already names and leaves about twenty points of headroom. The typecheck
job also starts installing the project, because mypy without the dependencies
sees every third-party import as `Any` and `strict` reasons differently about
`Any` than about a real type: the job would otherwise be checking a different
program than the one a developer checks.

## Alternatives Considered

- **Set the floor at the measured 89.88%.** It locks in today's number, and the
  first honest refactor that moves a few statements turns CI red for no defect.
  A floor is a floor, not a ratchet.
- **Leave the CI mypy invocation and narrow the `pyproject.toml` overrides to the
  three packages CI checks.** It makes the two agree by giving up on four
  packages that already pass strict today, which is throwing away a property the
  code has earned.
- **Keep the typecheck job dependency-free for speed.** It is faster and it
  checks something other than what it claims: with every import resolving to
  `Any`, strict mode's `warn_return_any` and `disallow_any_*` rules fire on
  different lines than they do locally, so green in CI would not mean green for a
  contributor.

## Scope

- Includes: `--cov-fail-under` raised to 70 with the stale comment replaced; the
  CI typecheck job installing the project and running mypy over `agent`, `api`,
  `core`, `retrieval`, `generation`, `memory` and `verification`; a test that the
  floor and the checked packages do not silently drift apart again.
- Does NOT include: writing tests to raise actual coverage, in particular for
  `retrieval/ollama_embeddings.py`; changing the `[tool.mypy]` strictness; adding
  a Windows CI runner; changing the lint or test jobs.

## Acceptance Criteria

- `the_floor_is_at_least_seventy`: `--cov-fail-under` in `pyproject.toml` is 70 or
  higher.
- `the_suite_passes_at_the_new_floor`: the full selection still passes, so the
  floor is below the real number rather than aspirational.
- `ci_type_checks_every_package_declared_strict`: every module named in a
  `[[tool.mypy.overrides]]` block with `strict = true` appears in the CI mypy
  command.
- `mypy_passes_on_all_of_them`: `mypy agent/ api/ core/ retrieval/ generation/
  memory/ verification/` reports no issues.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .` and `ruff format --check .` all pass.

## Reproducibility

`uv run --extra dev mypy agent/ api/ core/ retrieval/ generation/ memory/
verification/` reports `Success: no issues found in 29 source files`.
`uv run --extra dev pytest tests/ -m "not requires_infra"` reports the coverage
total the floor is set against.

## Risks and Assumptions

- Assumption: coverage does not vary by more than twenty points between runs or
  platforms. It is deterministic here; the marker-excluded tests are the same on
  every runner.
- Assumption: installing the project in the typecheck job does not change what
  mypy reports, because that is what a developer already runs. If it does, the
  difference was a bug in the gate, not in the code.
- What would invalidate this spec: raising real coverage far above 89.88%, which
  would make 70 loose enough to be worth revisiting.
