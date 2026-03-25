![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react&logoColor=black)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

# SmartB100 — Agriculture RAG Agent

> RAG-powered chat system for agriculture consulting, using PDF documents as a knowledge base.

## Overview

SmartB100 is a Retrieval-Augmented Generation (RAG) system that answers agronomy questions by retrieving relevant context from indexed PDF documents and generating responses via a local LLM. It exposes a FastAPI backend and a React frontend, orchestrated through npm scripts with Docker for the vector database.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| LLM inference | Ollama (`llama3.2:3b`) |
| Embeddings | Ollama (`nomic-embed-text`, 768 dims) |
| Vector database | Qdrant (Docker) |
| Document ingestion | PyMuPDF + semantic chunker |
| Frontend | React + Vite |

## Getting Started

### Prerequisites

- **Docker Desktop** (for Qdrant)
- **Ollama** (for LLM inference)
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
├── agents/
│   └── agent.py              # FastAPI app with RAG logic
├── database/
│   └── semantic_chunker.py   # PDF ingestion and semantic chunking
├── frontend/
│   └── smartb100/src/
│       ├── components/        # React components (StartScreen, ChatScreen)
│       ├── hooks/             # useChat.js
│       ├── services/          # api.js
│       └── assets/images/     # background.png, logo.png
├── archives/                  # PDF files to be indexed
├── qdrant_storage/            # Qdrant persistent data
├── docker-compose.yml
├── package.json               # npm scripts (root)
├── pyproject.toml
├── start.bat
└── start.ps1
```

## Current Status

**Status: In development — active**

| Feature | Status |
|---------|--------|
| RAG pipeline (retrieval + generation) | Done ✅ |
| FastAPI backend (`/chat` and `/health`) | Done ✅ |
| Semantic chunker with cosine-similarity grouping | Done ✅ |
| React frontend (start + chat screens) | Done ✅ |
| Hybrid search (dense + sparse vectors) | In progress 🔄 |
| Semantic entropy / hallucination detection | In progress 🔄 |
| Hallucination risk score in API response | Pending ⏳ |

**Active branches:**

| Branch | Feature |
|--------|---------|
| `feat/hallucination-audit-method` | Semantic Entropy Pipeline — detects hallucinations via Shannon entropy over response clusters |
| `feat/audit-and-hybrid-search` | Architecture documentation with Mermaid diagrams (`ARCHITECTURE.md`) |

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
# Ask the agent a question
curl "http://localhost:8000/chat?question=What+should+I+use+to+correct+soil+acidity?"

# Health check
curl "http://localhost:8000/health"
```

| Endpoint | Description |
|----------|-------------|
| `GET /chat?question=<text>` | Queries the RAG agent |
| `GET /health` | Returns API and model status |