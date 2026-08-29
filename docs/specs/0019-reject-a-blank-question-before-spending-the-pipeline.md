# SPEC: fix(chat): reject a blank question up front and record a turn atomically

## Problem

`ChatRequest.question` has `min_length=1` and pydantic does not strip, so a
whitespace-only question passes validation, spends the whole embed-search-generate
pipeline, and then fails with a 500 when `ConversationBuffer.add` rejects it; the
two `buffer.add` calls are also unguarded, so an empty answer records a user turn
with no assistant turn beside it.

## Design Decision

Strip and reject at the schema, which is the boundary that already claims the
field is non-empty: a blank question then returns 422 before anything is embedded,
and every downstream consumer receives the stripped value. Recording a turn moves
into one `ConversationBuffer.add_turn` that validates both halves before appending
either, so the buffer cannot end up holding half a conversation. The invariant
belongs to the buffer, not to the caller that happens to write to it.

## Alternatives Considered

- **Catch the `ValueError` around the two `add` calls in the handler.** It stops
  the 500 and leaves both causes in place: the pipeline is still spent on a blank
  question, and a caught exception between the two calls still leaves the orphan
  user turn it was raised to prevent.
- **`str_strip_whitespace=True` on the model config.** It strips every string
  field on the model, including `profile.name` and `session_id`, which is a wider
  behaviour change than the defect asks for and would silently alter session keys.
- **Drop the turn silently when the answer is empty.** It keeps the buffer
  consistent and hides that the generator returned nothing. Logging it and
  skipping the turn is the same outcome with the evidence kept.

## Scope

- Includes: a field validator on `ChatRequest.question`; `add_turn` on
  `ConversationBuffer`; the handler using it; tests for the 422, for atomicity,
  and for the stripped value reaching the pipeline.
- Does NOT include: stripping other fields; changing `min_length`/`max_length`;
  the answer-empty behaviour of the generator itself; persistence.

## Acceptance Criteria

- `a_blank_question_is_rejected_with_422`: `POST /chat` with `"   "` returns 422
  and never calls the embedder.
- `a_question_is_stripped_before_use`: surrounding whitespace is removed from the
  value the pipeline receives.
- `add_turn_appends_both_or_neither`: with an empty assistant answer, the buffer
  gains no user turn either.
- `add_turn_appends_both_on_success`: the ordinary path records the two turns in
  order.
- `an_empty_answer_does_not_fail_the_request`: the response is still returned, and
  the skipped turn is logged.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`,
  `ruff check .`, `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_chat_ui.py tests/test_conversation.py
tests/test_schemas.py -v`, plus the documented request:
`POST /chat {"session_id":"s1","question":"   ", ...}` with a valid token, which
returned 500 after generation and now returns 422 before it.

## Risks and Assumptions

- Assumption: 422 is the right status. FastAPI returns it for request-model
  validation, and moving the check to the schema is what makes the rejection
  happen before the pipeline; the issue asks for 400 "or normalized", and the
  framework's own code for this is 422.
- What would invalidate this spec: accepting a blank question deliberately, for
  example to return the last answer, which nothing does today.
