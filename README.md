![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react&logoColor=black)
![Status](https://img.shields.io/badge/status-MVP%20complete-brightgreen)
![CI](https://github.com/LukeSantossz/sb100_agents/actions/workflows/ci.yml/badge.svg)

# SmartB100 — Agriculture RAG Agent

> RAG-powered chat system for agricultural technical support, with agent-oriented architecture via LangGraph and hallucination verification through semantic entropy.

## Overview

SmartB100 is a Retrieval-Augmented Generation (RAG) system specialized in agronomy. It answers technical agricultural questions by retrieving relevant context from indexed PDF documents and generating responses via a local LLM. It exposes a FastAPI backend and a React frontend, orchestrated through npm scripts with Docker for the vector database.

The evolving architecture targets migration to a ReAct graph with LangGraph, hybrid search (dense + sparse vectors with RRF fusion), and a dual-pipeline hallucination verifier — semantic entropy and atomic claim verification.

For architecture details and design decisions, see [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI + Uvicorn |
| LLM inference | Ollama (`llama3.2:3b`) |
| Embeddings | Ollama (`nomic-embed-text`, 768 dims) |
| Vector database | Qdrant (Docker) |
| Document ingestion | PyMuPDF + semantic chunker |
| Frontend | React + Vite |
| Agent orchestration | LangGraph (migration in progress) |
| Conversation memory | FIFO rolling window buffer |
| Hallucination verification | Semantic Entropy + Claim Verification (in development) |
| Eval providers | Groq, OpenRouter (Gemma 4) |

## Getting Started

### Prerequisites

- **Docker Desktop** (for Qdrant)
- **Ollama** (for local LLM inference)
- **Python 3.12+**
- **Node.js 18+**

### Installation
```bash
# Install Ollama models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Create Python virtual environment (choose one)
uv sync                # if using uv (recommended)
# or
python -m venv .venv && .venv\Scripts\pip install -e .  # Windows
python -m venv .venv && .venv/bin/pip install -e .      # Linux/Mac

# Install root and frontend dependencies
npm install
npm run install:frontend
```

### Running

**Windows (one-shot script):**
```bash
.\start.bat
# or
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

**Manual (step by step):**
```bash
# 1. Start the vector database
docker-compose up -d

# 2. Index PDF documents (first run only)
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/

# 3. Start API + Frontend
npm run start
```

## Architecture

SmartB100 follows a modular 8-layer architecture:

| Layer | Purpose |
|-------|---------|
| `api/` | FastAPI endpoints (chat, auth, health) |
| `core/` | Pydantic schemas (`ChatRequest`, `ChatResponse`, `ExpertiseLevel`) |
| `retrieval/` | Embeddings (Ollama `nomic-embed-text`) + Qdrant vector search |
| `generation/` | LLM response generation with profile-aware system prompts |
| `memory/` | `ConversationBuffer` — FIFO rolling window (maxlen=10) |
| `profiling/` | User expertise adaptation (beginner / intermediate / expert) |
| `verification/` | Hallucination detection via semantic entropy |
| `database/` | SQLite (users, conversations) + Qdrant (vectors) + PDF ingestion |

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for detailed diagrams and design decisions.

## Project Structure
```
sb100_agents/
├── api/                            # FastAPI backend
│   ├── main.py                     # App entry (CORS + routers + lifespan)
│   └── routes/
│       ├── auth.py                 # POST /auth/register, /auth/token
│       ├── chat.py                 # POST /chat (RAG pipeline)
│       └── health.py               # GET /health
├── core/                           # Pydantic schemas & configuration
│   ├── config.py                   # Settings (env vars)
│   └── schemas.py                  # ChatRequest, ChatResponse, UserProfile
├── database/                       # SQLite + PDF ingestion
│   ├── db.py                       # SQLAlchemy engine + session
│   ├── models.py                   # User, Conversation, Message ORM
│   └── semantic_chunker.py         # PDF indexing + semantic chunking
├── eval/                           # 5-step evaluation pipeline
│   ├── dataset/                    # Generated questions and references
│   ├── results/                    # Evaluation outputs
│   ├── generate_questions.py       # PDF → questions
│   ├── collect_references.py       # Reference answers (OpenRouter/Groq)
│   ├── run_evaluation.py           # Executor against /chat endpoint
│   ├── judge.py                    # LLM-as-judge scoring
│   ├── report.py                   # Summary + human samples
│   └── README.md                   # Pipeline documentation
├── generation/                     # LLM response generation
│   └── llm.py                      # Multi-turn with profile-aware prompts
├── memory/                         # Conversation context management
│   └── conversation.py             # ConversationBuffer (FIFO, maxlen=10)
├── profiling/                      # User expertise adaptation
│   ├── intent_filter.py            # Agricultural domain classification
│   └── profile.py                  # Expertise-based response tuning
├── retrieval/                      # Vector search & embeddings
│   ├── embedder.py                 # Ollama embedding (768 dims)
│   └── vector_store.py             # Qdrant context search (top-k=3)
├── ui/                             # Alternative chat interface
│   └── chat_ui.py                  # Gradio chat interface
├── verification/                   # Hallucination detection
│   ├── entropy.py                  # Semantic entropy scoring
│   └── gate.py                     # Retry logic + fallback
├── tests/                          # Unit + integration tests
├── scripts/
│   └── ingest.py                   # PDF ingestion wrapper
├── ARCHITECTURE.md
├── SETUP.md                        # Detailed setup guide (local/remote Qdrant)
├── docker-compose.yml
├── package.json
├── pyproject.toml
├── start.bat
└── start.ps1
```

## Current Status

**MVP Complete** — Core RAG pipeline functional with hallucination verification

| Feature | Status |
|---------|--------|
| RAG pipeline (retrieval + generation) | Done |
| FastAPI backend (`POST /chat`, `GET /health`) | Done |
| JWT authentication (`POST /auth/register`, `/auth/token`) | Done |
| SQLite persistence (users, conversations, messages) | Done |
| Semantic chunker with cosine-similarity grouping | Done |
| React frontend (start + chat screens) | Done |
| `ARCHITECTURE.md` with Mermaid diagrams | Done |
| Evaluation pipeline (`eval/` — 5 steps) | Done |
| Multi-turn conversation memory (FIFO buffer) | Done |
| Profile-aware LLM generation (beginner/intermediate/expert) | Done |
| Session-based conversation isolation | Done |
| Semantic Entropy Pipeline (hallucination verifier) | Done |
| `hallucination_score` in API response | Done |
| Integration tests (end-to-end validation) | Done |
| GitHub Actions CI (lint, type check, tests) | Done |

## Roadmap

| Feature | Description |
|---------|-------------|
| Hybrid search | Dense + sparse vectors with RRF fusion |
| LangGraph migration | ReAct agent with agricultural intent filter |
| Claim Verification | Atomic decomposition + RAG-based fact checking |
| Evaluation dataset | 300 questions from indexed PDFs |

## Service URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

## npm Scripts

| Command | Description |
|---------|-------------|
| `npm run start` | Starts API and Frontend simultaneously |
| `npm run api` | Starts the API only |
| `npm run frontend` | Starts the Frontend only |
| `npm run setup` | Installs frontend dependencies |
| `npm run docker:up` | Starts the Qdrant container |
| `npm run docker:down` | Stops the Qdrant container |

## API Reference

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Creates new user; returns `{"message", "username"}` |
| `POST /auth/token` | OAuth2 login; returns `{"access_token", "token_type"}` |
| `POST /chat` | RAG query; returns answer with hallucination score |
| `GET /health` | Returns API health status |

### POST /chat — RAG Pipeline

**Request (`ChatRequest`):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Qual é a época ideal de plantio da soja na região Centro-Oeste?",
  "profile": {
    "name": "Hilário Silva",
    "expertise": "intermediate"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID for conversation continuity |
| `question` | string | User query |
| `profile.name` | string | User display name |
| `profile.expertise` | enum | `beginner` \| `intermediate` \| `expert` |

**Response (`ChatResponse`):**
```json
{
  "answer": "Com base na documentação indexada, a janela de plantio recomendada para soja na região Centro-Oeste é entre outubro e dezembro...",
  "hallucination_score": 0.18
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Generated response adapted to user expertise |
| `hallucination_score` | float | Risk score 0.0–1.0 (lower = more grounded) |

### curl Examples

```bash
# Register new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"secret123"}'

# Login (get JWT token)
curl -X POST "http://localhost:8000/auth/token" \
  -d "username=user1&password=secret123"

# Chat with complete ChatRequest
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "question": "Qual é a época ideal de plantio da soja?",
    "profile": {"name": "User", "expertise": "beginner"}
  }'

# Health check
curl "http://localhost:8000/health"
```

## Known Issues

- **Evaluation dataset**: Requires PDF documents in `./archives/` to generate the 300-question dataset
- **Ollama dependency**: LLM and embedding models must be pulled before first run
- **Windows paths**: Some scripts assume Windows path separators; cross-platform support is manual
