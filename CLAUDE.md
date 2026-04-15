# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartB100 is a RAG (Retrieval-Augmented Generation) chat system for agricultural consulting. The system indexes PDF documents, performs semantic search via Qdrant, and generates responses using a local LLM (Ollama).

## Development Commands

```bash
# Start everything (API + Frontend)
npm run start

# Individual services
npm run api          # FastAPI on port 8000 (uvicorn with reload)
npm run frontend     # Vite dev server on port 5173

# Docker (Qdrant vector database)
npm run docker:up    # Start Qdrant on port 6333
npm run docker:down  # Stop Qdrant

# Index PDF documents (run once after adding new PDFs to ./archives/)
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/

# Test search
.venv\Scripts\python.exe database\semantic_chunker.py search "query text"

# Frontend linting
cd frontend/smartb100 && npm run lint
```

### Prerequisites

Before running, ensure:
1. **Ollama** is running with models pulled: `ollama pull llama3.2:3b && ollama pull nomic-embed-text`
2. **Docker** is running (for Qdrant)
3. **Python venv** exists: `uv sync` or `pip install -e .`
4. **Frontend deps** installed: `npm run install:frontend`

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST "http://localhost:8000/chat" -H "Content-Type: application/json" \
  -d '{"session_id":"test","question":"your question","profile":{"name":"User","expertise":"beginner"}}'

# Auth endpoints
curl -X POST "http://localhost:8000/auth/register" -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"secret123"}'

curl -X POST "http://localhost:8000/auth/token" -d "username=user1&password=secret123"
```

## Architecture

```
Frontend (React :5173) → FastAPI (:8000) → Qdrant (:6333)
                              ↓
                         Ollama (local)
```

**RAG Pipeline**: Query → Embed (nomic-embed-text) → Search Qdrant → Build Prompt → LLM (llama3.2:3b) → Response

### Key Entry Points

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app: CORS, routers, DB lifespan |
| `api/routes/chat.py` | `POST /chat` - main RAG endpoint |
| `api/routes/auth.py` | JWT authentication (register, token) |
| `core/schemas.py` | Pydantic models: `ChatRequest`, `ChatResponse`, `UserProfile` |
| `retrieval/embedder.py` | Ollama embedding generation |
| `retrieval/vector_store.py` | Qdrant context search |
| `database/semantic_chunker.py` | PDF ingestion CLI |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/smartb100/src/hooks/useChat.js` | Chat state management |
| `frontend/smartb100/src/services/api.js` | HTTP client (via Vite proxy `/api` → `:8000`) |
| `frontend/smartb100/src/contexts/AuthContext.jsx` | JWT auth context |

## Code Patterns

- **Backend**: Simple functions, no classes. Use Pydantic for validation.
- **Frontend**: Custom hooks for state (`useChat.js`), React Context for auth.
- **API Contract**: All request/response models in `core/schemas.py`.
- **Expertise levels**: `beginner`, `intermediate`, `expert` - affects response complexity.

## Configuration

Copy `.env.example` to `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAT_MODEL` | `llama3.2:3b` | Ollama model for generation |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings (768-dim) |
| `QDRANT_URL` | `http://localhost:6333` | Vector database URL |
| `COLLECTION_NAME` | `archives_v2` | Qdrant collection name |
| `TOP_K` | `3` | Number of context chunks to retrieve |
| `JWT_SECRET_KEY` | (required for auth) | Secret for JWT signing |

## Semantic Chunking Configuration

In `database/semantic_chunker.py`:

```python
SIMILARITY_THRESHOLD = 0.75   # Below = new chunk
MIN_CHUNK_SENTENCES  = 3
MAX_CHUNK_SENTENCES  = 20
EMBED_DIM           = 768     # nomic-embed-text dimension
```

Chunks are created by grouping consecutive sentences with cosine similarity ≥ 0.75.

## Service URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| Ollama | http://localhost:11434 |

## References

- `ARCHITECTURE.md` - Detailed diagrams, MVP target architecture, and design decisions
- `README.md` - Setup instructions and project status
