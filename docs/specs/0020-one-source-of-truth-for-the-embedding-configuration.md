# SPEC: fix(retrieval): embed with one configured model, inside the context it accepts

## Problem

The two halves of retrieval disagree about the embedding model and about how much
text it accepts: the indexer embeds with a hardcoded `nomic-embed-text` while every
query path embeds with `settings.embed_model`, so `EMBED_MODEL` moves the query and
not the corpus and leaves the two in different vector spaces (#105); and
`_MAX_EMBED_CHARS` truncates at 8192 characters, which is above what the model
accepts, so the guard runs and the call it protects still fails with `the input
length exceeds the context length` (#225).

## Design Decision

One name and one bound, each held in one place.

The chunker stops owning a model name. `OLLAMA_MODEL` becomes the `--model`
override alone, defaulting to `None`, and `resolve_embed_model()` answers
`OLLAMA_MODEL or settings.embed_model` at call time rather than at import. That is
the same source `retrieval/embedder.py` reads, so `EMBED_MODEL` now moves both
sides together, which is what makes the setting mean what the README says it means.
Resolving per call, not per import, also means a caller that changes the setting is
obeyed without reloading the module.

Making `EMBED_MODEL` reach the indexer makes a model of another dimension reachable
for the first time, so `process_folder` probes the model once before creating the
collection and fails with a message naming the model, both dimensions, and the
setting that chose it. Without the probe such a run embeds every sentence of every
PDF and then fails at the Qdrant upsert with a vector-shape error that names none
of them.

Matching the dimension is not the same as matching the model: two 768-dimension
models produce two incompatible spaces of the same shape, and `init_qdrant` keeps
an existing collection while `upsert_chunks` writes fresh UUIDs, so a second model's
vectors would simply be appended to the first model's corpus. Each point is
therefore stamped with the model that embedded it, and the run refuses a collection
whose stamp names another model. A collection written before the stamp existed
carries none; an absent stamp cannot demonstrate a mismatch, so it is logged and
allowed rather than breaking every install that predates this.

`_MAX_EMBED_CHARS` drops to a measured value below the ceiling rather than a round
number above it. Counting tokens properly would mean carrying the tokenizer as a
dependency for one bound, which is not proportionate here; a character limit set
below the worst density measured on this corpus buys the same protection for a
constant.

## Alternatives Considered

- **Read `settings.embed_model` into `OLLAMA_MODEL` at import.** One line, and it
  fixes the shipped defect. It also freezes the value at import time, so the
  argparse default and every test would need a module reload to change it, and the
  global would still be two things at once: a default and an override.
- **Derive `EMBED_DIM` from the model instead of probing against it.** A different
  model would then index without complaint, and the query side would still refuse
  it: `retrieval/vector_store._EMBEDDING_DIM` is 768 and the shipped collection
  holds 768 vectors. Deriving the dimension would build a corpus nothing can read.
- **Count tokens with the real tokenizer for the truncation.** Correct, and it
  costs a model-specific dependency plus a load at import to bound one call. The
  measured character limit is a worse instrument for a much lower price.
- **A collection name per model instead of a stamp.** It isolates the spaces without
  any check, and it silently doubles the corpus on disk and leaves `COLLECTION_NAME`
  meaning two things, one of which `retrieval/vector_store` does not know about.
  Refusing is the behaviour the operator can act on.
- **Scan every point for its model rather than sampling one.** It is the only way to
  prove a collection is not already mixed, and it costs a full scroll of the
  collection on every run to defend against a state this change is what prevents.
  Sampling catches the case worth catching and the docstring says which case it does
  not.
- **Leave `_MAX_EMBED_CHARS` at 8192 and catch the failure.** The retry loop
  already catches it and retries four times, spending the whole budget on an input
  that cannot succeed. Truncating below the limit is the fix; catching it is the
  symptom being handled again.

## Scope

- Includes: `resolve_embed_model()`, the dimension probe and the collection-model
  guard in `database/semantic_chunker.py`; the `embed_model` payload stamp; the
  `--model` default; the lowered `_MAX_EMBED_CHARS`; the `.env.example` note that
  changing `EMBED_MODEL` now means re-indexing; tests for all of it.
- Does NOT include: making `EMBED_DIM` or the collection name configurable;
  changing how the query path embeds; re-indexing the shipped corpus, which is
  unnecessary because the default model does not change; de-duplicating chunks when
  the same PDF is indexed twice, which is #128 and predates this; a truncation limit
  derived per model rather than measured for the default one; the eight `database/`
  type errors (#227); task prefixes (#106).

## Acceptance Criteria

- `the_indexer_embeds_with_the_configured_model`: with `settings.embed_model`
  changed, `get_embedding` asks Ollama for that model.
- `the_indexer_and_the_query_path_agree`: both sides request the same model name.
- `the_cli_override_still_wins`: `--model` remains authoritative over the setting.
- `a_model_of_the_wrong_shape_fails_before_indexing`: the probe raises
  `EmbeddingDimensionError` naming the model and both dimensions.
- `the_expected_shape_passes_the_probe`: a 768-dimension model indexes as before.
- `a_collection_built_by_another_model_is_refused`: a stamp naming another model
  raises `EmbeddingModelMismatchError` naming both models.
- `the_same_model_may_add_to_its_own_collection`: the ordinary re-index still runs.
- `a_collection_predating_the_stamp_is_allowed`: no stamp is not a mismatch.
- `a_collection_that_does_not_exist_yet_is_allowed`: a first run is not blocked.
- `indexed_points_record_the_model_that_embedded_them`: the stamp the guard reads is
  actually written.
- `the_truncation_limit_is_below_the_measured_ceiling`: `_MAX_EMBED_CHARS` is at or
  under the worst ceiling measured.
- `a_long_text_is_truncated_to_the_limit`: the prompt reaching Ollama is exactly
  `_MAX_EMBED_CHARS` long.
- `the_limit_still_admits_a_chat_question`: the limit stays above the 2000-character
  cap `ChatRequest.question` enforces, so nothing the API accepts gets truncated.
- `full_suite_stays_green`: `pytest tests/ -m "not requires_infra"`, `ruff check .`,
  `ruff format --check .` and the CI mypy invocation all pass.

## Reproducibility

`uv run --extra dev pytest tests/test_embedding_config.py -v`.

The ceiling was measured against the live model, not assumed: a binary search for
the largest accepted prefix of each of the five longest chunks in the shipped
collection, plus two synthetic samples chosen to bracket the density.

| sample | chars | largest accepted | chars per token |
| --- | --- | --- | --- |
| corpus_0 | 7048 | 7048 (whole) | >= 3.44 |
| corpus_1 | 6609 | 6609 (whole) | >= 3.23 |
| **corpus_2** | 6585 | **6203** | **3.03** |
| corpus_3 | 6265 | 6265 (whole) | >= 3.06 |
| corpus_4 | 5692 | 5692 (whole) | >= 2.78 |
| repeated accented Portuguese | 21600 | 9207 | 4.50 |
| repeated ASCII English | 22000 | 10004 | 4.88 |

Only corpus_2 and the two synthetic samples were refused at all; the other four
were accepted whole, so their rows are lower bounds rather than ceilings. The worst
real ceiling is therefore **6203 characters**, and `_MAX_EMBED_CHARS = 4000` sits a
third below it.

The synthetic samples were built expecting them to be the dense case and they were
the opposite: repeated text compresses well under a BPE tokenizer, so both accepted
more characters than any real chunk. Natural prose is the dense case here, which is
why the limit is set from the corpus and not from a constructed worst case.

## Risks and Assumptions

- Assumption: 4000 has margin against text denser than anything in this corpus. It
  is 1.95 characters per token against a measured worst case of 3.03, so a text
  would have to tokenise about a third worse than the densest chunk here to break
  it. Ollama answers 500 rather than truncating, so being wrong in the generous
  direction costs a failed request and being wrong in the strict direction costs
  characters of a text nothing currently embeds.
- Assumption: the ceiling is a property of the model and the text, not of the host.
  It was measured on one machine against one Ollama build. A different quantisation
  or context setting would move it, which is why the number is recorded next to the
  constant rather than left implicit.
- Assumption: no shipped path embeds text long enough for the lower limit to change
  a stored vector. The chunker embeds sentences, `ChatRequest.question` is capped at
  2000 characters, and the agent's `search_corpus` embeds a query it wrote. A test
  pins the 2000-character half of that.
- Known limit, stated rather than hidden: the collection guard samples one point, so
  it cannot detect a collection that is already mixed. Nothing shipped could have
  produced one, because until this change `EMBED_MODEL` did not reach the indexer at
  all.
- Known limit: `_MAX_EMBED_CHARS` is one number for every model, measured against
  `nomic-embed-text`. A model with a smaller context could still refuse a truncated
  input. This is strictly better than the 8192 it replaces and the per-model version
  is filed separately.
- What would invalidate this spec: embedding whole chunks or whole documents, which
  #106 would do if it is ever implemented. That change has to re-measure the ceiling
  for the text it actually sends, prefix included.
