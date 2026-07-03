#!/usr/bin/env bash
# R2 gate shim for submodule adoption.
#
# The development standards are adopted as a git submodule at .standards/, so the
# framework's pre-push hook (core.hooksPath=.standards/.githooks) looks for its
# runner at <repo_root>/scripts/codex-review.sh. This shim supplies that path and
# forwards to the real runner in the submodule, so the R2 cross-provider review
# actually fires instead of the hook silently exiting 0. See CLAUDE.md and
# .standards/docs/standards/codex_review.md.
set -u

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
runner="$repo_root/.standards/scripts/codex-review.sh"

# Absence must not block the push (mirrors the framework hook): if the submodule
# is not checked out, skip rather than fail.
[ -f "$runner" ] || exit 0

exec bash "$runner" "$@"
