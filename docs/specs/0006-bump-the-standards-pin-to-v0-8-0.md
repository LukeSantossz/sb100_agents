# SPEC: chore(standards): bump the pin to v0.8.0 so the gates here stop passing without checking

## Problem

This repository is pinned to `v0.7.1`, two releases behind. `v0.8.0` closes six
of the harness's own gates that report `ok` while verifying nothing — among them
an exempt-path glob that means different things on Windows than in CI, and an R1
attestation any machine-wide git setting satisfies — and `v0.7.2`, which this
repository also skipped, fixes the header of a generated instruction file.

## Scope

- Includes: the `.standards` pin at `v0.8.0`; `.framework.lock`.
- Does NOT include: any change to this repository's `.framework.toml`, which the
  upgrade preflight below shows needs none; regenerating `CLAUDE.md` or
  `AGENTS.md`, since `v0.8.0` changes no document under `docs/agents/` or
  `docs/standards/` and the agents gate confirms it; adopting
  `paths.agents_overlay`, which this repository still has no project-specific
  instructions to put in.

## Acceptance Criteria

- `the_pin_and_the_lock_name_the_same_version`
- `mf check` passes here against the v0.8.0 binary.
- `mf check agents` reports the generated files still match their source, so no
  regeneration is owed.
- `none_of_the_five_upgrade_cases_applies_to_this_repository`

## Reproducibility

Run with `sh -e`: every line below is an assertion, so the block stops at the
first thing that is not true. A preflight that only prints is one nobody reads.

```sh
mf version | grep -qx 'mf v0.8.0'
git submodule status .standards | grep -q '(v0.8.0)'
grep -q 'framework_version = "v0.8.0"' .framework.lock
mf check
mf check agents

# The five upgrade cases .standards/docs/specs/0050-release-v0-8-0.md lists.
# Each line fails if the case applies here, which is what makes it a preflight.
! grep -qE 'exempt_paths.*"\*"' .framework.toml    # no wildcard exempt path
! grep -qE '^[[:space:]]*file[[:space:]]*=[[:space:]]*""' .framework.toml
! grep -rq 'MF_PATHS_' .github                     # no per-run path override in CI
! git config --global --get mf.attestation.r1      # the attestation here is local
```

Versions: `mf` v0.8.0.

## Risks and Assumptions

- Assumption: nothing here relies on a `paths.*` value from outside the project
  file, on an empty `agents.<name>.file`, or on a wildcard exempt path. Each was
  read out of the tree above rather than assumed.
