# SPEC: fix(ci): stop a derived file from failing every Dependabot pull request

## Problem

`requirements.txt` is generated from `uv.lock`, committed, and then checked: the
`validate-requirements` job regenerates it and fails if the result differs from
what is in the tree. Dependabot updates `pyproject.toml` and `uv.lock` and
cannot run `uv export`, so every Dependabot pull request arrives with the two
out of step and fails a check that is asking a bot to do something it has no way
to do.

That is most of this repository's red CI: of the last sixty runs, fourteen
failed, and nearly all of them are Dependabot branches or Dependabot's own
update job. The signal is worthless — a red check that says nothing about the
change — and a red check nobody can act on is one people stop reading.

The lint, typecheck and test jobs install `ruff`, `mypy` and `pytest`
unversioned, which is the same failure with a slower fuse: a tool release turns
CI red on a tree nobody touched. It has already happened once in a sibling
repository, where an unpinned `ruff` broke the lint job for three weeks.

## Design Decision

Stop committing the derived file. `requirements.txt` exists for one consumer —
`Dockerfile.api`, which `pip install -r` it — so the builder stage generates it
from `uv.lock` at build time, and the file leaves the repository. There is then
nothing to fall out of step, no job to check that it has not, and a Dependabot
pull request touches exactly the two files that describe the dependencies.

`uv export --locked` is what makes this safe: it refuses to resolve anything,
and it also refuses a lockfile that no longer matches `pyproject.toml`. So the
image is built from the locked versions or the build fails — including in the
case a Dependabot pull request could actually produce, where a dependency is
added to `pyproject.toml` and the lockfile is stale. That is the guarantee the
deleted check was reaching for, applied where it is load-bearing, in the image
that ships, rather than to a copy in git.

The CI tools are pinned to exact versions. A version bump becomes a commit
somebody makes, which is what a dependency change is.

## Alternatives Considered

- **Have a workflow regenerate `requirements.txt` on Dependabot branches and
  push it.** Rejected: it needs write permission on a bot-authored branch, which
  GitHub restricts for exactly the reason it sounds like, and it answers "the
  file drifts" with "a robot will fix it" rather than with "there is no file".
- **Skip `validate-requirements` on Dependabot branches.** Rejected: the check
  would then pass on the one class of change that alters dependencies, which is
  the only time it could ever have caught something.
- **Keep the file and let a human run `uv export` on each Dependabot PR.**
  Rejected: fourteen failures say what happens to a step that depends on someone
  remembering.
- **Replace `pip install -r` with `uv sync` in the image.** Rejected as out of
  scope here: it is a larger change to how the image is built, and it is not
  needed to remove the file.

## Scope

- Includes: generating `requirements.txt` in `Dockerfile.api`'s builder stage,
  with a pinned `uv` installed into the system interpreter rather than into the
  venv the runtime stage receives;
  removing the committed file and ignoring it; deleting the
  `validate-requirements` job; `docker-build.yml` triggering on `uv.lock`
  instead of `requirements.txt`; pinning `ruff`, `mypy`, `types-requests`,
  `pytest`, `pytest-cov` and `httpx` in the CI jobs.
- Does NOT include: changing which dependencies are declared; replacing pip with
  `uv sync` in the image; the runtime stage; anything in `docker-compose.yml`;
  the Dependabot configuration, which this repository does not have — its
  updates come from the repository's security settings.

## Acceptance Criteria

- `the_repository_tracks_no_requirements_file`
- `the_image_builds_from_the_lockfile_without_a_committed_requirements_file`
- `the_docker_build_workflow_triggers_on_a_lockfile_change`
- `every_ci_tool_is_installed_at_a_pinned_version`
- `a_dependency_bump_touching_only_pyproject_and_the_lockfile_passes_ci`

## Reproducibility

```sh
test ! -e requirements.txt                             # gone from the tree
! git ls-files --error-unmatch requirements.txt        # and untracked
docker build -f Dockerfile.api -t sb100-api .          # succeeds
```

Before this change, any branch that edits `uv.lock` without also running
`uv export --frozen --no-dev -o requirements.txt` fails `validate-requirements`.

Versions: Python 3.12, `uv` as resolved in the build.

## Risks and Assumptions

- Risk: the image build now depends on `uv` being installable in the builder
  stage. It is a pip install of a published package, and `docker-build.yml`
  builds the image on every change to the Dockerfile or the lockfile, so a break
  is caught in CI rather than at deploy.
- Risk: `requirements.txt` was a readable record of exactly what shipped.
  `uv.lock` is that record, and it is the one the export is derived from.
- Assumption: nothing outside this repository consumes the committed
  `requirements.txt`. Nothing in the tree references it but `Dockerfile.api` and
  the workflow being deleted.
