"""Guard that the R2 cross-provider pre-push gate actually fires (issue #181, FW2).

This repo adopts ``.standards`` as a submodule, so the framework pre-push hook
(``.standards/.githooks/pre-push``) execs ``<repo_root>/scripts/codex-review.sh``.
That path does not exist under submodule adoption unless a repo-root shim forwards
to the submodule's runner; without it the hook silently ``exit 0``s and R2 never
runs (gate theater). This guard fails if the shim is missing or stops forwarding.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PRE_PUSH = _REPO_ROOT / ".standards" / ".githooks" / "pre-push"
_SHIM = _REPO_ROOT / "scripts" / "codex-review.sh"
_SUBMODULE_RUNNER = _REPO_ROOT / ".standards" / "scripts" / "codex-review.sh"
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"

_needs_standards = pytest.mark.skipif(
    not _PRE_PUSH.is_file(),
    reason="`.standards` submodule not checked out; R2 wiring guard needs it",
)


@_needs_standards
def test_pre_push_hook_targets_repo_root_shim() -> None:
    """The framework hook execs ``scripts/codex-review.sh`` at the repo root."""
    hook = _PRE_PUSH.read_text(encoding="utf-8")
    assert "scripts/codex-review.sh" in hook, (
        "pre-push hook no longer targets scripts/codex-review.sh; the shim path "
        "assumption changed — re-check the R2 wiring"
    )


def test_repo_root_shim_exists_and_forwards_to_submodule_runner() -> None:
    """The shim the hook execs exists and forwards to the submodule's runner."""
    assert _SHIM.is_file(), (
        "scripts/codex-review.sh is missing; the pre-push hook will silently "
        "exit 0 and the R2 gate will never run (gate theater, FW2)"
    )
    shim = _SHIM.read_text(encoding="utf-8")
    assert ".standards/scripts/codex-review.sh" in shim, (
        "the shim must forward to .standards/scripts/codex-review.sh so R2 runs"
    )


@_needs_standards
def test_submodule_runner_present() -> None:
    """The framework's actual R2 runner exists to be forwarded to."""
    assert _SUBMODULE_RUNNER.is_file(), (
        ".standards/scripts/codex-review.sh is missing; run "
        "`git submodule update --init`"
    )


def test_claude_md_states_r2_gate_is_active() -> None:
    """CLAUDE.md's Adoption Note reflects that R2 is wired, not 'not activated'."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    assert "not activated here" not in text, (
        "CLAUDE.md still claims the R2 gate is not activated; update the "
        "Review-composition Adoption Note to reflect that codex is wired"
    )
    assert "codex-review.sh" in text, (
        "CLAUDE.md should name the repo-root shim that makes the R2 gate fire"
    )
