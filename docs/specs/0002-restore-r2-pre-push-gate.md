# SPEC: chore(process): restore the R2 pre-push gate under submodule adoption

## Problem
The R2 cross-provider pre-push gate never runs: the framework hook execs `<repo_root>/scripts/codex-review.sh`, which is absent under `.standards` submodule adoption, so every push silently skips R2 despite `codex` being installed.

## Scope
- Includes:
  - `scripts/codex-review.sh` (new): a thin shim that forwards to `.standards/scripts/codex-review.sh`, preserving env, arguments, and exit status, and skipping gracefully (`exit 0`) when the submodule runner is absent — mirroring the framework hook's own "absence must not block the push" behavior.
  - `tests/test_r2_gate_wiring.py` (new): a deterministic guard asserting the pre-push hook targets `scripts/codex-review.sh`, the shim exists and forwards to `.standards/scripts/codex-review.sh`, and the submodule runner is present; self-skips when `.standards` is not checked out (mirroring `test_claude_md_paths.py`).
  - `CLAUDE.md`: correct the Review-composition Adoption Note so it states R2 is active — `codex` is the configured Reviewer, `core.hooksPath` is `.standards/.githooks`, and the repo-root shim supplies the runner — instead of "not activated here".
- Does NOT include:
  - Editing any `.standards/` submodule file (the submodule-aware fix to `setup.sh` / `docs-consistency.sh` is upstream and tracked separately).
  - Copying framework scripts or hooks into the repo root (rejected: it forks the framework and defeats submodule adoption).
  - Committing the pending `.standards` submodule-pointer bump (FW6, a separate change).
  - Versioning `core.hooksPath` (it is local git config, not a committable file) or editing the R3 / ephemeral-SPEC Adoption Notes.

## Acceptance Criteria
- `shim_exists_and_forwards_to_submodule_runner`: `scripts/codex-review.sh` exists and its body forwards to `.standards/scripts/codex-review.sh`.
- `pre_push_hook_targets_the_repo_root_shim`: `.standards/.githooks/pre-push` references `scripts/codex-review.sh` (guard self-skips if `.standards` is absent).
- `submodule_runner_present_when_standards_checked_out`: `.standards/scripts/codex-review.sh` exists.
- `claude_md_states_r2_active`: `CLAUDE.md` no longer states R2 "is not activated"; it names `codex` as the Reviewer and the repo-root shim, and `test_claude_md_paths.py` stays green (every `.standards/...` reference still resolves).
- `suite_green`: `pytest tests/ -m "not requires_infra"` passes.
