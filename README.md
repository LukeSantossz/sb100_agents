# SmartB100 - Agente RAG para Agricultura

Sistema de chat baseado em RAG (Retrieval-Augmented Generation) para consultas sobre agricultura, utilizando documentos PDF como base de conhecimento.

## Requisitos

- **Docker Desktop** (para Qdrant)
- **Ollama** (para modelos LLM)
- **Python 3.12+**
- **Node.js 18+** (para frontend)

## Início Rápido

### Windows
```bash
# Execute o script de inicialização
.\start.bat
# ou
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

### Com npm (após setup inicial)
```bash
npm run start
```

## Passo a Passo Manual

### 1. Iniciar Qdrant (banco de dados vetorial)
```bash
docker-compose up -d
```

### 2. Instalar modelos Ollama

**Windows (via winget):**
```bash
winget install Ollama.Ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 3. Instalar dependências
```bash
# Dependências do projeto raiz
npm install

# Dependências do frontend
npm run install:frontend
```

### 4. Indexar documentos (primeira vez)
```bash
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/
```

### 5. Iniciar tudo junto
```bash
npm run start
```

## URLs dos Serviços

| Serviço | URL |
|---------|-----|
| API | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

## Scripts npm

| Comando | Descrição |
|---------|-----------|
| `npm run start` | Inicia API e Frontend simultaneamente |
| `npm run api` | Inicia apenas a API |
| `npm run frontend` | Inicia apenas o Frontend |
| `npm run setup` | Instala dependências do frontend |
| `npm run docker:up` | Inicia container Qdrant |
| `npm run docker:down` | Para container Qdrant |

## Estrutura do Projeto

```
sb100_agents/
├── agents/
│   └── agent.py              # API FastAPI com RAG
├── database/
│   └── semantic_chunker.py   # Indexação de documentos
├── frontend/
│   └── smartb100/
│       └── src/
│           ├── components/   # Componentes React
│           │   ├── StartScreen.jsx   # Tela inicial
│           │   ├── ChatScreen.jsx    # Tela de chat
│           │   └── index.js          # Exports
│           ├── hooks/        # Custom hooks
│           │   └── useChat.js
│           ├── services/     # Serviços/API
│           │   └── api.js
│           ├── assets/       # Imagens
│           │   └── images/
│           │       ├── background.png
│           │       └── logo.png
│           ├── App.jsx       # Componente principal
│           ├── App.css       # Estilos do app
│           └── index.css     # Estilos globais
├── archives/                 # PDFs para indexação
├── qdrant_storage/           # Dados do Qdrant
├── docker-compose.yml        # Configuração Docker
├── package.json              # Scripts npm raiz
├── pyproject.toml            # Dependências Python
├── start.bat                 # Script Windows CMD
└── start.ps1                 # Script PowerShell
```

## Testar a API

```bash
curl "http://localhost:8000/chat?question=O%20que%20devo%20utilizar%20para%20corrigir%20a%20acidez%20do%20solo?"
```

## Endpoints da API

- `GET /chat?question=<pergunta>` - Faz uma pergunta ao agente
- `GET /health` - Verifica status da API

## Roadmap

Features in development on separate branches:

| Branch | Feature | Status |
|--------|---------|--------|
| `feat/hallucination-audit-method` | **Semantic Entropy Pipeline** - Hallucination detection using Shannon entropy over response clusters | In Progress |
| `feat/audit-and-hybrid-search` | **Architecture Documentation** - System audit with Mermaid diagrams (`ARCHITECTURE.md`) | In Progress |

### Semantic Entropy Pipeline

Uncertainty detection module to identify potential LLM hallucinations:

1. Generate multiple responses for the same query
2. Convert responses to vector embeddings
3. Cluster embeddings by cosine similarity
4. Calculate Shannon entropy over cluster distribution
5. Return risk-based decision

### Planned Improvements

- [ ] Hybrid search (dense + sparse vectors)
- [ ] Response validation loop
- [ ] Hallucination risk scoring in API response
