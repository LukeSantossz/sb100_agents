# SmartB100 - RAG Agent for Agriculture

RAG (Retrieval-Augmented Generation) chat system for agricultural queries, using PDF documents as a knowledge base.

## Requirements

- **Docker Desktop** (for Qdrant)
- **Ollama** (for LLM models)
- **Python 3.12+**
- **Node.js 18+** (for frontend)

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

## Manual Step-by-Step

### 1. Start Qdrant (vector database)
```bash
docker-compose up -d
```

### 2. Install Ollama models

**Windows (via winget):**
```bash
winget install Ollama.Ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 3. Install dependencies
```bash
# Root project dependencies
npm install

# Frontend dependencies
npm run install:frontend
```

### 4. Index documents (first time only)
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
| `npm run api` | Starts API only |
| `npm run frontend` | Starts Frontend only |
| `npm run setup` | Installs frontend dependencies |
| `npm run docker:up` | Starts Qdrant container |
| `npm run docker:down` | Stops Qdrant container |

## Project Structure

```
sb100_agents/
├── agents/
│   └── agent.py              # FastAPI API with RAG
├── database/
│   └── semantic_chunker.py   # Document indexing
├── frontend/
│   └── smartb100/
│       └── src/
│           ├── components/   # React components
│           │   ├── ChatInput.jsx
│           │   ├── ChatScreen.jsx
│           │   ├── MessageBubble.jsx
│           │   ├── StartScreen.jsx
│           │   └── index.js
│           ├── hooks/        # Custom hooks
│           │   └── useChat.js
│           ├── services/     # Services/API
│           │   └── api.js
│           ├── assets/       # Images
│           ├── App.jsx       # Main component
│           └── App.css       # Styles
├── archives/                 # PDFs for indexing
├── qdrant_storage/           # Qdrant data
├── docker-compose.yml        # Docker configuration
├── package.json              # Root npm scripts
├── pyproject.toml            # Python dependencies
├── start.bat                 # Windows CMD script
└── start.ps1                 # PowerShell script
```

## Test the API

```bash
curl "http://localhost:8000/chat?question=What+should+I+use+to+correct+soil+acidity?"
```

## API Endpoints

- `GET /chat?question=<question>` - Ask the agent a question
- `GET /health` - Check API status
