# Modular monolith over microservices

SmartB100's RAG pipeline (embed → search → generate → verify) runs synchronously within a
single request and shares one `ChatRequest`/`ChatResponse` model. We run every domain module
in one FastAPI process, communicating by in-process function calls; the folder boundaries are
a convention for testability and review, not a network boundary.

## Status

Accepted.

## Considered Options

- **Modular monolith (chosen)**: one process, in-process function calls, folder-as-module
  convention.
- **Microservice per RAG step** (embed / search / generate / verify as separate services).
  Rejected — turns in-process calls into network hops and adds contract-versioning overhead
  with no independent-scaling benefit at current load.

## Consequences

- Inter-module communication stays a function call; no RPC, message broker, or queue.
- The folder structure carries no deployment meaning; reviewers read it as logical layering.
- The Verification Gate is the natural extraction point if entropy sampling must scale
  independently (beyond roughly 500 req/s); it already exposes a clean
  `evaluate(question, context, answer)` seam.
