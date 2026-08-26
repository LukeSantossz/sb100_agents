"""Guard that the pre-push gate is wired to something that runs (issue #181, FW2).

The guard this replaces asserted the shape of the old wiring: a framework hook
at ``.standards/.githooks/pre-push`` execing a repo-root shim that forwarded to
``.standards/scripts/codex-review.sh``. Every one of those files is gone — the
framework replaced the shell runner with the ``mf`` binary and now ships its
hooks into the adopting repository — so the guard could only have failed.

It also could not fail, which was worse. Every assertion sat behind a skip on
``.standards`` being checked out, and ``.standards`` was not checked out here, so
the suite reported green over a gate that had never once fired: ``core.hooksPath``
was unset, and nothing had noticed since the guard was written.

So the assertions below are deliberately about state this repository owns and
git resolves, not about files inside the submodule, and none of them is skipped.
The one fact that needs the submodule — that the standards it supplies are the
ones the gates read — is asserted through the configuration that names them
rather than by reading them.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _REPO_ROOT / ".githooks"
_PROJECT_FILE = _REPO_ROOT / ".framework.toml"


def _git_config(key: str) -> str:
    """Read a local git-config value, or the empty string when it is unset."""
    result = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        # Detached from whatever stdin this suite inherited: a git subprocess
        # given an invalid handle fails for a reason that has nothing to do
        # with the setting being read.
        stdin=subprocess.DEVNULL,
    )
    return result.stdout.strip()


def test_versioned_hooks_are_present() -> None:
    """Both gates ship into the repository, not into the submodule."""
    for name in ("pre-push", "commit-msg"):
        hook = _HOOKS_DIR / name
        assert hook.is_file(), (
            f".githooks/{name} is missing; `mf init` writes both gates here, and "
            "a hooks directory with only one of them enforces only one of them"
        )


def test_hooks_path_points_at_the_versioned_hooks() -> None:
    """The setting is what makes the hooks run at all.

    This is the assertion the old guard should have made and never did: it
    checked which file the hook execs, and never whether git would reach the
    hook.
    """
    assert _git_config("core.hooksPath") == ".githooks", (
        "core.hooksPath does not point at .githooks, so no hook in it runs. "
        "Run `mf hooks install`. This is the failure this guard exists for: "
        "the gate was documented as active here for months while unset."
    )


def test_hooks_fail_closed() -> None:
    """A hook that cannot reach its runner must stop the push, not pass.

    Executed rather than read: every pre-v0.5.0 hook ended its failure paths
    with ``|| exit 0`` and printed nothing, and the current hook's own comments
    quote that string while explaining why it is wrong — so grepping for it
    fails on the explanation instead of on the behaviour.

    ``MF_BIN`` naming something that is not executable is the cheapest way to
    reach the failure: it is the first branch of the runner lookup, so the hook
    answers without a repository state to arrange.
    """
    for name in ("pre-push", "commit-msg"):
        result = subprocess.run(
            # Repo-relative and slash-separated: bash is handed the path
            # verbatim, and a Windows absolute path arrives with its separators
            # eaten as escapes.
            ["bash", f".githooks/{name}", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "MF_BIN": str(_REPO_ROOT / "no-such-runner")},
        )
        assert result.returncode != 0, (
            f".githooks/{name} exited 0 with an unusable runner; a gate that "
            "cannot run has not passed, it has not run"
        )
        assert "MF_BIN" in result.stderr, (
            f".githooks/{name} refused without saying why; a silent refusal is "
            "the failure mode this hook was rewritten to end"
        )


def test_gates_read_the_standards_the_submodule_supplies() -> None:
    """No second copy of the corpus, and the paths name the submodule."""
    config = tomllib.loads(_PROJECT_FILE.read_text(encoding="utf-8"))
    paths = config["paths"]
    assert paths["standards"].startswith(".standards/"), (
        "paths.standards does not name the submodule, so the gates read a corpus "
        "this repository would have to maintain itself"
    )
    assert not (_REPO_ROOT / "docs" / "standards").exists(), (
        "a second standards corpus exists beside the submodule; the two drift, "
        "and only one of them is updated by `git submodule update`"
    )


def test_r2_chain_names_a_reviewer() -> None:
    """A chain nobody fills reports 'did not run' on every push, forever."""
    config = tomllib.loads(_PROJECT_FILE.read_text(encoding="utf-8"))
    chain = config["roles"]["r2"]["backends"]
    assert chain, (
        "roles.r2.backends is empty, so R2 never runs. That is honest, and it is "
        "not a gate."
    )
    for name in chain:
        assert name in config["backends"], (
            f"the R2 chain names {name!r} and nothing defines it; the runner "
            "reports an unknown backend rather than reviewing"
        )
