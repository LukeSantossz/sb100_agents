# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartB100 is a RAG (Retrieval-Augmented Generation) chat system for agricultural consulting. This repository (`sb100_agents`) is the production system, while `new_project` (sibling directory) serves as the architectural reference for planned improvements.

### Repository Context

| Repository | Purpose | Status |
|------------|---------|--------|
| `sb100_agents` | Production RAG chat with React frontend | MVP funcional |
| `new_project` | Advanced pipeline with LangGraph/hybrid search | Referência arquitetural |

## Development Commands

### sb100_agents

```bash
# Start everything (API + Frontend)
npm run start

# Individual services
npm run api          # FastAPI on port 8000 (uvicorn with reload)
npm run frontend     # Vite dev server on port 5173

# Docker
npm run docker:up    # Start Qdrant on port 6333
npm run docker:down  # Stop Qdrant

# Index documents
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/

# Search test
.venv\Scripts\python.exe database\semantic_chunker.py search "query text"

# Test API
curl -X POST "http://localhost:8000/chat" -H "Content-Type: application/json" \
  -d '{"session_id":"test","question":"your question","profile":{"name":"User","expertise":"beginner"}}'
curl "http://localhost:8000/health"

# Frontend linting
cd frontend/smartb100 && npm run lint
```

### new_project

```bash
# Start ingest API
cd ../new_project
uvicorn api.main:app --reload

# Run agent
python agent.py

# Ingest PDF
curl -X POST "http://localhost:8000/ingest/pdf" -F "file=@doc.pdf"
```

## Architecture Comparison

### sb100_agents (Current)

```
Frontend (React :5173) → FastAPI (:8000) → Qdrant (:6333)
                              ↓
                         Ollama (local)
```

- **Pipeline**: Linear (Query → Embed → Search → LLM → Response)
- **Search**: Dense only (nomic-embed-text, 768-dim, COSINE)
- **Validation**: None
- **LLM**: Ollama llama3.2:3b (local)

### new_project (Reference Architecture)

```
LangGraph Agent → Tool Call → Hybrid Search → Validation Subgraph
                                   ↓
                         Qdrant (Dense+Sparse+Late)
```

- **Pipeline**: LangGraph with ReAct pattern
- **Search**: Hybrid (MiniLM + BM25 + ColBERT) with RRF fusion
- **Validation**: LLM Judge with max 3 loops + neighbor expansion
- **LLM**: Groq cloud (llama-4-scout-17b)

## Key Files

### sb100_agents

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app entry: CORS, `include_router` for routes |
| `api/routes/chat.py` | `POST /chat` with `ChatRequest` / `ChatResponse` |
| `api/routes/health.py` | `GET /health` |
| `core/schemas.py` | Pydantic contract (`ChatRequest`, `ChatResponse`, `UserProfile`) |
| `database/semantic_chunker.py` | PDF → chunks → Qdrant indexing |
| `frontend/smartb100/src/hooks/useChat.js` | Chat state management |
| `frontend/smartb100/src/services/api.js` | HTTP client |
| `ARCHITECTURE.md` | Full system audit and gap analysis |

### new_project

| File | Purpose |
|------|---------|
| `agent.py` | LangGraph agent with validation subgraph |
| `api/main.py` | Ingest API (`/ingest/pdf`, `/ingest/text`) |
| `api/qdrant_utils.py` | Hybrid search setup (3 vector types) |
| `Codes/chunking_document.py` | Multiple chunking strategies |
| `Codes/document_read.py` | Docling + Gemini VLM extraction |

## Tech Stack Comparison

| Component | sb100_agents | new_project |
|-----------|--------------|-------------|
| Python | 3.12+ | 3.13+ |
| API | FastAPI 0.111.0+ | FastAPI 0.115.6+ |
| PDF | PyMuPDF | Docling + Gemini VLM |
| Embeddings | Ollama nomic-embed-text | FastEmbed (3 models) |
| LLM | Ollama (local) | Groq (cloud) |
| Orchestration | None | LangGraph 1.0.7+ |
| Frontend | React 19 + Vite 7 | None |

## Configuration Reference

### sb100_agents Chunking

```python
SIMILARITY_THRESHOLD = 0.75   # Below = new chunk
MIN_CHUNK_SENTENCES  = 3
MAX_CHUNK_SENTENCES  = 20
EMBED_DIM           = 768     # nomic-embed-text
```

### new_project Chunking

```python
chunk_size    = 256   # RecursiveCharacterTextSplitter
chunk_overlap = 128
# Models: all-MiniLM-L6-v2 (384d) + bm25 (sparse) + colbertv2.0 (late)
```

## Open Architecture Decisions

As decisões arquiteturais ainda estão em aberto. Consulte `ARCHITECTURE.md` para detalhes completos.

### 1. Modelo de Embeddings (Pendente Squad4)

| Opção | Status | Trade-off |
|-------|--------|-----------|
| nomic-embed-text (atual) | Em uso | Local, mas sem sparse |
| FastEmbed (MiniLM+BM25) | Planejado | Híbrido, requer migração |
| ColBERT | Opcional | Precisão vs complexidade |

**Decisão necessária**: Manter Ollama local ou migrar para FastEmbed híbrido?

### 2. LLM Provider (Indefinido)

| Opção | Custo | Qualidade | Latência |
|-------|-------|-----------|----------|
| Ollama local (atual) | $0 | Limitada | Baixa |
| Groq cloud | $$$ | Alta | Baixa |

**Decisão necessária**: Sistema local-first ou cloud-first?

### 3. Orquestração de Agente

| Opção | Complexidade | Benefício |
|-------|--------------|-----------|
| Pipeline linear (atual) | Baixa | Simples, rápido |
| LangGraph + ReAct | Alta | Validação, expansão |

**Decisão necessária**: Quando migrar para LangGraph?

### 4. Busca Híbrida

| Componente | Status |
|------------|--------|
| Dense (COSINE) | Implementado |
| Sparse (BM25) | Pendente |
| Late (ColBERT) | Opcional |
| RRF Fusion | Pendente |

**Decisão necessária**: Implementar BM25 antes ou junto com LangGraph?

## Code Patterns

- Backend: funções simples, sem classes
- Frontend: custom hooks para estado (`useChat.js`)
- Vite proxy: `/api` → `localhost:8000`
- Dependencies: `pyproject.toml` (uv) para Python, `package.json` para Node

## Environment Variables

### sb100_agents
Nenhuma obrigatória (Ollama local).

### new_project
```bash
GOOGLE_API_KEY=<gemini-vision>
GROQ_API_KEY=<llm-provider>
LANGSMITH_API_KEY=<optional-tracing>
```

## References

- `ARCHITECTURE.md` - Auditoria completa do sistema e gap analysis
- `README.md` - Setup e comandos básicos
- `../new_project/agent.py` - Referência de arquitetura LangGraph
- `../new_project/api/qdrant_utils.py` - Referência de busca híbrida
