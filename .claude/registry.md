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
>
> **Nota (TASK-T75, 2026-05-26):** Entradas #1-#38 foram movidas para `.claude/registry-archive.md` conforme regra 08.5 (histórico ativo cap em ~15 entradas mais recentes). Consultar o arquivo para histórico anterior à TASK-T55.

| # | Data | Task | Complexidade | Escopo Alterado | Resultado | Observações |
|---|------|------|--------------|-----------------|-----------|-------------|
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
| 53 | 2026-05-26 | TASK-T69 | major | 3 arquivos — tests/test_vector_store.py, tests/test_embedder.py, tests/test_integration.py | aprovado | Robustez de testes: `ScoredPoint` real (não MagicMock) em test_vector_store; 3 edge cases em test_embedder (string vazia/longa/Unicode); autouse fixture `_clear_sessions_cache` em test_integration evita leak entre testes. Coverage critério ≥50% alcançado: **84.80%**. Critérios de verification e Ollama already cobertos por T64+T68. 129 testes, cobertura 84.80%. |
| 54 | 2026-05-26 | TASK-T75 | minor | 4 arquivos — .claude/registry-archive.md (novo), .claude/registry.md, retrieval/ollama_embeddings.py, api/routes/chat.py | aprovado | Correções pós-review T60-T69: arquivamento regra 08.5 (entradas #1-#38 → archive; 15 ativas restantes); ollama_embeddings com `Client(timeout=5.0)` + retries reduzidos para 4 (worst-case ~25s, era indeterminado); logger.info `chat.access` + warnings nos paths 503. Padrões Recorrentes ampliados com push sem autorização, arquivamento esquecido e checklist agêntico ausente. 129 testes, cobertura 83.23%. |
| 55 | 2026-05-26 | TASK-T76 | minor | 7 arquivos — core/ollama_clients.py (novo), core/config.py, generation/llm.py, verification/entropy.py, retrieval/ollama_embeddings.py, tests/test_ollama_clients.py (novo), tests/test_verification.py, tests/test_integration.py | aprovado | Consolida 3 padrões de cliente Ollama em módulo único `core/ollama_clients.py` (singletons thread-safe). `settings.ollama_embed_timeout` substitui hardcode. Critério "nenhum `ollama.Client(...)` fora de core" verificado por grep. 7 novos testes (6 cobrindo singletons/timeouts/reset/independência + 1 caplog para chat.access). 136 testes, cobertura 85.87%. Wiki externa consultada (correção comportamental #1 do review T75). |

## Estado da Codebase

> Atualizado a cada implementação ou verificação pós-pull. Reflete o snapshot mais recente do projeto.

- **Última atualização:** 2026-05-26 (TASK-T76 — consolidação de clientes Ollama)
- **Último responsável:** Assistente (sessão local)
- **Branch ativa:** refactor/TASK-T76-ollama-client-consolidation
- **Dependências alteradas recentemente:** nenhuma desde T60 — todas em main
- **Testes passando:** sim — 136 passed, cobertura 85.87%; ruff + format + mypy strict em todos críticos ok
- **Divergências externas pendentes:** PRs #74-#79 mergeadas em main; T76 local
- **Última task concluída:** TASK-T76 — `core/ollama_clients.py` centralizado, 3 consumers consolidados, 7 testes
- **Backlog ativo:** 5 tasks pendentes (T70 ativa — hardening eval pipeline; T71–T74 enfileiradas)
- **PRs abertos:** nenhum; PR T76 a abrir após push (com autorização)

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
| Push/PR sem autorização explícita por task | múltiplas (T61-T69) | Médio — viola regra 06 (ponto de transferência) | Autorização pontual ou autorização durável registrada no início da sessão. Default: pedir antes |
| Arquivamento de registry esquecido | 1x (T60-T69) | Baixo — registry inflado mas operacional | Verificar contagem do histórico no início/fim de sessão; arquivar quando passar de 30 entradas (regra 08.5) |
| Checklist agêntico não-aplicado em PRs | múltiplas (T60-T69) | Médio — perde rastreio de revisão obrigatória | Anexar checklist da regra 06.1 (8 itens estendidos) no corpo de cada PR de código gerado por agente |

---

## Notas de Sessão

> Espaço para anotações pontuais sobre contextos que influenciam futuras sessões.

- **2026-04-27:** Migração de `.claude/instructions.md` monolítico para estrutura modular em `.claude/rules/` + `registry.md` separado. Dados preservados integralmente.
- **2026-05-26 (T59 recovery):** PR #67 foi aberto com `--base chore/TASK-T58-close-issue-59` esperando auto-rebase para main quando o PR pai (#66) mergeasse. GitHub manteve a base original — o merge do #67 foi para a branch T58 (já mergeada), deixando os 3 commits de T59 órfãos fora de main. Recuperação via PR #68 (base=main, head=chore/TASK-T58-close-issue-59) trazendo os commits órfãos. Padrão registrado para evitar repetição.
- **2026-05-26 (review pós-T60-T69):** Review formal da sessão identificou 3 não-conformidades de código (arquivamento, T68 timeout em ollama_embeddings, T60 logging em /chat) e 4 comportamentais (autorização git, wiki externa, checklist agêntico, checkpoints incrementais). Correções de código entram via TASK-T75; comportamentais ficam como diretrizes para próximas sessões e foram registradas como Padrões Recorrentes.
