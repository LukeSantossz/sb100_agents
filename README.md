# SmartB100 — Agriculture RAG Agent

A RAG (Retrieval-Augmented Generation) chat system for agriculture consulting, using PDF documents as a knowledge base.

## Requirements

- **Docker Desktop** (for Qdrant)
- **Ollama** (for LLM inference)
- **Python 3.12+**
- **Node.js 18+** (for the frontend)

## Quick Start

### Windows
```bash
# Run the startup script
.\start.bat
# or
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### With npm (after initial setup)
```bash
npm run start
```

## Manual Setup

### 1. Start Qdrant (vector database)
```bash
docker-compose up -d
```

### 2. Install Ollama models

**Windows (via winget):**
```bash
winget install Ollama.Ollama
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 3. Install dependencies
```bash
# Root project dependencies
npm install

# Frontend dependencies
npm run install:frontend
```

### 4. Index documents (first run only)
```bash
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/
```

### 5. Start everything
```bash
npm run start
```

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

## Project Structure

```
sb100_agents/
├── agents/
│   └── agent.py              # FastAPI app with RAG logic
├── database/
│   └── semantic_chunker.py   # PDF ingestion and semantic chunking
├── frontend/
│   └── smartb100/
│       └── src/
│           ├── components/   # React components
│           │   ├── StartScreen.jsx
│           │   ├── ChatScreen.jsx
│           │   └── index.js
│           ├── hooks/
│           │   └── useChat.js
│           ├── services/
│           │   └── api.js
│           ├── assets/images/
│           │   ├── background.png
│           │   └── logo.png
│           ├── App.jsx
│           ├── App.css
│           └── index.css
├── archives/                 # PDF files to be indexed
├── qdrant_storage/           # Qdrant persistent data
├── docker-compose.yml
├── package.json
├── pyproject.toml
├── start.bat
└── start.ps1
```

## Models in Use

| Role | Model |
|------|-------|
| LLM (chat) | `llama3.2:3b` |
| Embeddings | `nomic-embed-text` (768 dimensions) |

## API Reference

```bash
# Ask the agent a question
curl "http://localhost:8000/chat?question=What+should+I+use+to+correct+soil+acidity?"

# Health check
curl "http://localhost:8000/health"
```

### Endpoints

- `GET /chat?question=<text>` — Queries the RAG agent
- `GET /health` — Returns API and model status

## Roadmap

Features currently in development on separate branches:

| Branch | Feature | Status |
|--------|---------|--------|
| `feat/hallucination-audit-method` | **Semantic Entropy Pipeline** — Hallucination detection using Shannon entropy over response clusters | In Progress |
| `feat/audit-and-hybrid-search` | **Architecture Documentation** — System audit with Mermaid diagrams (`ARCHITECTURE.md`) | In Progress |

### Semantic Entropy Pipeline

Uncertainty detection module to identify potential LLM hallucinations:

1. Generate multiple responses for the same query
2. Convert responses to vector embeddings
3. Cluster embeddings by cosine similarity
4. Calculate Shannon entropy over the cluster distribution
5. Return a risk-based decision

### Planned Improvements

- [ ] Hybrid search (dense + sparse vectors)
- [ ] Response validation loop
- [ ] Hallucination risk score exposed in the API response
