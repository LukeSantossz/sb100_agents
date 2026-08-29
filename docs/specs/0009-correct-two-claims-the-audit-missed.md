# SPEC: docs: correct two claims the audit missed

## Problem

Two statements that survived the audit in #208 are false: the documented way to
index one PDF silently indexes nothing and exits `0`, and the README says the
Gradio process imports no domain module when it imports `core.config`.

## Scope

- Includes: the "index a specific file" command removed from `SETUP.md` and from
  the `scripts/ingest.py` docstring, replaced by a statement of what the argument
  actually has to be; the README sentence about the Gradio process corrected to
  name the module it imports.
- Does NOT include: making single-file ingestion work, which is a behaviour
  change and is filed as its own issue; any change to `process_folder`, to
  `scripts/ingest.py` beyond its docstring, or to `ui/chat_ui.py`.

## Acceptance Criteria

- `no_document_shows_a_command_that_indexes_nothing`: no file under version
  control passes a `.pdf` path to `scripts/ingest.py`, because
  `process_folder` globs `**/*.pdf` under the argument and a file path matches
  nothing, so the run logs `semantic_chunker.no_pdfs_found` and exits `0`.
- `readme_names_the_module_the_ui_imports`: the README states that
  `ui/chat_ui.py` imports `core.config`, and no longer claims it imports no
  domain module.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.
