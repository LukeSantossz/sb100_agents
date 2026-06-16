# Synchronous /chat handler

The RAG pipeline blocks on a synchronous Ollama call. We keep the `/chat` handler a synchronous
`def`, letting FastAPI run it in its threadpool so the event loop stays free for `/health` and
other concurrent requests while a generation is in flight.

## Status

Accepted.

## Considered Options

- **Synchronous handler in the threadpool (chosen)**: FastAPI offloads the blocking call,
  keeping the loop responsive.
- **`async def` handler**. Rejected — would block the event loop on the synchronous Ollama call
  and starve other requests.

## Consequences

- The event loop stays responsive under a slow generation; request concurrency is bounded by the
  threadpool size.
- Per-request state that is shared across threads (for example, per-Session Conversation Buffers)
  must be guarded; the session cache provides that boundary.
