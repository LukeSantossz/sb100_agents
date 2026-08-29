"""Guards for the startup scripts, which nothing else in this suite executes.

The defect these exist for: `start.ps1` tested for an installed model with
``$models -notmatch "nomic-embed-text"`` where ``$models`` is the array of lines
from ``ollama list``. Against an array ``-notmatch`` filters rather than
answering, returning every line that does not match, which is essentially always
non-empty, so the branch was always taken and both models were re-downloaded on
every run. Nothing caught it, because nothing ran the script.

So the behavioural test here runs it, against stubbed ``ollama`` and ``docker``
on ``PATH``, from a directory holding only a copy of the script. The stubs record
their arguments, which is what makes this a test of behaviour rather than of the
script's text: a rewrite that reintroduced the bug with different syntax would
still fail it.

``start.bat`` is deliberately not executed. Its final step is
``start "..." cmd /k``, which opens console windows that stay open by design, and
a ``cmd.exe`` builtin cannot be stubbed through ``PATH``. It is covered by the
invariants it shares with ``start.ps1``, which is weaker, and saying so here is
better than a test that leaves windows on someone's desktop when it fails. See
docs/specs/0011.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_START_PS1 = _REPO_ROOT / "start.ps1"
_START_BAT = _REPO_ROOT / "start.bat"

# The two models both scripts are responsible for making present.
_EMBED_MODEL = "nomic-embed-text"
_CHAT_MODEL = "llama3.2:3b"

# `ollama list` output with both models present: the state in which neither
# script has any reason to pull.
_OLLAMA_LIST_OUTPUT = (
    "echo NAME                       ID              SIZE      MODIFIED\n"
    f"echo {_CHAT_MODEL}                a80c4f17acd5    2.0 GB    2 months ago\n"
    f"echo {_EMBED_MODEL}:latest    0a109f422b47    274 MB    4 months ago\n"
)

_OLLAMA_STUB = f"""@echo off
echo %* >> "%OLLAMA_STUB_LOG%"
if "%1"=="list" (
{_OLLAMA_LIST_OUTPUT})
exit /b 0
"""

_DOCKER_STUB = """@echo off
echo docker stub: %*
exit /b 0
"""

requires_powershell = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell") is None,
    reason=(
        "executes a PowerShell script; skipped where PowerShell is absent, which "
        "is every CI runner this project has today"
    ),
)


def _run_start_ps1(tmp_path: Path, script_text: str) -> tuple[str, list[str]]:
    """Run ``script_text`` as start.ps1 against stubs; return stdout and the ollama calls.

    The working directory holds only the script, so the two ``Start-Process``
    calls for ``.venv\\Scripts\\python.exe`` fail as non-terminating errors after
    everything under test has already happened, and nothing real is launched.
    ``-NonInteractive`` turns the closing ``Read-Host`` into an immediate error
    rather than a block.
    """
    script = tmp_path / "start.ps1"
    script.write_text(script_text, encoding="utf-8")

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "ollama.cmd").write_text(_OLLAMA_STUB, encoding="utf-8")
    (stubs / "docker.cmd").write_text(_DOCKER_STUB, encoding="utf-8")

    call_log = tmp_path / "ollama-calls.log"
    call_log.write_text("", encoding="utf-8")

    env = {
        **os.environ,
        "OLLAMA_STUB_LOG": str(call_log),
        "PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=180,
    )
    calls = [
        line.strip() for line in call_log.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return result.stdout, calls


@requires_powershell
def test_start_ps1_does_not_pull_a_model_that_is_already_installed(tmp_path: Path) -> None:
    """The regression this file exists for: an installed model must not be re-pulled.

    Asserting the script reached the model check as well as that it pulled
    nothing. Without that, a script that died on its first line would satisfy
    "no pull happened" and the test would pass for the wrong reason.
    """
    stdout, calls = _run_start_ps1(tmp_path, _START_PS1.read_text(encoding="utf-8"))

    assert "Checking Ollama models" in stdout, (
        f"start.ps1 did not reach the model check, so this test proves nothing.\n{stdout}"
    )
    assert "list" in calls, f"start.ps1 never asked ollama what is installed; calls={calls}"
    assert not any(call.startswith("pull") for call in calls), (
        f"start.ps1 pulled a model that `ollama list` already reported; calls={calls}"
    )
    assert "Downloading" not in stdout, (
        f"start.ps1 announced a download with both models installed.\n{stdout}"
    )


@requires_powershell
def test_the_no_pull_guard_fails_on_the_defect_it_guards(tmp_path: Path) -> None:
    """The guard above must fail on the pre-fix expression, or it guards nothing.

    ``-notmatch`` against the raw array is the exact defect that shipped. Running
    it here keeps the guard honest: if someone "simplifies" the harness until it
    can no longer see the bug, this test goes red.
    """
    fixed = _START_PS1.read_text(encoding="utf-8")
    buggy = fixed.replace(
        "$models = (& $ollamaPath list 2>$null) -join [Environment]::NewLine",
        "$models = & $ollamaPath list 2>$null",
    )
    buggy = buggy.replace(f'-notlike "*{_EMBED_MODEL}*"', f'-notmatch "{_EMBED_MODEL}"')
    buggy = buggy.replace(f'-notlike "*{_CHAT_MODEL}*"', f'-notmatch "{_CHAT_MODEL}"')
    assert buggy != fixed, "the pre-fix expression was not reconstructed; this test is inert"

    stdout, calls = _run_start_ps1(tmp_path, buggy)

    assert [call for call in calls if call.startswith("pull")], (
        "the reconstructed defect did not re-pull, so the harness cannot see it"
    )
    assert "Downloading" in stdout


@requires_powershell
def test_start_ps1_parses() -> None:
    """A syntax error would only surface when a user runs it."""
    probe = (
        "$errs = $null; $tokens = $null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{_START_PS1}', "
        "[ref]$tokens, [ref]$errs) | Out-Null; "
        "if ($errs.Count -eq 0) { 'OK' } else { $errs | ForEach-Object { $_.Message } }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", probe],
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )
    assert result.stdout.strip() == "OK", (
        f"start.ps1 does not parse:\n{result.stdout}{result.stderr}"
    )


def test_both_scripts_check_for_the_same_models() -> None:
    """The two scripts must not drift on which models they guarantee.

    Changing the model in one and not the other leaves half the Windows users
    with a script that pulls the wrong thing, and neither script would complain.
    """
    bat = _START_BAT.read_text(encoding="utf-8")
    ps1 = _START_PS1.read_text(encoding="utf-8")
    for model in (_CHAT_MODEL, _EMBED_MODEL):
        assert model in bat, f"start.bat does not mention {model}"
        assert model in ps1, f"start.ps1 does not mention {model}"

    pulled_by_bat = set(re.findall(r"pull\s+(\S+)", bat))
    pulled_by_ps1 = set(re.findall(r"pull\s+(\S+)", ps1))
    assert pulled_by_bat == pulled_by_ps1, (
        f"the scripts pull different models: start.bat {sorted(pulled_by_bat)} "
        f"vs start.ps1 {sorted(pulled_by_ps1)}"
    )


@pytest.mark.parametrize("script", [_START_BAT, _START_PS1], ids=lambda p: p.name)
def test_startup_scripts_are_ascii_only(script: Path) -> None:
    """Both scripts were Portuguese until #209; ASCII-only is what that left behind.

    A reintroduced Portuguese message would almost certainly carry an accent, and
    the English rule in code_conventions.md covers their comments either way.
    """
    text = script.read_text(encoding="utf-8")
    offenders = sorted({character for character in text if ord(character) > 127})
    assert not offenders, f"{script.name} contains non-ASCII characters: {offenders}"
