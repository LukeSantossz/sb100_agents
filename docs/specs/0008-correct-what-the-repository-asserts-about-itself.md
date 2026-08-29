# SPEC: chore: correct what the repository asserts about itself

## Problem

Four places in this repository state something that is not true of it: the
startup scripts are written in Portuguese where the standards require English,
ADR-0009 still reads `Accepted` after ADR-0013 replaced the model choice it
made, `CONTEXT.md` is silent on why runtime user copy is Portuguese so the
question keeps being reopened, and `get_embeddings_batch` says it batches
embeddings "for efficiency" while sending one request per sentence. Executing the
scripts to check the translation then found a fifth: `start.ps1` re-downloads both
Ollama models on every run, because its "is it already installed" test is written
against an array and can never answer no.

## Design Decision

Each assertion is corrected against the rule or the measurement that governs it,
and nothing else changes. The English rule in `code_conventions.md` covers
identifiers, comments, commit and PR text, and documentation, so the startup
scripts are translated in full while the Portuguese strings the agent returns to
end users are left alone and the reading is written down. ADR-0009 gains a
Status line naming its successor, in place, keeping its number and its reasoning.
`get_embeddings_batch` keeps its sequential loop: the three faster shapes were
measured against it on the target host and none of them is faster, so the
docstring is corrected to say what the function does and why the obvious
optimisation was rejected, rather than the function being rewritten to match a
speedup that does not exist.

## Alternatives Considered

- **Implement the batching the docstring promises.** Measured on the target host
  over 96 corpus sentences: sequential 23.58s, a 4-worker thread pool 21.47s, an
  8-worker pool 23.28s, `client.embed` with `batch=16` 20.47s, `batch=64` 25.25s.
  The cost is CPU inference inside Ollama, which serialises regardless of how the
  requests arrive, so the best shape buys about 13 percent and the worst is
  slower than doing nothing. Rejected: real complexity, no real gain.
- **Switch the indexing path to `client.embed`.** It returns L2-normalised
  vectors where `client.embeddings` returns raw ones (measured: norm 1.0000
  against 19.14, cosine 1.00000000). Search is cosine so retrieval would survive,
  but the semantic chunker averages sentence vectors to form chunk vectors, and
  averaging normalised vectors is not the same operation. Rejected: it changes
  indexed content for no measured speed.
- **Translate the agent's Portuguese user-facing strings too.** They are product
  copy for Brazilian readers of a Portuguese corpus, and the English rule lists
  identifiers, comments, commit/PR/issue text and documentation, not runtime
  output. Rejected: it would change what the end user reads to satisfy a rule
  that does not reach it.
- **Delete ADR-0009 now that ADR-0013 supersedes it.** Rejected by
  `spec_method.md`: a durable number is never reused and a superseded record is
  marked in place, because every existing citation of "ADR-0009" must keep
  resolving to the decision that was actually made.

## Scope

- Includes: `start.bat` and `start.ps1` translated to English; the `start.ps1`
  model-presence test fixed so an installed model is not re-pulled; `docs/adr/0009-groq-agent-model.md`
  Status updated to name ADR-0013; `CONTEXT.md` gains one line recording that
  runtime user copy is Portuguese by design; the `get_embeddings_batch` docstring
  in `database/semantic_chunker.py` corrected and carrying the measurement.
- Does NOT include: any change to the startup scripts beyond the model-presence
  test named above; any change to the embedding code path; translating the agent's user-facing strings;
  renaming `get_embeddings_batch`; editing any part of ADR-0009 other than its
  Status; raising the CI coverage floor; persisting conversation history.

## Acceptance Criteria

- `startup_scripts_contain_no_portuguese`: neither `start.bat` nor `start.ps1`
  contains a Portuguese comment or message.
- `startup_scripts_still_run`: both scripts still detect Ollama, start the infra
  profile, pull the two models when absent, and launch the API and the web page.
- `installed_models_are_not_re_pulled`: with both models already installed,
  `start.ps1` prints neither "Downloading" line.
- `adr_0009_names_its_successor`: its Status section names ADR-0013, and the rest
  of the file is byte-identical to what was approved.
- `records_gate_stays_green`: `mf check records` passes with no reused number and
  no gap.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`, `ruff check .`,
  `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

The embedding measurement, on Windows 11, Python 3.12.13, Ollama 0.17.7,
`nomic-embed-text`, CPU only, over the first 96 sentences of
`archives/smart_boletim.pdf`: for each shape, embed all 96 and record wall clock.
Timings vary with load on a CPU-only host; the finding that matters is the
ordering, not the absolute seconds, and the ordering was stable.

## Risks and Assumptions

- Assumption: the embedding measurement holds because Ollama serialises inference
  on a CPU-only host. A GPU host, or an Ollama build that runs embedding requests
  concurrently, would change the numbers and reopen the batching question.
- Assumption: the startup scripts are developer tooling, so their echoed messages
  fall under the English rule alongside their comments, while the agent's replies
  do not.
- What would invalidate this spec: a decision that runtime output must also be
  English, which would make the `CONTEXT.md` line wrong.
