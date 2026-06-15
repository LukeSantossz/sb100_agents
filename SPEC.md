# SPEC: fix(eval): make the evaluation checkpoint reflect only successful, dataset-bound results and survive aborts

Resolves #94, #103, and #107 — three facets of one checkpoint-lifecycle contract in `eval/run_evaluation.py`, so they share one design and PR with per-issue test/fix commit pairs.

## Problem

The checkpoint subsystem corrupts or destroys resume state three ways:
- **#94 (destroyed on abort):** when the `/health` preflight fails on a resume, `run_evaluation_async` returns the loaded checkpoint results (`:195-197`); `run_evaluation` then sees a non-empty list, writes them as the "final" output, and `unlink()`s the checkpoint (`:288-290`) — losing resume state on a transient outage and exiting 0.
- **#103 (failed marked complete):** `completed_ids` is built from every checkpoint record (`:154`), including `sb100_success: False`; on resume those questions are filtered out of `pending` (`:155`) and never retried, so transient failures become permanent.
- **#107 (orphans across datasets):** the checkpoint path is fixed and carries no dataset identity; if the dataset is regenerated, `results = list(existing)` (`:164`) seeds the run with orphan records from a different dataset, contaminating the output metadata and stats.

## Design Decision

Adopt one contract: *the checkpoint holds only successful results for the current dataset, is never destroyed on an abort, and is deleted only when the run is genuinely complete.*

1. **Dataset binding (#107):** compute a stable `dataset_fingerprint` (SHA-256 over the sorted `question_id`s) and store it in the checkpoint payload (`{"dataset_fingerprint": ..., "results": [...]}`). `load_checkpoint` returns its results only when the fingerprint matches the current dataset; on mismatch it logs a warning and starts fresh. Loaded results are additionally filtered to the current dataset's `question_id`s.
2. **Success-only completion + retry (#103):** `completed_ids` counts only `sb100_success == True`. Failed/absent questions go back into `pending`; when reprocessed, the new record **replaces** the old one keyed by `question_id` (dedup, keep latest), so there are never duplicates and no permanent failures.
3. **Abort safety (#94):** the `/health` preflight failure (and any abort) raises a dedicated error that propagates to `main()` as a non-zero exit **without** writing the final output and **without** deleting the checkpoint. The checkpoint is `unlink()`ed only when every dataset question has a successful result (`successful_ids == all question_ids`).

## Alternatives Considered

1. **A `--retry-failures` opt-in flag instead of always retrying (#103).** Rejected as the default: silent permanent failures are the bug; retry must be the default. An opt-*out* flag could be added later but is not needed now.
2. **Encode the dataset fingerprint in the checkpoint *filename* instead of inside the file (#107).** Rejected: it complicates the existing `--checkpoint` argument and leaves stale files around; an in-file fingerprint is self-describing and keeps one known path.
3. **Treat any non-empty result list as "done" and keep current delete behavior (#94).** Rejected: that is the present bug — completion must be defined by coverage of the dataset, not by the list being non-empty.

## Scope

- **Includes:** `dataset_fingerprint` in the checkpoint payload and the load-time match/filter; success-only `completed_ids` with replace-by-`question_id` merge; an abort path that preserves the checkpoint and returns a non-zero exit without writing final output; delete-only-when-fully-successful. Changes confined to `eval/run_evaluation.py` (`load_checkpoint`, `save_checkpoint`, `run_evaluation_async`, `run_evaluation`, `main`).
- **Does NOT include:** authentication of `/chat` (that is #90, though both land in Wave 1); checkpointing for `collect_references.py`/`judge.py` (those are #120 batch items); changing the dataset schema or the results-output schema beyond adding the checkpoint fingerprint; concurrency/semaphore changes.

## Acceptance Criteria

- `checkpoint_stores_dataset_fingerprint` — `save_checkpoint` writes a `dataset_fingerprint` alongside `results`.
- `mismatched_fingerprint_checkpoint_is_ignored` — loading a checkpoint whose fingerprint differs from the current dataset yields zero carried-over results (fresh start).
- `failed_result_is_not_marked_complete` — a checkpoint containing a `sb100_success: False` record leaves that `question_id` in `pending`.
- `retried_question_replaces_failed_record` — after a retry succeeds, the result set has exactly one record for that `question_id` (no duplicate), with the successful payload.
- `health_failure_preserves_checkpoint_and_exits_nonzero` — when `/health` fails on resume, the checkpoint file still exists afterward, no final output file is written, and the process result is non-zero.
- `checkpoint_deleted_only_when_all_successful` — the checkpoint is removed only when every dataset `question_id` has a successful result; a run with any remaining failure keeps it.
- No regression: existing `tests/test_eval.py` continues to pass.

## Reproducibility

- Versions: Python 3.12, httpx 0.28+, on the dev host.
- Unit (no infra): `uv run pytest tests/test_eval.py -v` using temp checkpoint files and a mocked `AsyncClient`/`call_chat_api` to script success/failure and health outcomes — all six criteria are CI-reproducible without Ollama/Qdrant.

## Risks and Assumptions

- Assumption: every question object has a stable `question_id` — confirmed by the dataset schema (`eval/_utils.py:validate_dataset_schema`) and `process_question`. The fingerprint depends on it.
- Assumption: `save_checkpoint` remains atomic (`.tmp` + `replace`) — preserved; only the payload shape changes.
- Risk: an existing checkpoint written before this change lacks `dataset_fingerprint`; `load_checkpoint` must treat a missing fingerprint as a mismatch (ignore and start fresh) rather than crash — covered by `mismatched_fingerprint_checkpoint_is_ignored` generalized to "absent or mismatched".
