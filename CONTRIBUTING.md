# Contribuindo com o SmartB100

Obrigado pelo interesse em contribuir! Este guia explica como participar do desenvolvimento do projeto.

## Como contribuir

### 1. Fork e clone

```bash
# Fork pelo GitHub, depois:
git clone https://github.com/<seu-usuario>/sb100_agents.git
cd sb100_agents
```

### 2. Configure o ambiente

```bash
uv sync
cp .env.example .env
docker compose --profile infra up -d
```

### 3. Crie uma branch

O projeto segue a convenção `type/TASK-NNN-descricao-curta`:

```bash
git checkout -b feat/TASK-NNN-minha-feature
```

Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`

### 4. Faça suas alterações

- Siga as convenções de código do projeto (ver `.claude/rules/05-convencoes.md`)
- Nomenclatura segue o VAR Method (sufixos: Data, Info, Manager, Handler, Service, Repository...)
- Mantenha mudanças cirurgicas — toque apenas no necessario

### 5. Rode os testes

```bash
# Testes unitarios
pytest tests/ -v --ignore=tests/test_integration.py

# Lint
ruff check .
ruff format --check .

# Type check
mypy retrieval/ generation/ memory/ --strict
```

### 6. Commit

O projeto usa **Conventional Commits** — linha unica, sem body, sem co-authored-by:

```bash
git commit -m "feat(auth): add password reset endpoint"
```

### 7. Abra uma Pull Request

- Preencha o template de PR (`.claude/pr-template.md`)
- Descreva o que foi feito e como testar
- Certifique-se de que o CI passa

## Convenções do projeto

| Item | Regra |
|------|-------|
| Commits | `type(scope): subject` — sem body, sem co-authored-by |
| Branches | `type/TASK-NNN-descricao-curta` |
| Nomenclatura | VAR Method |
| Testes | Obrigatorios para novas features e bug fixes |
| Lint | `ruff check .` deve passar sem erros |

Para detalhes completos, consulte os arquivos em `.claude/rules/`.

## Reportando bugs

Abra uma [issue](https://github.com/LukeSantossz/sb100_agents/issues) seguindo o template em `.claude/issue-template.md`.

## Code of Conduct

Ao contribuir, espera-se que voce:

- Trate todos os participantes com respeito
- Aceite critica construtiva
- Foque no que e melhor para o projeto
- Demonstre empatia com outros contribuidores

Comportamento inaceitavel inclui: assedio, linguagem ofensiva, ataques pessoais e publicacao de informacoes privadas sem consentimento.

## Licenca

Ao contribuir, voce concorda que suas contribuicoes serao licenciadas sob a mesma licenca do projeto (MIT).
