# SPEC: refactor: translate code comments, docstrings, and internal messages to English

## Problem

The framework requires English for all code text, but ~459 Portuguese occurrences (docstrings, comments, log and internal exception messages, one identifier) span ~40 source and test files, in three coexisting styles (accented PT, accentless PT in eval/, English).

## Design Decision

Translate package by package with one commit per package, rewriting comments simply and directly (meaning-preserving, not word-for-word), removing historical task references (TASK-Txx), and renaming the single Portuguese identifier `resultados` to `results`. No logic changes; tests asserting any translated internal message are updated in the same commit as the message.

## Alternatives Considered

- Translate only files touched by future work (opportunistic migration): rejected — leaves three language styles coexisting indefinitely; the author chose full migration at the adoption review.
- Keep TASK-Txx references as traceability: rejected — the task registry was removed from the repo; git history and PRs carry the traceability, and the references point to a tracker that no longer exists.

## Scope

- Includes: docstrings, comments, log messages, internal exception messages, and inert test fixture strings across api/, core/, database/, generation/, memory/, retrieval/, verification/, ui/, eval/, scripts/, tests/; `resultados` → `results`; eval/README.md.
- Does NOT include: LLM system prompts, anti-injection context markers, Gradio UI labels, HTTP error details shown to users, and the verification fallback message (#139); any logic, behavior, or quality fix tracked in open issues (#89–#135), including str(e) in 503 details, semantic_chunker globals, and %-format logging; eval/dataset/ and eval/results/ data files; the .standards/ submodule.

## Acceptance Criteria

- accent_grep_gate_returns_empty_for_all_python_files
- no_task_reference_remains_in_comments_or_docstrings
- vector_store_uses_results_identifier
- full_test_suite_passes_unchanged
- ruff_check_and_format_pass
- mypy_scope_passes_unchanged

## Reproducibility

`uv run pytest tests/ -v --ignore=tests/test_integration.py`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy retrieval/ generation/ memory/ --ignore-missing-imports`; `git grep -nP "[\x{00C0}-\x{00FF}]" -- '*.py'` returns empty except #139-scoped strings; `git grep -nE "TASK-T[0-9]+" -- '*.py'` returns empty.

## Risks and Assumptions

- Assumption: eval/ LLM instructions that intentionally produce Portuguese output for the PT corpus keep an explicit English instruction "in Portuguese (pt-BR)"; output-language behavior of the eval pipeline is preserved.
- Assumption: no test asserts log text via caplog with Portuguese content (verified by grep).
- Risk: translated lines exceeding ruff line-length 100 — rewrapped manually; `ruff check` is the gate.
- Risk: accidental change to #139-scoped strings — those constants are listed and left byte-identical; the PT-string assertions tied to them stay untouched.
