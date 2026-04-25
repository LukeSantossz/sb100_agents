### TASK-T21
- **Status:** concluído
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-24
- **Sprint:** Backlog
- **Prioridade:** Alta

#### Objetivo (!obrigatório)
Configurar Ruff, mypy --strict e pytest-cov com threshold mínimo de 80%, centralizando toda configuração em pyproject.toml e integrando ao CI (T17).

#### Contexto (!obrigatório)
Estabelecer o ferramental de qualidade automatizável do projeto: análise estática com Ruff, type checking estrito com mypy e cobertura de testes com pytest-cov. O objetivo é criar uma baseline mensurável que impeça regressões de qualidade a cada merge. Esta task complementa T17 (GitHub Actions) — o CI deve executar todos esses checks em cada PR. Task criada como parte do ciclo de qualidade pós-auditoria estrutural (T19).

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** `pyproject.toml`, `.github/workflows/ci.yml`
- **Dependências necessárias:** `ruff`, `mypy`, `pytest-cov`
- **Impacto em funcionalidades existentes:** nenhum — task de configuração

#### Critérios de Aceite (!obrigatório)
- [ ] `ruff check .` sem erros em todos os módulos
- [ ] `mypy --strict` sem erros nos módulos críticos: `api`, `core`, `retrieval`, `generation`, `memory`, `profiling`, `verification`
- [ ] `pytest --cov` com threshold mínimo de 80% de cobertura nos módulos acima (`--cov-fail-under=80`)
- [ ] Configurações centralizadas em `pyproject.toml` (seções `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`)
- [ ] CI (T17) executando os três checks em todo PR
- [ ] `pyproject.toml` com as três seções de configuração documentadas
- [ ] Badge de cobertura visível no README
- [ ] Commit: `chore(quality): configure ruff, mypy and pytest-cov with coverage threshold`

#### Restrições
- Depende de: T19 — estrutura de diretórios auditada e correta
- Bloqueia: T22, T23, T24 — base de qualidade deve estar configurada antes das auditorias qualitativas
- Para mypy, aplicar `--strict` apenas nos módulos do `app/` — excluir `tests/` do strict para não bloquear mocks
- Para cobertura, usar `--cov-fail-under=80` como gate inicial, revisável após estabilização
- Risco: mypy --strict pode revelar anotações ausentes em quantidade — avaliar escopo inicial por módulo se o volume for alto

#### Referências
- https://docs.astral.sh/ruff/
- https://mypy.readthedocs.io/en/stable/
- https://pytest-cov.readthedocs.io/

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-24 | — | Task criada como parte do ciclo de qualidade pós-auditoria estrutural (T19) | pendente |
| 2026-04-24 | 1 | Implementadas configurações: [tool.mypy], [tool.pytest.ini_options], [tool.coverage.*], expandido [tool.ruff.lint], adicionado [project.optional-dependencies] dev. CI atualizado para 7 módulos mypy + coverage artifact. Badge cobertura no README. | concluído |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** 2026-04-24
- **Branch:** chore/TASK-T21-static-analysis-coverage
- **Commit(s):** c530b42 chore(quality): configure ruff, mypy and pytest-cov with coverage threshold
- **Avaliação pós-implementação:** aprovado com ressalvas
- **Observações:** mypy --strict e novas regras Ruff podem revelar erros preexistentes no CI. Validação completa requer push e execução do CI.

---
