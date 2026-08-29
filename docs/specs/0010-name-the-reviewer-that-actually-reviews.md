# SPEC: docs(review): name the automated reviewer this repository actually has

## Problem

`.framework.toml` states that no automated pull-request reviewer is wired for
this repository, and `.github/PULL_REQUEST_TEMPLATE.md` makes every PR repeat it,
while CodeRabbit reviews every pull request and posts actionable findings.

## Scope

- Includes: the `[roles.r3]` comment in `.framework.toml` rewritten to say what is
  true and why the chain stays empty; the R3 line of the PR template changed from
  an assertion to a question.
- Does NOT include: adding any backend to `roles.r3.backends`; changing the
  CodeRabbit, Greptile or Copilot installations; any change to R1 or R2.

## Acceptance Criteria

- `framework_toml_does_not_deny_the_reviewer_that_runs`: the `[roles.r3]` comment
  no longer claims no automated reviewer is wired, and names the GitHub Apps that
  review.
- `r3_backends_stays_empty_with_a_recorded_reason`: `roles.r3.backends` is still
  `[]` and the comment says why a GitHub App cannot be an `mf` backend.
- `pr_template_asks_for_the_r3_result`: the template's R3 line asks which app
  reviewed and what it found, instead of stating that none is configured.
- `gates_stay_green`: `mf check` passes, and `pytest tests/ -m "not requires_infra"`,
  `ruff check .` and `ruff format --check .` all pass.
