# Registry Archive — Histórico Arquivado

> Arquivo cumulativo de entradas mais antigas do `registry.md`. Mantido para
> rastreabilidade histórica. **Nunca editar entradas já inseridas aqui**.
> Regra de origem: `.claude/rules/08-registro-projeto.md` §8.5 — quando o
> histórico ativo ultrapassa 30 entradas, as mais antigas são movidas para
> este arquivo, mantendo as 15 mais recentes em `registry.md`.

Arquivamento inicial executado em 2026-05-26 (TASK-T75) — entradas #1 a #38
movidas do `registry.md` ativo.

---

## Histórico Arquivado

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
