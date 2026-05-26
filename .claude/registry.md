# Registro de Projeto — Estado e Histórico

> Este arquivo contém o estado atual e histórico do projeto. É atualizado pelo agente ao final de cada implementação.
> As **regras** sobre como atualizar este registro estão em `.claude/rules/08-registro-projeto.md`.

---

## Informações do Projeto

- **Nome:** SmartB100
- **Stack:** Python 3.12+ (FastAPI, Ollama, Qdrant, Gradio)
- **Repositório:** LukeSantossz/sb100_agents
- **Estrutura:** RAG system — api/, core/, retrieval/, memory/, profiling/, generation/, verification/, database/, eval/

## Histórico de Implementações

> Registro de conclusões. Cada entrada representa uma task finalizada. O agente adiciona uma nova linha após cada task concluída. Nunca remova entradas anteriores.

| # | Data | Task | Complexidade | Escopo Alterado | Resultado | Observações |
|---|------|------|--------------|-----------------|-----------|-------------|
| 1 | 2026-04-24 | TASK-000 | major | 6 arquivos — .claude/hooks/, enforcement.conf | aprovado | Hooks funcionais, .gitignore ajustado |
| 2 | 2026-04-25 | TASK-T18 | minor | 1 arquivo — README.md | aprovado | Documentação MVP completa |
| 3 | 2026-04-24 | TASK-T21 | minor | 4 arquivos — pyproject.toml, ci.yml, README.md, TASK-T21.md | aprovado c/ ressalvas | Ruff, mypy --strict, pytest-cov configurados. CI pode falhar até correção de tipos |
| 4 | 2026-04-24 | TASK-T22 | major | 13 arquivos — core, retrieval, generation, verification, api | aprovado | Docstrings Google Style em todos os módulos públicos |
| 5 | 2026-04-25 | TASK-T24-UI | major | 7 arquivos — ui/, docker-compose.yml, pyproject.toml, requirements.txt | aprovado | Interface Gradio + Docker Compose com profiles infra/app |
| 6 | 2026-04-25 | TASK-T27 | patch | 1 arquivo — ui/chat_ui.py | aprovado c/ ressalvas | Fix formatação ruff. Task retroativa — violação de fluxo documentada |
| 7 | 2026-04-24 | TASK-T23 | major | 0 arquivos — verificação apenas | aprovado | Contratos já tipados; mypy --strict passa em 22 arquivos |
| 8 | 2026-04-25 | TASK-T17 | major | 3 arquivos — .github/workflows/ci.yml, requirements.txt | aprovado | CI com 4 jobs: lint, test, validate-requirements, typecheck |
| 9 | 2026-04-25 | TASK-T24 | major | 4 arquivos — core/config.py, database/models.py, retrieval/vector_store.py, tests/ | aprovado | Auditoria Clean Code + fixes (datetime.UTC, remoção alias) |
| 10 | 2026-04-25 | TASK-T25 | minor | 6 arquivos — SETUP.md, .env.example, core/, retrieval/, database/, tests/ | aprovado | Guia setup local/remoto + suporte QDRANT_API_KEY |
| 11 | 2026-04-25 | TASK-T26 | patch | 2 arquivos — start.bat, start.ps1 | aprovado | Resolução dinâmica Ollama via PATH |
| 12 | 2026-04-25 | TASK-T28 | major | 11 arquivos + 2 removidos — codebase completa | aprovado | Remoção completa de React/npm/Node.js; scripts reescritos para Python puro |
| 13 | 2026-04-25 | TASK-T29 | patch | 2 arquivos — .env.example, docker-compose.yml | aprovado | CHAT_MODEL alinhado para llama3.2:3b |
| 14 | 2026-04-25 | TASK-T30 | patch | 1 arquivo — .env.example | aprovado | COLLECTION_NAME alinhado para archives_v2 |
| 15 | 2026-04-25 | TASK-T31 | minor | 1 arquivo — api/routes/auth.py | aprovado | JWT_SECRET_KEY via settings + validação de erro |
| 16 | 2026-04-25 | TASK-T33 | minor | 1 arquivo — database/db.py | aprovado | os.path substituído por pathlib.Path |
| 17 | 2026-04-25 | TASK-T32 | minor | 3 arquivos — docker-compose.yml, README.md, SETUP.md | aprovado | Ollama removido do Docker, uso local exclusivo documentado |
| 18 | 2026-04-25 | TASK-T34 | patch | 1 arquivo — api/routes/auth.py | aprovado | datetime.utcnow() substituído por datetime.now(UTC) |
| 19 | 2026-04-25 | TASK-T35 | patch | 1 arquivo — README.md | aprovado | Badge coverage corrigido de 80% para 25% |
| 20 | 2026-04-25 | TASK-T36 | minor | 7 arquivos — semantic_entropy/ removido, .gitignore, pyproject.toml | aprovado | Módulo duplicado removido |
| 21 | 2026-04-26 | TASK-T37 | patch | 1 arquivo — database/semantic_chunker.py | aprovado | Emojis Unicode removidos dos prints; prefixos ASCII ([OK], [INFO]) |
| 22 | 2026-04-26 | TASK-T38 | patch | 2 arquivos — archives/smart_boletim.pdf, .gitignore | aprovado | PDF versionado em archives/; entradas removidas do .gitignore |
| 23 | 2026-04-26 | TASK-T39 | minor | 1 arquivo — README.md | aprovado | Getting Started com 7 passos, .env explícito, verificação por etapa |
| 24 | 2026-04-27 | TASK-T40 | minor | 1 arquivo — api/routes/chat.py | aprovado | async def -> def; event loop desbloqueado |
| 25 | 2026-04-27 | TASK-T41 | patch | 1 arquivo — database/db.py | aprovado | parents[2] -> parents[1]; DB na raiz do projeto |
| 26 | 2026-04-27 | TASK-T42 | patch | 1 arquivo — start.bat | aprovado | >nul -> >NUL; evita criação de arquivo literal |
| 27 | 2026-04-27 | TASK-T43 | patch | 1 arquivo — ui/chat_ui.py | aprovado | REQUEST_TIMEOUT 120s -> 300s; LLM local demora ~120s |
| 28 | 2026-04-27 | TASK-T45 | minor | 2 arquivos — verification/entropy.py, core/config.py | aprovado | Verificação migrada de OpenAI para multi-provedor (Groq/Ollama/OpenRouter); embeddings via Ollama local |
| 29 | 2026-04-27 | TASK-T44 | minor | 3 arquivos — ui/chat_ui.py, generation/llm.py, README.md | aprovado | Timeout 600s, TimeoutException separada, num_predict no Ollama |
| 30 | 2026-04-27 | TASK-T46 | patch | 2 arquivos — database/db.py, .gitignore; filesystem smartb100_v2.db | aprovado | Diretório espúrio removido; guard se path for pasta; DB local ignorado no git; bind mount documentado |
| 31 | 2026-04-27 | TASK-T47 | minor | 6 arquivos — retrieval/ollama_embeddings.py (novo), embedder, semantic_chunker, entropy, db.py, tests | aprovado | Retries/backoff + truncagem embeddings; URL SQLite as_posix; reduz 500/tcp reset Ollama no Windows |
| 32 | 2026-04-27 | TASK-T48 | patch | 1 arquivo — retrieval/ollama_embeddings.py | aprovado | Variável tipada resolve mypy no-any-return; CI typecheck desbloqueado |
| 33 | 2026-04-27 | TASK-T49 | major | 22 arquivos — .claude/ reestruturado | aprovado | Migração instructions.md monolítico para rules/ modular + registry.md separado |
| 34 | 2026-04-27 | TASK-T50 | minor | 3 arquivos — CONTRIBUTING.md, LICENSE, README.md | aprovado | Guia contribuição open-source + MIT License + seção Contribuindo no README |
| 35 | 2026-04-27 | TASK-T51 | major | 3 arquivos — .github/workflows/claude-auto.yml, claude-respond.yml, README.md | aprovado | GitHub Actions: auto-implementação de issues (claude-auto label) + resposta interativa (@claude) via anthropics/claude-code-action@v1 |
| 36 | 2026-05-04 | TASK-T52 | patch | 5 arquivos — .claude/rules/ (3 novos) + guia-configuracao-codex.md (novo) + 05-convencoes.md (editado) | aprovado | Sincronização .claude/ com .claude_config/: regras 10-12, guia Codex, parágrafo portfolio em 05. Checklist agêntico: N/A |
| 37 | 2026-05-04 | TASK-T53 | minor | 2 arquivos — README.md (reescrito), ARCHITECTURE.md (removido) | aprovado | README conforme regra 12.2: contexto de negocio, Mermaid embutido, decisoes de engenharia, setup conciso. ARCHITECTURE.md absorvido. Checklist agentico: N/A |
| 38 | 2026-05-04 | TASK-T54 | minor | 3 arquivos — .gitignore, .claude/hooks/pre-commit, CONTRIBUTING.md | aprovado | Hardening preventivo: .env nunca esteve no historico git. Duplicatas removidas do .gitignore, guard no pre-commit hook, secao secrets no CONTRIBUTING.md. Issue #48 fechada. Checklist agentico: aplicado |
| 39 | 2026-05-13 | TASK-T55 | major | 8 arquivos — .claude/ (VERSION, CLAUDE.md, quick-ref.md, rules/00,06,08,10) + raiz (CLAUDE.md removido) | aprovado | Migração framework v1.1.0 → v1.2.0: âncoras always-on (quick-ref), modelo por complexidade, micro-checkpoint, gatilho "desviou". .claude_update e TEMP_MIGRATION_PROMPT.md deletados. |
| 40 | 2026-05-13 | TASK-T56 | major | 7 arquivos + 2 removidos — profiling/, pyproject.toml, core/config.py, .env.example, .gitignore, database/semantic_chunker.py | aprovado | Auditoria: código morto removido, dependências não usadas removidas, configuração sincronizada. |
| 41 | 2026-05-21 | TASK-T57 | patch | 2 arquivos — uv.lock, requirements.txt | aprovado | Follow-up T56: locks regenerados (-950 linhas) sem torch/transformers/sentence-transformers/pypdf e transitivos. pytest 18 ok (cov 24.10%), ruff ok, mypy ok |
| 42 | 2026-05-26 | TASK-T58 | patch | 0 arquivos — issue #59 fechada no GitHub | aprovado | Issue resolvida pela T56 (commit 69cfb0b, PR #64); close via gh CLI com comentário referenciando o estado atual do módulo profiling/ |
| 43 | 2026-05-26 | TASK-T59 | minor | 3 arquivos — pyproject.toml, uv.lock, requirements.txt | aprovado | Bump dependências vulneráveis: idna 3.11→3.16, urllib3 2.6.3→2.7.0, python-multipart 0.0.26→0.0.29, pygments 2.19.2→2.20.0. Resolve 9 alertas Dependabot. pytest 18/18 (cov 24.10%), ruff, mypy ok |
| 44 | 2026-05-26 | TASK-T60 | major | 13 arquivos — auth.py, chat.py, main.py, config.py, dependencies.py (novo), pyproject.toml, uv.lock, requirements.txt, tests/conftest.py (novo), tests/test_auth.py (novo), tests/test_integration.py, README.md, tasks.md | aprovado | bcrypt+JWT gate em /chat + rate-limit slowapi (5/15min token, 3/h register). passlib CryptContext (timing-safe). verify_token busca usuário no DB. JWT_SECRET_KEY ≥32 chars validado em Settings. UserCreate regex + min_length. bcrypt pinado <5 por incompat com passlib 1.7.4. 48 testes (era 18), cobertura 68.32% (era 24.10%). Breaking: hashes SHA-256 antigos obsoletos. |
| 45 | 2026-05-26 | TASK-T61 | minor | 4 arquivos — generation/llm.py, core/schemas.py, tests/test_llm.py, tests/test_schemas.py (novo) | aprovado | Mitigação prompt injection RAG: `_sanitize_context` (delimitador [DOCUMENTO RECUPERADO ...]), `_sanitize_question` (remove [SYSTEM]/[INST]/<<SYS>>/<\|im_*\|>/### System: case-insensitive), aviso anti-injection no system prompt. `ChatRequest.question` min/max 1-2000. 12 novos testes em test_llm + 4 em test_schemas. 64 testes (era 48), cobertura 69.69%. |
| 46 | 2026-05-26 | TASK-T62 | minor | 4 arquivos — core/config.py, core/schemas.py, tests/test_schemas.py, tests/test_config.py (novo) | aprovado | Validações rigorosas: `VerificationProvider(StrEnum)`, `Field(ge/le)` em top_k/buffer_maxlen/llm_max_tokens/hallucination_threshold/entropy_num_samples, API keys `str \| None`, schemas com bounds (session_id, name, hallucination_score). 26 novos testes. 90 testes (era 64), cobertura 70.82%. |
| 47 | 2026-05-26 | TASK-T63 | minor | 4 arquivos — database/models.py, database/db.py, tests/test_db.py (novo), README.md | aprovado | Integridade SQLAlchemy: NOT NULL em campos obrigatórios, index em FKs, ondelete=CASCADE + passive_deletes, Boolean em is_hallucinated, DateTime(timezone=True), connect_args timeout=10, PRAGMA foreign_keys=ON via event listener, get_db rollback-on-exception. 11 novos testes (NULL, CASCADE, tz, rollback). 101 testes, cobertura 70.82%. Breaking: schemas legados ficam frouxos — recriar `smartb100_v2.db`. |
| 48 | 2026-05-26 | TASK-T64 | minor | 4 arquivos — verification/entropy.py, verification/gate.py, core/config.py, tests/test_verification.py (novo) | aprovado | Estabilidade verificação: epsilon 1e-10 em cosseno, logger.warning em missing API key, try/except parcial em samples, resp.get safe access em ollama, validação provider antes de dispatch, gate fallback score=0.5 em falha de entropia, entropy_temperature em Settings (ge=0.0, le=2.0). 13 novos testes. 114 testes, cobertura 81.37%. mypy strict agora limpo em verification/entropy.py (resolve parte da T74). |
| 49 | 2026-05-26 | TASK-T65 | minor | 4 arquivos — api/routes/chat.py, memory/conversation.py, tests/test_conversation.py, tests/test_chat_concurrency.py (novo) | aprovado | Thread-safety: `_sessions_lock = threading.Lock()` envolve cleanup/eviction/lookup em `_get_or_create_buffer`; `del` → `.pop(sid, None)`. `ConversationBuffer.add()` valida role em `{"user", "assistant"}` e content não-vazio (ValueError). 6 novos testes (validação + 3 de concorrência ThreadPoolExecutor 50 threads). 120 testes, cobertura 81.84%. |
| 50 | 2026-05-26 | TASK-T66 | minor | 4 arquivos — retrieval/vector_store.py, retrieval/embedder.py, retrieval/ollama_embeddings.py, tests/test_vector_store.py | aprovado | Singleton QdrantClient com double-checked locking + dim validation (768), logger.warning em payload sem `text`, logger em embedder+ollama_embeddings, `assert` substituído por `raise RuntimeError` defensivo. test_vector_store reescrito em pytest (5 testes incl. singleton reuse). 123 testes, cobertura 82.27%. |
| 51 | 2026-05-26 | TASK-T67 | major | 4 arquivos — api/main.py, generation/llm.py, memory/conversation.py, database/semantic_chunker.py | aprovado | Logging estruturado consolidado: `logging.basicConfig` em `api/main.py` (INFO level + formato com timestamp/logger/level/msg); logger em `generation/llm.py` com info/timing em request e response; logger em memory/conversation; 11 prints em `database/semantic_chunker.py` substituídos por logger.info/warning com extras estruturados; basicConfig no `main()` do chunker CLI. 123 testes, cobertura 82.67%. |
| 52 | 2026-05-26 | TASK-T68 | minor | 5 arquivos — core/config.py, generation/llm.py, verification/entropy.py, tests/test_llm.py, tests/test_verification.py | aprovado | Ollama Client com timeout (`ollama_timeout` settings, default 120s, bounds 1-600); wrapper `_ollama_chat` testável; error handling em `generate` (RequestError/ResponseError/TimeoutError/ConnectionError); singleton thread-safe `_ollama_client`. Cache local de embeddings em `_cluster_responses` reduz embed calls de O(N²) para O(N único). Tests refatorados (7 mocks atualizados + 2 timeouts + 1 cache). 126 testes, cobertura 84.80%. |

## Estado da Codebase

> Atualizado a cada implementação ou verificação pós-pull. Reflete o snapshot mais recente do projeto.

- **Última atualização:** 2026-05-26 (TASK-T68 — Ollama timeout + cache embeddings)
- **Último responsável:** Assistente (sessão local)
- **Branch ativa:** feat/TASK-T68-ollama-timeout-cache
- **Dependências alteradas recentemente:** nenhuma desde T60 — todas em main
- **Testes passando:** sim — 126 passed, cobertura 84.80%; ruff + format + mypy strict em todos críticos ok
- **Divergências externas pendentes:** PRs #74 (T65), #75 (T66), #76 (T67) mergeadas em main; T68 local
- **Última task concluída:** TASK-T68 — Ollama Client com timeout, error handling, cache de embeddings em clustering
- **Backlog ativo:** 6 tasks pendentes (T69 ativa — testes verification ≥50% e mocks robustos; T70–T74 enfileiradas)
- **PRs abertos:** nenhum; PR T68 a abrir após push

## Pendências Conhecidas

- **Docker `api` (profile `app`):** antes de `docker compose --profile app up`, garantir que `./smartb100_v2.db` seja **arquivo** (pode ser vazio), não um diretório; caso contrário o bind mount no Windows costuma criar uma pasta com esse nome e o SQLite falha.

## Decisões Técnicas Relevantes

> Decisões tomadas durante implementações que afetam futuras tasks. Inclua justificativa breve.

- **mypy ignore_missing_imports=true** (T21): Necessário porque ollama, qdrant-client e outras dependências não possuem type stubs. Evita falsos positivos sem comprometer a verificação do código próprio.
- **Embeddings de verificação sempre via Ollama local** (T45): Mesmo quando o provider de geração é Groq ou OpenRouter, os embeddings para clustering de entropia usam Ollama (nomic-embed-text) local. Rápido, gratuito, sem dependência de API externa para embeddings.
- **SQLite e bind mount em Windows** (T46): O volume `.\smartb100_v2.db` no `docker-compose` cria o path no host. Se faltar, o Docker Desktop pode materializar `smartb100_v2.db` como **diretório**; a API trata isso com `RuntimeError` explícita após a correção em `database/db.py`. Mitigação: criar o arquivo (vazio) antes de subir o `api` ou apagar a pasta e recriar o ficheiro.
- **Embeddings Ollama com retries** (T47): `retrieval/ollama_embeddings.embed_text` concentra truncagem (8192 chars) e backoff exponencial para `ResponseError`, `ConnectionError`, erros `httpx` e `OSError`, usado pelo chunker, `generate_embedding` e verificação por entropia.
- **bcrypt pinado `<5` com passlib 1.7.4** (T60): bcrypt 5.0 rejeita senhas mesmo curtas por mudança interna na API, quebrando passlib 1.7.4 (`ValueError: password cannot be longer than 72 bytes` mesmo com input curto). Pin `bcrypt>=4.0.1,<5` resolve até passlib publicar release compatível com bcrypt 5.x. Revisitar quando passlib 1.8+ sair.
- **`verify_token` busca usuário no DB a cada request** (T60): Cada chamada autenticada a `/chat` faz 1 query SQL para confirmar que o usuário ainda existe. Trade-off escolhido: 1 query/req em troca de revogação imediata por delete. Em produção com volume, considerar cache curto (60s) ou rota de blocklist.

## Padrões Recorrentes Observados

| Padrão | Frequência | Impacto | Ação Corretiva |
|--------|------------|---------|----------------|
| Commit sem task registrada | 1x (T27) | Médio — quebra rastreabilidade | Agente deve recusar modificações até task existir. Criar task retroativa se violação ocorrer |
| Commit direto em branch protegida (dev) | 1x (T27) | Médio — pula review | Sempre criar branch dedicada, mesmo para fixes urgentes |
| Modo de operação não declarado | 1x | Baixo — ambiguidade de contexto | Agente deve perguntar modo antes de qualquer ação |
| PR encadeado vira órfão | 1x (T59→PR #67) | **Alto** — commits "mergeados" não chegam em main | **Sempre criar PR com `--base main`**, mesmo se a branch foi feita a partir de outra branch local. GitHub não auto-rebasea a base quando o PR pai mergeia primeiro |

---

## Notas de Sessão

> Espaço para anotações pontuais sobre contextos que influenciam futuras sessões.

- **2026-04-27:** Migração de `.claude/instructions.md` monolítico para estrutura modular em `.claude/rules/` + `registry.md` separado. Dados preservados integralmente.
- **2026-05-26 (T59 recovery):** PR #67 foi aberto com `--base chore/TASK-T58-close-issue-59` esperando auto-rebase para main quando o PR pai (#66) mergeasse. GitHub manteve a base original — o merge do #67 foi para a branch T58 (já mergeada), deixando os 3 commits de T59 órfãos fora de main. Recuperação via PR #68 (base=main, head=chore/TASK-T58-close-issue-59) trazendo os commits órfãos. Padrão registrado para evitar repetição.
