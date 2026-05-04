![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-5%2B-orange?logo=gradio&logoColor=white)
![Status](https://img.shields.io/badge/status-MVP%20complete-brightgreen)
![CI](https://github.com/LukeSantossz/sb100_agents/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-25%25-yellow)

# SmartB100 — Agriculture RAG Agent

> RAG-powered chat system for agricultural technical support, with hallucination verification through semantic entropy.

## Why This Exists

Agricultural extension workers and agronomists need quick, reliable answers to technical questions about crop management, soil treatment, pest control, and planting schedules. Traditional search through dense PDF manuals is slow and error-prone.

SmartB100 indexes agricultural PDF documents into a vector database and uses a local LLM to generate answers grounded in the indexed content. The system adapts response complexity to the user's expertise level (beginner, intermediate, expert) and flags potentially hallucinated answers using semantic entropy scoring, so users know when to double-check the information.

## Architecture

```mermaid
flowchart TD
    subgraph CLIENT["Client"]
        GRADIO["Gradio UI\n:7860"]
        CURL["curl / HTTP"]
    end

    subgraph API["API Layer"]
        ENDPOINT["POST /chat"]
        AUTH["POST /auth/*"]
        HEALTH["GET /health"]
    end

    subgraph PIPELINE["RAG Pipeline"]
        EMBED["Embedder\nOllama nomic-embed-text\n768 dims"]
        SEARCH["Vector Search\nCosine Similarity"]
        MEMORY["ConversationBuffer\nFIFO deque (maxlen=10)"]
        PROFILE["Profiling\nbeginner | intermediate | expert"]
        LLM["LLM Generator\nOllama llama3.2:3b"]
    end

    subgraph VERIFY["Verification"]
        ENTROPY["Semantic Entropy\nMulti-provider (Groq/Ollama/OpenRouter)"]
        GATE["Verification Gate\nRetry + Fallback"]
    end

    subgraph DATA["Data Layer"]
        QDRANT[("Qdrant\n:6333\narchives_v2")]
        SQLITE[("SQLite\nusers / conversations")]
    end

    GRADIO -->|HTTP JSON| ENDPOINT
    CURL -->|HTTP JSON| ENDPOINT

    ENDPOINT --> EMBED
    EMBED --> SEARCH
    SEARCH --> QDRANT

    ENDPOINT --> MEMORY
    MEMORY -.->|history| LLM
    SEARCH -->|context| PROFILE
    PROFILE --> LLM

    LLM --> GATE
    GATE -->|verification_enabled| ENTROPY
    ENTROPY -->|score| GATE
    GATE -->|retry if high entropy| LLM

    GATE --> RESPONSE["ChatResponse\n{answer, hallucination_score}"]

    AUTH --> SQLITE
```

**RAG Pipeline Flow:**

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API /chat
    participant E as Embedder
    participant Q as Qdrant
    participant G as LLM Generator
    participant V as Verification Gate

    C->>A: POST /chat {session_id, question, profile}
    A->>E: generate_embedding(question)
    E-->>A: vector[768]
    A->>Q: search_context(vector, top_k=3)
    Q-->>A: chunks[]
    A->>G: generate(question, context, history, profile)
    G-->>A: answer
    alt verification_enabled
        A->>V: evaluate(question, context, answer)
        V-->>A: {answer, hallucination_score}
    end
    A-->>C: ChatResponse {answer, hallucination_score}
```

## Engineering Decisions

| Decision | Rationale |
|----------|-----------|
| **Ollama for all embeddings** | Even when generation uses Groq or OpenRouter, embeddings for entropy clustering use Ollama (`nomic-embed-text`) locally. Free, fast, no external API dependency for embeddings. |
| **Semantic entropy over binary classifiers** | Generates N candidate responses, clusters by semantic similarity, computes Shannon entropy. Higher entropy = less agreement between candidates = higher hallucination risk. Produces a continuous score (0.0-1.0) instead of a binary flag. |
| **Multi-provider verification** | Replaced OpenAI-only verification with Groq/Ollama/OpenRouter dispatch. Removes hard dependency on paid API for hallucination checks. |
| **Ollama embeddings with retries + backoff** | Centralized in `retrieval/ollama_embeddings.py`: truncation at 8192 chars, 6 attempts, exponential backoff up to 60s. Handles `ResponseError`, `ConnectionError`, `httpx` errors, and `OSError`. Used by chunker, embedder, and entropy verification. |
| **SQLite with pathlib + POSIX URLs** | `database/db.py` uses `Path.as_posix()` for SQLite connection strings. On Windows with Docker bind mounts, the host may create `smartb100_v2.db` as a directory instead of a file; the API raises `RuntimeError` with a clear message if this happens. |
| **Sync endpoint for /chat** | `def chat()` instead of `async def chat()`. FastAPI runs sync handlers in a thread pool, which frees the event loop for `/health` and other concurrent requests while the LLM blocks. |
| **mypy `ignore_missing_imports=true`** | Ollama, qdrant-client, and other dependencies lack type stubs. Avoids false positives without compromising type checking on project code. |
| **Profile-aware system prompts** | Three expertise levels (`beginner`, `intermediate`, `expert`) select different system prompts. Same RAG context, different response complexity. No separate models or fine-tuning needed. |

## How to Run

### Prerequisites

- **Docker Desktop** ([download](https://www.docker.com/products/docker-desktop/))
- **Ollama** ([download](https://ollama.ai/download))
- **Python 3.12+** ([download](https://www.python.org/downloads/))

### Setup

```bash
# 1. Pull models
ollama pull llama3.2:3b && ollama pull nomic-embed-text

# 2. Install dependencies
uv sync                            # or: python -m venv .venv && .venv/bin/pip install -e .

# 3. Configure environment
cp .env.example .env               # defaults work for local dev

# 4. Start Qdrant
docker compose --profile infra up -d

# 5. Index documents (first run only)
.venv/bin/python database/semantic_chunker.py index ./archives/

# 6. Start API
.venv/bin/python -m uvicorn api.main:app --reload

# 7. (Optional) Start Gradio UI
.venv/bin/python ui/chat_ui.py
```

Windows users: replace `.venv/bin/python` with `.venv\Scripts\python.exe`, or use `.\start.bat` / `.\start.ps1` after steps 1-3.

Full Docker deployment: `docker compose --profile infra --profile app up -d`

See [`SETUP.md`](./SETUP.md) for remote Qdrant configuration.

### Verify

```bash
curl http://localhost:6333/healthz           # Qdrant: "healthz check passed"
curl http://localhost:8000/health            # API: {"status":"ok"}
```

## API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /chat` | RAG query; returns answer with hallucination score |
| `POST /auth/register` | Creates new user |
| `POST /auth/token` | OAuth2 login; returns JWT |
| `GET /health` | API health status |

**POST /chat:**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "question": "Qual a epoca ideal de plantio da soja?",
    "profile": {"name": "User", "expertise": "beginner"}
  }'
# {"answer": "...", "hallucination_score": 0.18}
```

| Request Field | Type | Description |
|---------------|------|-------------|
| `session_id` | string | UUID for conversation continuity |
| `question` | string | User query |
| `profile.expertise` | enum | `beginner` \| `intermediate` \| `expert` |

| Response Field | Type | Description |
|----------------|------|-------------|
| `answer` | string | Generated response adapted to expertise level |
| `hallucination_score` | float | 0.0 (grounded) to 1.0 (likely hallucinated) |

## Project Structure

```
sb100_agents/
├── api/                            # FastAPI backend
│   ├── main.py                     # App entry (CORS + routers + lifespan)
│   └── routes/                     # chat.py, auth.py, health.py
├── core/                           # Pydantic schemas & configuration
├── retrieval/                      # Embeddings + Qdrant vector search
├── generation/                     # LLM response generation
├── memory/                         # Conversation buffer (FIFO)
├── profiling/                      # User expertise adaptation
├── verification/                   # Semantic entropy + verification gate
├── database/                       # SQLite + PDF semantic chunking
├── eval/                           # 5-step evaluation pipeline
├── ui/                             # Gradio chat interface
├── tests/                          # Unit + integration tests
├── .claude/                        # Agent workflow enforcement
│   ├── rules/                      # Directive files (00-12)
│   ├── guia-configuracao-codex.md  # Codex plugin setup guide
│   ├── registry.md                 # Project state & history
│   ├── tasks.md                    # Task registry
│   └── hooks/                      # Git hooks (commit-msg, pre-commit, etc.)
├── .github/workflows/              # CI + Claude Code automation
├── docker-compose.yml              # Qdrant (infra) + API+Gradio (app)
└── pyproject.toml
```

## Roadmap

| Feature | Description |
|---------|-------------|
| Hybrid search | Dense + sparse vectors with RRF fusion |
| LangGraph migration | ReAct agent with agricultural intent filter |
| Claim Verification | Atomic decomposition + RAG-based fact checking |
| Streaming | SSE for incremental responses |

## Automated Issue Implementation

Issues labeled `claude-auto` are automatically implemented by Claude Code via GitHub Actions. Mention `@claude` in any issue or PR comment for interactive assistance.

Setup: add `ANTHROPIC_API_KEY` secret and create the `claude-auto` label.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Quick summary: fork, branch (`type/TASK-NNN-description`), tests, Conventional Commits, PR.

## License

[MIT License](./LICENSE)
