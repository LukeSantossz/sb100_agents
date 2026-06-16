# SPEC: chore(standards): adopt the updated my-framework standards

## Problem
The `.standards` submodule is pinned to the framework's first version (`9c291b2`); the
latest `main` (`776a1b5`) relocates `token_economy.md` into `docs/standards/`, which turns
the project `CLAUDE.md` reference `.standards/token_economy.md` into a dangling path and
leaves the project without the framework's new ADR flow and domain glossary.

## Design Decision
Bump the submodule to `776a1b5` and adopt the new surface at the project level: repoint the
broken `token_economy.md` reference, add a self-skipping regression test asserting every
`.standards/...` reference in `CLAUDE.md` and `CONTRIBUTING.md` resolves on disk, seed a
SmartB100 `CONTEXT.md` domain glossary, backfill the README's already-resolved Engineering
Decisions into durable ADRs under `docs/adr/`, and re-index those decisions from the README.
The Codex R2 pre-push gate ships in the framework but stays unactivated (no second provider
in this project), consistent with the existing Adoption Notes.

## Alternatives Considered
- Minimal bump (submodule + path fix only). Rejected: leaves the README Engineering
  Decisions non-compliant with the updated `github.md` (rows must link ADRs) and forgoes the
  domain glossary the Developer explicitly opted into.
- Lazy creation of `CONTEXT.md`/ADRs via `/grill-with-docs` only (the framework's default
  path). Rejected for this change because the decisions being recorded are already resolved
  and documented in the README; backfilling them once makes the README compliant now. Future
  decisions still flow through the lazy path.
- Activate the Codex R2 gate. Rejected: no second LLM provider is configured here; R1 plus
  the human CRURA review continue to stand in for R2, per the Adoption Notes.

## Scope
- Includes: submodule bump to `776a1b5`; `CLAUDE.md` `token_economy` path fix and wording
  sync; Adoption Notes refresh; a self-skipping `CLAUDE.md`/`CONTRIBUTING.md` path-resolution
  test; `CONTEXT.md` (SmartB100 glossary); `docs/adr/0001`–`0007` backfilled from the README;
  README Engineering Decisions rewritten to index those ADRs.
- Does NOT include: activating the Codex R2 pre-push gate or `core.hooksPath`; copying the
  framework's agent skills (issue-tracker/triage/domain) or `AGENTS.md` into the project; any
  change to application code, tests of application behavior, CI workflows, or the 47-issue
  implementation roadmap; resolving any codebase-review finding.

## Acceptance Criteria
- `standards_submodule_points_at_776a1b5`: `git submodule status .standards` shows `776a1b5`.
- `claude_md_standards_paths_resolve`: `pytest tests/test_claude_md_paths.py` passes with the
  submodule initialized, and skips (not fails) when `.standards/` is absent.
- `readme_engineering_decisions_link_adrs`: every Engineering Decisions row links a file that
  exists under `docs/adr/`.
- `no_dangling_standards_reference`: no `.standards/...` reference in `CLAUDE.md` or
  `CONTRIBUTING.md` points at a missing file.

## Reproducibility
- `git submodule update --init .standards`
- `git -C .standards rev-parse HEAD` resolves to `776a1b5...`
- `pytest tests/test_claude_md_paths.py -q --no-cov`
- `ruff check . && ruff format --check .`
- Versions: Python 3.12; ruff/pytest pinned in `pyproject.toml`.

## Risks and Assumptions
- Assumption: no second LLM provider (Codex) is available in this project, so R2 stays off.
  Invalidated if the Developer has Codex configured, in which case activation is the local
  opt-in `git config core.hooksPath .standards/.githooks`.
- Assumption: CI does not check out the submodule (confirmed: `ci.yml` uses a bare
  `actions/checkout@v4`), so the new path test must self-skip when `.standards/` is empty.
- Risk: the seeded `CONTEXT.md` and backfilled ADRs reflect today's code and go stale if not
  maintained via `/grill-with-docs`. Mitigated by keeping them small and decision-focused.
