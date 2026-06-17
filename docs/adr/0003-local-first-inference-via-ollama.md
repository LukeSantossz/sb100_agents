# Local-first inference via Ollama

SmartB100 must run fully offline and free by default. We use Ollama on the host for both
embeddings (`nomic-embed-text`) and chat (`llama3.2:3b`), keeping the embedding space stable
regardless of the generation provider and removing any paid-API dependency from the core
pipeline.

## Status

Accepted.

## Considered Options

- **Local-first via Ollama for embeddings and chat (chosen)**: one local runtime serves both;
  the embedding space never moves when the generation provider changes.
- **Hosted-provider embeddings** (Groq / OpenRouter). Rejected — couples the embedding space to
  a paid provider and to network availability.
- **Larger hosted chat model**. Rejected — reintroduces a paid-API dependency and breaks
  offline operation.

## Consequences

- The core pipeline — embeddings and chat — runs offline and free. Verification can also run
  offline, but only when the Ollama Provider is selected; the default verification Provider is the
  hosted Groq (see ADR-0004).
- CPU inference latency is high (minutes per answer on CPU-only hosts), mitigated by a
  configurable `CHAT_TIMEOUT` and transient-error retries. A GPU or hosted provider removes
  this limitation.
- The embedding dimension is fixed at 768 by `nomic-embed-text`; swapping the embed model
  requires re-indexing and matching the Qdrant collection dimension. See ADR-0004 for how
  generation (not embeddings) is allowed to vary by provider.
