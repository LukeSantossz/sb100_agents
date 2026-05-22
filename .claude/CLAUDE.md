# CLAUDE.md — Ponto de Entrada do Framework de Desenvolvimento

> **Versão:** 1.2.0 | **Localização das regras:** `.claude/rules/` | **Estado:** `.claude/tasks.md` + `.claude/registry.md` | **Âncoras críticas:** `.claude/quick-ref.md`

---

## Trava de Segurança (Regra 00 — Incondicional)

Nenhuma implementação, modificação, criação ou exclusão de código é permitida sem:

1. **Task registrada** em `.claude/tasks.md`
2. **Modo declarado** pelo usuário (Desenvolvimento, Review ou Tutor)
3. **Codebase reconhecida** (regra 02 executada)
4. **Registry verificado** (`.claude/registry.md` lido)
5. **Micro-checkpoint emitido** antes do tool call (regra 10.2)

Exceções: Modo Tutor e Review podem iniciar sem task, mas qualquer modificação de código exige registro prévio. Detalhes completos: `.claude/rules/00-trava-seguranca.md` e `.claude/rules/10-modelo-e-atencao.md`.

## Princípios Core (Regra 01)

- Pense antes de codar. Declare premissas, exponha trade-offs, pergunte se ambíguo.
- Simplicidade primeiro. Código mínimo, sem features especulativas, sem abstração prematura.
- Mudanças cirúrgicas. Toque apenas o necessário. Limpe apenas a própria sujeira.
- Todo código gerado por agente é rascunho até ser revisado e compreendido pelo desenvolvedor.

## Início de Sessão — O Que Ler

### Sempre (toda sessão):

1. Este arquivo (`CLAUDE.md`)
2. `.claude/quick-ref.md` → âncoras críticas (trava, modelo, checkpoint, "desviou", invioláveis, anti-padrões)
3. `.claude/registry.md` → estado atual, última implementação, pendências
4. `.claude/tasks.md` → **apenas a seção "Tasks Ativas"**, não carregar Tasks Concluídas

### Sob demanda (quando a condição ativar):

| Condição | Ler |
|----------|-----|
| Projeto novo ou primeira sessão | `.claude/prd.md` (se existir) |
| Task `minor` ou `major` | Regras 04 (avaliação) + 06 (CRURA) + 08 (registro) |
| Task `patch` | Apenas regra 05 (convenções) para commit |
| Modo Review ativado | Regra 03 completa (protocolo de review) |
| Modo Tutor ativado | Regra 03 completa (método de dicas progressivas) |
| Publicar no GitHub / curar portfólio | `.claude/guides/guia-portfolio.md` |
| Usar integração Codex | `.claude/guides/guia-codex.md` |
| Setup de hooks ou enforcement | Regra 09 |
| Dúvida sobre nomenclatura ou commits | Regra 05 |
| Dúvida sobre modelo, checkpoint ou gatilho "desviou" | Regra 10 |
| Usuário enviou mensagem contendo "desviou" | Re-ler `quick-ref.md` integralmente e executar protocolo 10.3 |
| Task requer referência a padrões anteriores | Consultar base de conhecimento externa (ver seção abaixo) |

### Regras detalhadas (referência completa):

```
.claude/rules/
├── 00-trava-seguranca.md     ← condições obrigatórias (5 condições)
├── 01-principios.md          ← como pensar e codar
├── 02-reconhecimento.md      ← mapeamento pré-implementação
├── 03-modos-operacao.md      ← desenvolvimento / review / tutor
├── 04-avaliacao-pos.md       ← verificação pós-implementação + testes
├── 05-convencoes.md          ← nomenclatura, commits, branches
├── 06-crura.md               ← fluxo CRURA + checklist unificado
├── 07-integridade.md         ← regras invioláveis
├── 08-registro-projeto.md    ← registry + recuperação de sessão
├── 09-enforcement.md         ← hooks git automatizados
└── 10-modelo-e-atencao.md    ← modelo por complexidade + checkpoint + "desviou"
```

## Recuperação de Sessão

Se a sessão anterior foi interrompida (timeout, limite de contexto, crash):

1. Ler `registry.md` → última implementação e estado registrado
2. Ler `tasks.md` → task ativa e último Log de Andamento
3. Verificar branch atual (`git branch --show-current`) e último commit (`git log -1 --oneline`)
4. Comparar estado real vs registrado. Reportar divergências ao usuário.
5. Retomar do ponto documentado no Log de Andamento.

---

## Informações do Projeto

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

## Base de Conhecimento Externa

Caminho: C:\Users\lucas\OneDrive\Desktop\llm-wiki\wiki\
Índice: wiki/index.md

**Regras de uso:**
- APENAS CONSULTA — não modificar, criar ou atualizar arquivos nesta pasta
- Consultar antes de: decidir stack, investigar bugs recorrentes, tomar decisões arquiteturais
- O índice `index.md` é o ponto de entrada para navegação

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
