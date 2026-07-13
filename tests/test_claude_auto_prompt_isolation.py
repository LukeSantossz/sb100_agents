"""Guard that claude-auto.yml never feeds untrusted issue content to the agent (issue #111).

The auto-implement workflow runs ``claude-code-action`` with write permissions and
secrets in scope. Its prompt must reference the issue only by number and read the
title/body as isolated data captured via step ``env`` — never ``${{ }}``-interpolated
into the prompt or a ``run`` step (GitHub Actions template injection) — and the job
must not hold ``id-token: write`` it does not use. See ADR-0011.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "claude-auto.yml"

# Attacker-controllable expressions that must never be expanded into the prompt
# or a run step; they may only be captured under a step ``env`` mapping.
_UNTRUSTED_EXPRESSIONS = ("github.event.issue.body", "github.event.issue.title")


def _implement_job() -> dict:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["implement"]


def _claude_step(job: dict) -> dict:
    for step in job.get("steps", []):
        if str(step.get("uses", "")).startswith("anthropics/claude-code-action"):
            return step
    raise AssertionError("claude-auto.yml has no anthropics/claude-code-action step")


def test_prompt_has_no_untrusted_issue_content() -> None:
    """The agent prompt does not interpolate the issue title or body."""
    prompt = str(_claude_step(_implement_job()).get("with", {}).get("prompt", ""))
    leaked = [expr for expr in _UNTRUSTED_EXPRESSIONS if expr in prompt]
    assert not leaked, (
        "claude-auto prompt must not interpolate attacker-controlled issue content; "
        f"found {leaked} (pass the issue number and read an isolated file instead)"
    )


def test_prompt_references_issue_by_number() -> None:
    """The agent is still told which issue to implement, by number."""
    prompt = str(_claude_step(_implement_job()).get("with", {}).get("prompt", ""))
    assert "github.event.issue.number" in prompt, (
        "the agent must still be told which issue to implement, by its number"
    )


def test_untrusted_issue_content_only_under_step_env() -> None:
    """Title/body may be captured in a step ``env`` mapping, never in ``run`` or ``with``."""
    offenders: list[str] = []
    captured_in_env: set[str] = set()
    for step in _implement_job().get("steps", []):
        name = str(step.get("name") or step.get("uses") or "<step>")
        run_blob = str(step.get("run", ""))
        with_blob = " ".join(str(value) for value in step.get("with", {}).values())
        env_blob = " ".join(str(value) for value in step.get("env", {}).values())
        for expr in _UNTRUSTED_EXPRESSIONS:
            if expr in run_blob:
                offenders.append(f"{name}: run -> {expr}")
            if expr in with_blob:
                offenders.append(f"{name}: with -> {expr}")
            if expr in env_blob:
                captured_in_env.add(expr)
    assert not offenders, (
        "untrusted issue content must reach the job only via step env, never "
        f"expanded into run/with (template injection); found: {offenders}"
    )
    missing_from_env = [expr for expr in _UNTRUSTED_EXPRESSIONS if expr not in captured_in_env]
    assert not missing_from_env, (
        "untrusted issue content must be captured under a step env mapping so it is passed as "
        f"isolated data, not interpolated; missing from env: {missing_from_env}"
    )


def test_implement_job_omits_id_token_write() -> None:
    """The job does not request the unused ``id-token: write`` privilege."""
    permissions = _implement_job().get("permissions", {})
    assert permissions.get("id-token") != "write", (
        "claude-auto job must not request id-token: write; no OIDC consumer uses it"
    )
