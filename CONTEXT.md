# SmartB100

The domain language of an agricultural RAG assistant: how a question becomes a
source-grounded answer, adapted to the reader, and scored for how much it can be
trusted. This glossary is the source of truth for what each term means; it holds no
implementation detail. The framework's own process vocabulary — Developer, Author,
Reviewer, SPEC, ADR, CRURA — is defined separately in `.standards/CONTEXT.md`.

## Language

### Retrieval & grounding

**RAG (Retrieval-Augmented Generation)**:
The end-to-end pipeline — embed the question, search the vector store, generate an
answer grounded in the retrieved chunks, then score it. The system's core contract:
answers come from indexed sources, not model memory.
_Avoid_: search, semantic search, lookup (each names one step, not the pipeline).

**Chunk**:
A contiguous slice of a source PDF produced by semantic chunking, embedded and stored
as one Qdrant point with its text payload. The unit of retrieval.
_Avoid_: passage, segment, fragment, document.

**Embedding**:
The 768-dimension vector the `nomic-embed-text` model produces for a chunk or a
question; the space in which similarity is measured.
_Avoid_: vector (unqualified), encoding.

**Context**:
The retrieved chunk texts joined and handed to the Generator as grounding for one
answer. Distinct from conversation history, which is the Conversation Buffer.
_Avoid_: prompt, sources, documents, history.

**Grounded answer**:
An answer derived from the retrieved Context rather than the model's parametric memory.
Ungrounded output is what the Hallucination Score is meant to flag.
_Avoid_: factual, accurate, correct.

**Qdrant collection (`archives_v2`)**:
The vector store holding every chunk embedding (768-dimension, cosine distance); the
single retrieval index.
_Avoid_: database, index (unqualified), table.

### Generation & memory

**Generator**:
The component that builds the profile-aware prompt and calls the local chat model
(`llama3.2:3b` via Ollama) to produce the answer.
_Avoid_: the model, the LLM (unqualified), the AI.

**Expertise Profile**:
The reader's declared level — `beginner`, `intermediate`, or `expert` — that selects
the System Prompt and shapes the answer's depth. The user-facing personalization knob.
_Avoid_: profile (unqualified — collides with Compose profile and User), persona, role,
level.

**System Prompt**:
The per-request instruction block chosen by Expertise Profile and hardened with the
anti-injection notice. Built fresh each request; never stored in the Conversation Buffer.
_Avoid_: instruction, preamble, role prompt.

**Conversation Buffer**:
The per-Session FIFO rolling window (a bounded `deque`) of recent user and assistant
turns passed to the Generator as history. In-memory only; not a persisted record.
_Avoid_: memory (unqualified), history store, cache.

**Session**:
One conversation thread identified by `session_id` and namespaced per User; owns exactly
one Conversation Buffer.
_Avoid_: conversation (reserve for any persisted record), thread, chat.

**Anti-injection**:
The layered defense against prompt injection — sanitizing the question, delimiting the
retrieved Context, and a System Prompt notice — covering both user input and poisoned
documents.
_Avoid_: sanitization (alone), filtering, escaping.

### Verification

**Semantic Entropy**:
The hallucination-scoring method: generate N candidate answers, cluster them by embedding
similarity, and compute normalized Shannon entropy over the clusters. Disagreement between
candidates is the signal. See ADR-0002.
_Avoid_: confidence, uncertainty, perplexity.

**Hallucination Score**:
The continuous `0.0`–`1.0` value Semantic Entropy attaches to every answer — `0.0`
grounded, `1.0` likely hallucinated. The system's headline trust signal.
_Avoid_: confidence score, accuracy, rating.

**Candidate Answer**:
One of the N independently sampled answers Semantic Entropy clusters; never returned to
the User.
_Avoid_: sample (loosely), response, draft, generation.

**Verification Gate**:
The component wrapping generation with scoring: it retries on high entropy and degrades to
the Neutral Score — not a 503 — when verification itself fails.
_Avoid_: validator, checker, filter.

**Provider**:
The backend serving a model for verification sampling — Groq (the default), OpenRouter, or
Ollama (the offline option, no API key required). A SmartB100 runtime concept; distinct from the
framework's model-vendor Provider in `.standards/CONTEXT.md`.
_Avoid_: backend, vendor, service.

**Neutral Score**:
The `0.5` Hallucination Score the Verification Gate returns when the entropy computation cannot
produce one: a provider or runtime failure, and equally a missing API key for the configured
Provider, which raises `MissingVerifierKeyError` and reaches the same degraded path. A declared
degraded path, not an error.
_Avoid_: default score, error score, fallback (reserve for the fallback answer).

**Threshold**:
The Hallucination Score boundary (default `0.5`) at or below which the Verification Gate
accepts an answer.
_Avoid_: cutoff, limit.

### Platform & identity

**Modular monolith**:
The architecture — every domain module loaded into one FastAPI process, communicating by
in-process function calls rather than a network boundary. See ADR-0001.
_Avoid_: microservice, per-module service, monolith (unqualified, implies non-modular).

**Compose profile**:
A Docker Compose activation group — `infra` (Qdrant) or `app` (API + Gradio). Distinct from
Expertise Profile.
_Avoid_: profile (unqualified), environment, stack.

**User**:
The authenticated account (bcrypt-hashed credential, JWT subject) that owns Sessions and
gates `/chat`.
_Avoid_: account, client, profile.

**User copy**:
Text the system shows a reader of the product, as opposed to text it shows a developer. It is
Portuguese here, deliberately: the corpus is a Portuguese agricultural bulletin and the readers
are Brazilian, so the domain-gate refusal and the bounded-run fallback in `agent/` are written
in Portuguese while everything the English rule in `code_conventions.md` names (identifiers,
comments, commit, PR and issue text, documentation) stays English. Operator-facing output, such
as the startup scripts and log messages, is developer text and is English.
_Avoid_: message, string, label (each names the container, not the audience).
