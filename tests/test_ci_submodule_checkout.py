"""Guard that CI keeps checking out the ``.standards`` submodule (issue #161).

The standards path guard in ``test_claude_md_paths.py`` self-skips when the
``.standards`` submodule is absent. For that guard to run in CI, the workflow's
``test`` job must check out submodules. This test fails fast if that enabling
input is ever removed, which would silently disable the path guard in CI.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# Values of the actions/checkout ``submodules`` input that enable checkout.
# YAML ``true`` parses to the bool ``True``; ``recursive`` to the string.
_SUBMODULES_ENABLED = ("recursive", "true", True)


def _checkout_step(job: dict) -> dict:
    """Return the ``actions/checkout`` step of a workflow job."""
    for step in job.get("steps", []):
        if str(step.get("uses", "")).startswith("actions/checkout"):
            return step
    raise AssertionError("job has no actions/checkout step")


def test_test_job_checks_out_submodules() -> None:
    """The CI ``test`` job checks out the ``.standards`` submodule.

    Without it, ``test_claude_md_paths.py`` self-skips in CI and a broken
    standards reference passes unnoticed.
    """
    workflow = yaml.safe_load(_CI_WORKFLOW.read_text(encoding="utf-8"))
    checkout = _checkout_step(workflow["jobs"]["test"])
    submodules = checkout.get("with", {}).get("submodules")
    assert submodules in _SUBMODULES_ENABLED, (
        "ci.yml `test` job must check out submodules so the standards path "
        f"guard runs in CI; got submodules={submodules!r}"
    )
