# SPEC: test(scripts): cover the startup scripts, which no test executes

## Problem

Nothing in the suite reads or runs `start.bat` or `start.ps1`, so the defect that
made `start.ps1` re-download both Ollama models on every run was found by hand
and would regress without anything noticing.

## Design Decision

Test `start.ps1` by executing it against stubbed `ollama` and `docker` on `PATH`,
from a temporary directory holding only a copy of the script. The stubs record
what they were called with, so the assertion is about behaviour, not about the
text of the script. Running from a directory with no `.venv` makes the two
`Start-Process` calls fail harmlessly after the point under test, and
`-NonInteractive` turns the closing `Read-Host` into an immediate error instead
of a block, so the run always terminates. The tests skip rather than fail where
PowerShell is unavailable, which is every CI runner this project has today.

`start.bat` gets no execution test. Its last step is `start "..." cmd /k`, which
opens console windows that stay open by design, and there is no way to stub a
`cmd.exe` builtin through `PATH`. It is covered by the invariants it shares with
`start.ps1` instead, which is weaker and is recorded as such rather than papered
over.

## Alternatives Considered

- **Assert on the text of the model check.** A test that greps for `-notlike`
  passes for the wrong reason: it locks in one spelling of the fix rather than
  the behaviour, and it would have passed against a rewrite that reintroduced the
  bug with different syntax. The bug was an expression evaluating wrongly, so the
  test has to evaluate it.
- **Refactor the scripts to expose a testable entry point**, for example a
  `-CheckOnly` switch. It would make both scripts testable symmetrically, but it
  changes the interface a reader is told to run in order to make it observable,
  and the stub harness gets the same evidence without touching them.
- **Run `start.bat` too and clean up the windows afterwards.** Killing console
  windows a test spawned is racy, and a test that leaves windows open when it
  fails is worse than one that does not run.

## Scope

- Includes: `tests/test_start_scripts.py` with a PowerShell syntax check, a
  behavioural regression test for the model-presence check, and two invariants
  that hold on every platform.
- Does NOT include: any change to `start.bat` or `start.ps1`; a Windows job in
  the CI matrix; any change to `pyproject.toml` markers.

## Acceptance Criteria

- `installed_models_are_not_re_pulled`: running `start.ps1` with both models
  reported as installed prints no `Downloading` line and calls `ollama` with
  `list` but never `pull`.
- `the_regression_test_fails_on_the_defect_it_guards`: the same test, run against
  the pre-fix expression, sees both `Downloading` lines and two `pull` calls.
- `start_ps1_parses`: the PowerShell parser reports no errors for `start.ps1`.
- `both_scripts_name_the_same_models`: the model identifiers checked by
  `start.bat` and by `start.ps1` are the same set.
- `startup_scripts_stay_ascii`: neither script contains a non-ASCII character,
  which is what the translation in #209 left behind and what a reintroduced
  Portuguese message would break.
- `tests_skip_off_windows`: on a platform without PowerShell the executing tests
  skip and the suite stays green.

## Reproducibility

`uv run --extra dev pytest tests/test_start_scripts.py -v` on Windows 11 with
Windows PowerShell 5.1. On Linux the two executing tests report `SKIPPED`.

Red-green evidence for the regression test, gathered before it was written, by
running the harness against the pre-fix expression:

```
--- Downloading lines in output ---
Downloading the embedding model...
Downloading the chat model...
--- OLLAMA CALLS ---
list
pull nomic-embed-text
pull llama3.2:3b
```

and against the current script:

```
--- Downloading lines in output ---
(none)
--- OLLAMA CALLS ---
list
```

## Risks and Assumptions

- Assumption: `Start-Process` failing on a missing `.venv\Scripts\python.exe`
  stays a non-terminating error, so the script reaches its end. If that changed,
  the test would fail loudly rather than silently pass, because it also asserts
  the script reached the model check.
- Assumption: the stubs are `.cmd` files found through `PATH` by `Get-Command`.
  A PowerShell that resolved `ollama` some other way would not see them, and the
  test would then exercise the real binary, which the assertion on the call log
  would expose.
- What would invalidate this spec: adding a Windows CI runner, which would turn
  the skips into real coverage and make the `start.bat` gap worth closing too.
