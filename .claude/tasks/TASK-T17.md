### TASK-T17
- **Status:** concluída
- **Modo:** desenvolvimento
- **Complexidade:** major
- **Data de criação:** 2026-04-07
- **Sprint:** Sprint 5
- **Prioridade:** Alta

#### Objetivo (!obrigatório)
Configurar pipeline de CI com GitHub Actions: lint via Ruff, type check via mypy e testes unitários do pipeline RAG com mocks, sem dependências externas em tempo de CI.

#### Contexto (!obrigatório)
O repositório `sb100_agents` não possui CI configurado. Por depender do Qdrant como serviço externo, a estratégia de teste em CI exige mocking — os testes devem ser executados sem dependências de infraestrutura real. Inclui type checking estrito com mypy. Gap de CI/CD identificado no CV Camaleão.

Escopo expandido em 2026-04-24:
1. **Consolidação do pipeline.yml:** O arquivo `.github/pipeline.yml` nunca foi executado pois está fora de `.github/workflows/`. Seu conteúdo referencia `frontend/smartb100` que está no `.gitignore`. O arquivo deve ser deletado.
2. **Geração automatizada do requirements.txt:** O `requirements.txt` está defasado em relação ao `pyproject.toml` (faltam pydantic-settings, sqlalchemy, pyjwt, python-multipart, groq, openai, entre outras). Gerar via `uv export --frozen --no-dev -o requirements.txt`. Adicionar step de validação no CI que verifica sincronização com `uv.lock` — se divergirem, pipeline falha.

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** `.github/workflows/ci.yml`, `.github/pipeline.yml` (deletar), `requirements.txt`
- **Dependências necessárias:** ruff, mypy, pytest, unittest.mock (stdlib)
- **Impacto em funcionalidades existentes:** nenhum — infraestrutura de CI nova

#### Critérios de Aceite (!obrigatório)
- [ ] Pipeline verde sem dependências externas em tempo de CI
- [ ] `ruff check` sem erros
- [ ] `mypy` sem erros nos módulos críticos do pipeline (retriever, reranker, validator)
- [ ] Testes de unidade dos três componentes passam com mocks via `unittest.mock`
- [ ] Badge de CI visível no README
- [ ] `.github/pipeline.yml` deletado
- [ ] `requirements.txt` gerado via `uv export --frozen --no-dev -o requirements.txt`
- [ ] Step de validação no CI verifica sincronização `requirements.txt` vs `uv.lock`
- [ ] Commit: `ci: add GitHub Actions workflow with lint, type check and RAG pipeline tests`

#### Restrições
- Trigger: `on: [push, pull_request]` para `main`
- Jobs: (1) lint — `ruff check .`; (2) typecheck — `mypy --strict` sobre módulos do pipeline; (3) test — `pytest tests/unit/` com mocking de QdrantClient via `unittest.mock.patch`
- Estratégia de mock: substituir QdrantClient por MagicMock que retorna resultados sintéticos — nenhuma chamada real ao Qdrant em CI
- Runner: `ubuntu-latest`
- Nenhum teste deve falhar por timeout ou connection error — confirmar que todos usam mocks
- mypy --strict pode revelar anotações ausentes — avaliar aplicação apenas nos módulos críticos

#### Referências
- https://mypy.readthedocs.io/en/stable/
- https://docs.astral.sh/ruff/
- https://docs.python.org/3/library/unittest.mock.html

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-07 | — | Task criada no Backlog | pendente |
| 2026-04-24 | — | Escopo expandido: consolidação pipeline.yml + geração requirements.txt | em andamento |
| 2026-04-24 | TERMINAL-2 | Implementação: deletou pipeline.yml, gerou requirements.txt via uv export, adicionou job validate-requirements no ci.yml | commit feito |
| 2026-04-25 | TERMINAL-2 | Fix: corrigiu validação de requirements.txt usando git diff ao invés de diff de arquivos | pipeline verde |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** 2026-04-25
- **Branch:** ci/TASK-T17-github-actions (merged to dev)
- **Commit(s):** 0e962f2, a533310
- **Avaliação pós-implementação:** aprovado
- **Observações:** Pipeline verde com 4 jobs: lint, test, validate-requirements, typecheck

---
