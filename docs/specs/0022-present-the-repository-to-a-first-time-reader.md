# SPEC: docs: present the repository to a first-time reader

## Problem

A reader who opens the README cannot tell what the shipped corpus is, gets a mypy
command that checks three of the seven packages CI checks, reads test and coverage
figures from an older state of the code (370 tests, 90 percent, a 23 percent floor
that is now 70), sees "raise the CI coverage floor" listed as pending when it is done,
and finds no list of the command-line entry points the project exposes.

The repository also shipped the bulletin itself, `archives/smart_boletim.pdf`. The 2022
edition is sold, through the Fundag store, and is not ours to redistribute. The file has
been removed from the whole history; this change keeps it from coming back and tells the
reader where the corpus comes from.

## Scope

- Includes: naming the IAC Boletim 100 as the corpus in `archives/` and where to get it;
  ignoring everything under `archives/` except a `.gitkeep` that keeps the folder; the mypy command
  copied from `.github/workflows/ci.yml`; the test count and coverage measured on a fresh
  clone of `92fc9a1`; dropping the done item from Not done; a table of the command-line
  entry points under API Reference.
- Does NOT include: SETUP.md, CONTRIBUTING.md, any code, the visual identity, or the
  history rewrite itself, which happens outside any commit.

## Acceptance Criteria

- `readme_names_the_corpus`: the README names the bulletin, its publisher and its year.
- `bulletin_is_not_shipped`: `git check-ignore archives/smart_boletim.pdf` matches, the
  folder exists on a fresh clone, and the README says the reader brings their own copy.
- `every_documented_command_runs`: each command in the new table starts and prints its
  help with `--help` on a fresh `uv sync --extra dev`.
- `mypy_command_matches_ci`: the README mypy line lists the same packages and flag as
  the CI typecheck job.
- `figures_match_a_measured_run`: the test count and coverage are the ones a fresh
  clone of `92fc9a1` reported (465 passed, 82.53 percent, floor 70).
