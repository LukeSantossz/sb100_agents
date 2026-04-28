# Contributing to SmartB100

Thank you for your interest in contributing! This guide explains how to get involved.

## How to contribute

### 1. Fork and clone

```bash
# Fork via GitHub, then:
git clone https://github.com/<your-username>/sb100_agents.git
cd sb100_agents
```

### 2. Set up the environment

```bash
uv sync
cp .env.example .env
docker compose --profile infra up -d
```

### 3. Create a branch

This project follows the `type/TASK-NNN-short-description` convention:

```bash
git checkout -b feat/TASK-NNN-my-feature
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`

### 4. Make your changes

- Follow the project code conventions (see `.claude/rules/05-convencoes.md`)
- Naming follows the VAR Method (suffixes: Data, Info, Manager, Handler, Service, Repository...)
- Keep changes surgical — touch only what is necessary

### 5. Run tests

```bash
# Unit tests
pytest tests/ -v --ignore=tests/test_integration.py

# Lint
ruff check .
ruff format --check .

# Type check
mypy retrieval/ generation/ memory/ --strict
```

### 6. Commit

This project uses **Conventional Commits** — single line, no body, no co-authored-by:

```bash
git commit -m "feat(auth): add password reset endpoint"
```

### 7. Open a Pull Request

- Fill in the PR template (`.claude/pr-template.md`)
- Describe what was done and how to test
- Make sure CI passes

## Project conventions

| Item | Rule |
|------|------|
| Commits | `type(scope): subject` — no body, no co-authored-by |
| Branches | `type/TASK-NNN-short-description` |
| Naming | VAR Method |
| Tests | Required for new features and bug fixes |
| Lint | `ruff check .` must pass with no errors |

For full details, see the files in `.claude/rules/`.

## Reporting bugs

Open an [issue](https://github.com/LukeSantossz/sb100_agents/issues) following the template in `.claude/issue-template.md`.

## Code of Conduct

When contributing, you are expected to:

- Treat all participants with respect
- Accept constructive criticism
- Focus on what is best for the project
- Show empathy towards other contributors

Unacceptable behavior includes: harassment, offensive language, personal attacks, and publishing private information without consent.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
