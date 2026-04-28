# SmartB100 — Diretrizes para Agentes de IA

> **Este projeto opera sob um fluxo mandatório.** Nenhum agente de IA pode modificar a codebase sem task registrada em `.claude/tasks.md`. Consulte `.claude/rules/` para as regras completas.

## Projeto

- **Nome:** SmartB100
- **Stack:** Python 3.12+ (FastAPI, Ollama, Qdrant, Gradio)
- **Repositório:** LukeSantossz/sb100_agents
- **Estrutura:** RAG system — api/, core/, retrieval/, memory/, profiling/, generation/, verification/, database/, eval/

## Comandos

```bash
# Install dependencies
uv sync

# Start infrastructure (Qdrant via Docker)
docker compose --profile infra up -d

# Index PDFs (required before first chat)
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/

# Start API
.venv\Scripts\python.exe -m uvicorn api.main:app --reload

# Start Gradio UI (optional)
.venv\Scripts\python.exe ui/chat_ui.py

# Startup scripts (Windows)
.\start.bat                      # CMD
.\start.ps1                      # PowerShell

# Tests
pytest tests/ -v --ignore=tests/test_integration.py

# Lint
ruff check .
ruff format .

# Type check
mypy retrieval/ generation/ memory/ --strict

# Evaluation pipeline
python eval/generate_questions.py ./archives/doc.pdf --num-questions 300
python eval/collect_references.py
python eval/run_evaluation.py
python eval/judge.py
python eval/report.py
```

## Estrutura do Sistema de Regras

```
sb100_agents/
├── CLAUDE.md                          <- este arquivo (entrada do projeto)
├── .claude/
│   ├── rules/
│   │   ├── 00-trava-seguranca.md      <- condições obrigatórias de operação
│   │   ├── 01-principios.md           <- pense antes de codar, simplicidade, cirúrgico
│   │   ├── 02-reconhecimento.md       <- inventário técnico pré-implementação
│   │   ├── 03-modos-operacao.md       <- desenvolvimento, review, tutor
│   │   ├── 04-avaliacao-pos.md        <- protocolo pós-implementação
│   │   ├── 05-convencoes.md           <- VAR Method, Conventional Commits, branches
│   │   ├── 06-crura.md               <- fluxo CRURA + checklist + reversão + templates
│   │   ├── 07-integridade.md          <- 12 regras invioláveis
│   │   ├── 08-registro-projeto.md     <- regras de atualização do registry
│   │   └── 09-enforcement.md          <- hooks git automatizados
│   ├── registry.md                    <- estado do projeto + histórico (mutável)
│   ├── tasks.md                       <- registro de tasks (obrigatório)
│   ├── pr-template.md                 <- template de Pull Request
│   ├── issue-template.md              <- template de Issue
│   ├── hooks/                         <- scripts de enforcement git
│   └── enforcement.conf               <- padrões de debug log por linguagem
```

## Fluxo Resumido

1. **Task registrada** em `tasks.md` — obrigatório antes de qualquer código
2. **Modo declarado** (Desenvolvimento / Review / Tutor)
3. **Reconhecimento** da codebase
4. **Implementação** seguindo princípios e convenções
5. **Avaliação pós-implementação** (automática pelo agente)
6. **Atualização** do `registry.md`
7. **CRURA** — Change -> Review -> Upload -> Review Again -> Auto-Revisão

## Convenções Rápidas

- **Commits:** `type(scope): subject` — sem body, sem co-authored-by
- **Branches:** `type/TASK-NNN-descricao-curta`
- **Tasks:** uma por implementação, complexidade obrigatória (patch/minor/major)
- **Nomenclatura:** VAR Method (Data, Info, Manager, Handler, Service, Repository...)

## Arquitetura

**Oito camadas modulares:**

| Camada | Propósito |
|--------|-----------|
| `api/` | FastAPI endpoints (routes/chat.py, routes/auth.py, routes/health.py) |
| `core/` | Pydantic schemas (ChatRequest/Response, UserProfile with ExpertiseLevel) |
| `retrieval/` | Embeddings (Ollama nomic-embed-text) and Qdrant vector search |
| `memory/` | ConversationBuffer - FIFO deque for multi-turn context |
| `profiling/` | User expertise adaptation (beginner/intermediate/expert) |
| `generation/` | LLM response generation with profile-aware system prompts |
| `verification/` | Hallucination detection via semantic entropy |
| `database/` | SQLite (users, conversations) + Qdrant (vectors) |

**RAG Pipeline Flow:**
1. POST /chat receives question + session_id + profile
2. ConversationBuffer retrieves session history
3. Query embedded via nomic-embed-text (768 dims)
4. Qdrant search returns top-k relevant chunks
5. LLM generates response adapted to expertise level
6. Semantic entropy calculates hallucination_score
7. Response + score returned to client

**Key contracts (core/schemas.py):**
- `ExpertiseLevel`: beginner | intermediate | expert
- `ChatRequest`: session_id, question, profile
- `ChatResponse`: answer, hallucination_score (0.0-1.0)

## Configuração

Environment variables via `.env`:
- `CHAT_MODEL`: LLM model (default: llama3.2:3b)
- `EMBED_MODEL`: Embedding model (default: nomic-embed-text)
- `QDRANT_URL`: Vector DB URL (default: http://localhost:6333)
- `COLLECTION_NAME`: Qdrant collection (default: archives_v2)
- `VERIFICATION_ENABLED`: Enable hallucination check (true/false)
- `GROQ_API_KEY`, `OPENROUTER_API_KEY`: For eval pipeline

## Notas de Teste

- Unit tests mock external services (Ollama, Qdrant)
- Integration tests use FastAPI TestClient with fixtures
- CI runs: `pytest tests/ -v --ignore=tests/test_integration.py`
- Type checking runs on: `retrieval/`, `generation/`, `memory/`
