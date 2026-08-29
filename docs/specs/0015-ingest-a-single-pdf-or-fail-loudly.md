# SPEC: fix(ingest): index a single PDF path instead of silently indexing nothing

## Problem

`python scripts/ingest.py ./archives/some.pdf` exits `0` having indexed nothing,
because `process_folder` globs `**/*.pdf` beneath its argument and a path to a
file matches nothing; a mistyped directory fails the same silent way, leaving an
empty collection and a `/chat` that answers from no context.

## Design Decision

Split discovery from processing. A new `discover_pdfs` returns the PDFs a path
denotes: the file itself when the path is a PDF file, every `**/*.pdf` beneath it
when it is a directory, and nothing otherwise. When it finds nothing the run ends
non-zero with a message naming the path, rather than warning and returning
success. `main` returns an exit code and both entry points propagate it, so the
silence is impossible to reproduce from either.

## Alternatives Considered

- **Keep it directory-only and rely on documentation.** That is the state #210
  shipped: honest, and still wrong for the user, because the obvious thing to type
  fails and now not even a docstring contradicts it.
- **Fail only on a path that does not exist, keeping the empty-match warning.** It
  would fix the typo case and leave the reported one: a real directory holding no
  PDFs still reports success having built nothing, which is the same silence with
  a smaller blast radius.
- **Accept any file and let PyMuPDF reject non-PDFs.** It moves the error later
  and reports it per file, so a directory of mixed content would half-index and
  still exit non-zero, which is harder to reason about than refusing up front.

## Scope

- Includes: `discover_pdfs` in `database/semantic_chunker.py`; `process_folder`
  using it and raising when it finds nothing; `main` returning an exit code;
  `scripts/ingest.py` propagating it; the single-file form restored to `SETUP.md`
  and to the `scripts/ingest.py` docstring; tests.
- Does NOT include: the task prefixes or the hardcoded embedding model, which are
  their own issues; recursive symlink handling; any change to chunking, to the
  Qdrant schema, or to the `search` subcommand.

## Acceptance Criteria

- `a_pdf_file_path_is_indexed`: `discover_pdfs` on a path to a PDF returns that
  file.
- `a_directory_is_searched_recursively`: `discover_pdfs` on a directory returns
  every PDF beneath it, nested ones included, in a deterministic order.
- `a_non_pdf_file_is_not_indexed`: `discover_pdfs` on a path to a non-PDF file
  returns nothing.
- `a_missing_path_yields_nothing`: `discover_pdfs` on a path that does not exist
  returns nothing rather than raising.
- `an_empty_result_ends_the_run_non_zero`: `main` returns a non-zero exit code for
  a missing path, for a file that is not a PDF, and for a directory holding no
  PDFs, and the message names the path.
- `the_wrapper_propagates_the_exit_code`: `scripts/ingest.py` exits with whatever
  `main` returned.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_semantic_chunker.py -v`. The discovery
tests need no Ollama and no Qdrant; the exit-code tests drive `main` with an
argument list and assert the return value without reaching the indexing pipeline,
because discovery fails before it.

## Risks and Assumptions

- Assumption: exiting non-zero on an empty match is what an operator wants. It
  changes a previously "successful" run into a failure, which is the point, and
  no automation in this repository depends on the old exit code.
- What would invalidate this spec: a batch mode that walks several roots and
  should tolerate some being empty, which would want a per-root report rather
  than a single exit code.
