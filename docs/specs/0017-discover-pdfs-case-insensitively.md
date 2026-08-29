# SPEC: fix(ingest): discover PDFs case-insensitively and assert the documented exit codes

## Problem

`discover_pdfs` accepts `REPORT.PDF` when it is passed directly but skips it
inside a directory, because the file branch lowercases the suffix while the
directory branch globs the case-sensitive pattern `**/*.pdf`; on Linux the same
file is indexed or ignored depending on how it was named on the command line.

## Scope

- Includes: the directory branch matching any case of the extension; the exit
  codes in `tests/test_semantic_chunker.py` asserted exactly rather than as
  non-zero.
- Does NOT include: matching other document formats, following symlinks, or any
  change to `process_folder`, `main` or the wrapper.

## Acceptance Criteria

- `an_uppercase_extension_is_found_in_a_directory`: a directory containing
  `REPORT.PDF` yields it, and so does a mixed-case `Report.Pdf`.
- `the_two_branches_agree`: for the same file, passing its path directly and
  passing its parent directory both yield it.
- `no_duplicates_from_a_case_insensitive_filesystem`: on a filesystem where
  `*.pdf` and `*.PDF` match the same entry, the file appears once.
- `the_documented_exit_codes_are_asserted`: the tests assert `1` for a path with
  no PDF and `2` for no subcommand, not merely a non-zero value.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.
