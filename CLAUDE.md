# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Mandatory Workflow (`.claude/instructions.md`)

**CRITICAL: No code implementation is allowed without following the workflow defined in `.claude/instructions.md`.**

### Pre-Implementation Requirements
All 4 conditions must be met before any code modification:
1. **Task registered** in `.claude/tasks.md` with status, mode, complexity, objective, context, technical scope, and acceptance criteria
2. **Operating mode declared** by user (Development, Review, or Tutor)
3. **Codebase reconnaissance completed** (Section 2 of instructions.md)
4. **Project Registry verified** (Section 9 of instructions.md)

### Operating Modes
- **Development**: Full implementation following all conventions + post-implementation evaluation
- **Review**: Critical code review posture (can start without task, but modifications require task)
- **Tutor**: Mentorship without providing ready code (progressive hints, no solutions)

### Commit Convention (Conventional Commits)
Format: `type(scope): subject` — single line only, no body, no co-authored-by
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`
- Example: `feat(auth): add Google OAuth integration`

### Branch Convention
Format: `type/TASK-NNN-short-description`
- Example: `feat/TASK-001-login-google`, `fix/TASK-012-upload-error`

### Post-Implementation Evaluation (Section 4)
After each implementation, execute:
1. **Conformance check**: All requirements met? Acceptance criteria covered?
2. **Quality check**: Naming conventions, architecture patterns, real error handling, edge cases?
3. **Scope impact check**: Does it affect existing functionality? Duplicate logic? Dependencies compatible?
4. **Report**: Present summary with decision (ready for commit / requires adjustments)

### Project Registry Update (Section 9)
After each successful implementation, update `.claude/instructions.md` Section 9 with:
- Entry in Implementation History
- Current codebase state
- Known pending items
- Technical decisions made

### Active Task
Check `.claude/tasks.md` for the current active task (TASK-000: Implement git hooks for automated enforcement).

---

## Project Overview

SmartB100 is a RAG (Retrieval-Augmented Generation) system for agricultural technical support. It retrieves context from indexed PDF documents and generates expertise-adapted responses via a local LLM (Ollama). The system exposes a FastAPI backend and React frontend.

## Commands

### Development
```bash
# Install dependencies (first time setup)
uv sync                          # Python (recommended)
npm install && npm run setup     # Node + frontend

# Start everything (API + Frontend)
npm run start

# Start components individually
npm run api                      # FastAPI on :8000
npm run frontend                 # React/Vite on :5173
npm run docker:up                # Qdrant on :6333

# Index PDFs (required before first chat)
.venv\Scripts\python.exe database\semantic_chunker.py index ./archives/
```

### Testing
```bash
# Run unit tests (excludes integration tests)
pytest tests/ -v --ignore=tests/test_integration.py

# Run single test file
pytest tests/test_conversation.py -v

# Run integration tests (requires mocks, no external services)
pytest tests/test_integration.py -v
```

### Linting
```bash
ruff check .                     # Lint
ruff format .                    # Format
ruff check --fix .               # Auto-fix
```

### Evaluation Pipeline
The eval/ directory contains a 5-step pipeline for measuring RAG quality:
```bash
python eval/generate_questions.py ./archives/doc.pdf --num-questions 300
python eval/collect_references.py
python eval/run_evaluation.py    # Requires API running
python eval/judge.py
python eval/report.py
```

## Architecture

**Eight modular layers:**

| Layer | Purpose |
|-------|---------|
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

## Configuration

Environment variables via `.env`:
- `CHAT_MODEL`: LLM model (default: llama3.2:3b)
- `EMBED_MODEL`: Embedding model (default: nomic-embed-text)
- `QDRANT_URL`: Vector DB URL (default: http://localhost:6333)
- `COLLECTION_NAME`: Qdrant collection (default: archives_v2)
- `VERIFICATION_ENABLED`: Enable hallucination check (true/false)
- `GROQ_API_KEY`, `OPENROUTER_API_KEY`: For eval pipeline

## Testing Notes

- Unit tests mock external services (Ollama, Qdrant)
- Integration tests use FastAPI TestClient with fixtures that mock embedding, context, and generation
- CI runs: `pytest tests/ -v --ignore=tests/test_integration.py`
- Type checking runs on: `retrieval/`, `generation/`, `memory/`

## Naming Convention (VAR Method)

Primary suffixes:
- `Data`: Raw data, payloads, simple attributes (e.g., `userData`, `paymentData`)
- `Info`: Processed data, metadata, config (e.g., `systemInfo`, `accountInfo`)
- `Manager`: Classes orchestrating processes/state (e.g., `SessionManager`)
- `Handler`: Functions reacting to events (e.g., `onClickHandler`)

Extended suffixes: `Service`, `Repository`, `Controller`, `Adapter`, `Mapper`, `Middleware`, `Provider`, `Hook`

## Key Principles (from `.claude/instructions.md`)

1. **Think before coding**: Declare assumptions, expose trade-offs, ask when ambiguous
2. **Simplicity first**: Minimal code, no speculative features, no premature abstractions
3. **Surgical changes**: Touch only what's necessary, follow existing style, don't "improve" adjacent code
4. **Goal-oriented execution**: Transform tasks into verifiable objectives with success criteria

## Integrity Rules

- Never implement without registered task
- Never invent APIs/methods/configurations — verify in official docs
- Never add dependencies without validation
- Never remove/alter code outside task scope
- Never silence errors — handle them usefully
- Always run post-implementation evaluation
- Always update Project Registry after implementation
