![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react&logoColor=black)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

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
| Hallucination verification | Semantic Entropy + Claim Verification (in development) |

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

## Project Structure
```
sb100_agents/
├── api/
│   ├── main.py                     # FastAPI app entry (CORS + routers + lifespan)
│   └── routes/
│       ├── auth.py                 # POST /auth/register, /auth/token (JWT)
│       ├── chat.py                 # POST /chat (RAG pipeline integrated)
│       └── health.py               # GET /health
├── auth/
│   └── security.py                 # JWT tokens, password hashing, OAuth2
├── core/
│   ├── config.py                   # Pydantic settings (env vars)
│   └── schemas.py                  # Pydantic API contract (ChatRequest, etc.)
├── database/
│   ├── db.py                       # SQLAlchemy engine + session
│   ├── models.py                   # User, Conversation, Message models
│   └── semantic_chunker.py         # PDF ingestion and semantic chunking
├── retrieval/
│   ├── embedder.py                 # Ollama embedding generation
│   └── vector_store.py             # Qdrant context search
├── semantic_entropy/               # Hallucination verifier (in development)
│   ├── compute_entropy.py          # Main entropy pipeline orchestrator
│   ├── response_generator.py       # Multi-response generation
│   ├── shannon_entropy.py          # Entropy calculation
│   └── similarity_clustering.py    # Embedding clustering
├── frontend/
│   └── smartb100/src/
│       ├── components/             # React components (StartScreen, ChatScreen)
│       ├── contexts/               # AuthContext.jsx
│       ├── hooks/                  # useChat.js
│       ├── pages/                  # Dashboard, Login, Register
│       ├── services/               # api.js
│       └── assets/images/          # background.png, logo.png
├── archives/                       # PDF files to be indexed
├── qdrant_storage/                 # Qdrant persistent data
├── ARCHITECTURE.md                 # Architecture diagrams and decisions (Mermaid)
├── docker-compose.yml
├── package.json
├── pyproject.toml
├── start.bat
└── start.ps1
```

## Current Status

**Sprint 1 — active | MVP: functional RAG pipeline**

| Feature | Status |
|---------|--------|
| RAG pipeline (retrieval + generation) | Done |
| FastAPI backend (`POST /chat`, `GET /health`) | Done |
| JWT authentication (`POST /auth/register`, `/auth/token`) | Done |
| SQLite persistence (users, conversations, messages) | Done |
| Semantic chunker with cosine-similarity grouping | Done |
| React frontend (start + chat screens) | Done |
| `ARCHITECTURE.md` with Mermaid diagrams | Done |
| Hybrid search (dense + sparse vectors, RRF fusion) | In progress |
| LangGraph skeleton with agricultural intent filter | In progress |
| Semantic Entropy Pipeline (hallucination verifier) | In progress |
| Claim Verification Pipeline (atomic decomposition + RAG) | In progress |
| Hallucination risk score in API response | Pending |

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
```bash
# Register new user
curl -X POST "http://localhost:8000/auth/register" -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"secret123"}'

# Login (get JWT token)
curl -X POST "http://localhost:8000/auth/token" \
  -d "username=user1&password=secret123"

# Chat (JSON body — contract in core/schemas.py)
curl -X POST "http://localhost:8000/chat" -H "Content-Type: application/json" \
  -d '{"session_id":"demo-session","question":"What should I use to correct soil acidity?","profile":{"name":"User","expertise":"beginner"}}'

# Health check
curl "http://localhost:8000/health"
```

| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Creates new user; returns `{"message", "username"}` |
| `POST /auth/token` | OAuth2 login; returns `{"access_token", "token_type"}` |
| `POST /chat` | Accepts `ChatRequest` body; returns `ChatResponse` (`answer`, `hallucination_score`) |
| `GET /health` | Returns API health status |
