# Contributing to SmartB100

Thank you for your interest in contributing! This guide explains how to get involved.

## How to contribute

### 1. Fork and clone

```bash
# Fork via GitHub, then:
git clone --recurse-submodules https://github.com/<your-username>/sb100_agents.git
cd sb100_agents
# already cloned without --recurse-submodules?
git submodule update --init
```

The standards this project binds itself to live in the `.standards` submodule. A
clone without them leaves every gate reading an empty directory.

### 2. Set up the environment

```bash
uv sync
cp .env.example .env
docker compose --profile infra up -d

# Wire the gates in this clone. `core.hooksPath` is local git config: it is not
# committed and no clone inherits it, so a fresh checkout has the hooks and runs
# none of them until this is run.
mf hooks install
mf doctor          # reports what is wired and what is still missing
```

`mf` comes from [my-framework](https://github.com/LukeSantossz/my-framework) —
`go install github.com/LukeSantossz/my-framework/cmd/mf@latest`, or a release
binary on `PATH`. Both hooks fail closed, so the next commit is refused until
`mf` is reachable.

### Handling secrets

- **Never commit `.env`**, `.env.local`, or any file containing real API keys or credentials. These files are in `.gitignore`.
- Copy `.env.example` to `.env` and fill in your own keys. The example file contains only safe placeholders.
- If you accidentally expose a secret in a commit, **revoke the affected keys immediately** in their respective service dashboards (Groq, OpenRouter, etc.) and notify the maintainers.
- For CI/CD pipelines, use [GitHub Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) — never hardcode credentials in workflow files.

### 3. Create a branch

Work is issue-first: open (or claim) a GitHub issue before branching. Branches follow
the `type/NNN-short-description` convention, where `NNN` is the issue number:

```bash
git checkout -b feat/130-persist-conversation-history
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`

### 4. Pass the Spec Gate (non-trivial changes)

Any change big enough to have a design starts with a spec, per
`.standards/docs/standards/spec_method.md`. The spec passes the Gate only when:

- the Problem is stated in one sentence;
- Scope is filled, including a non-empty "Does NOT include" list;
- at least one Acceptance Criterion exists and is verifiable.

The spec is durable, not ephemeral: it is written as `docs/specs/NNNN-<slug>.md` — the
next free number — and it stays there. `mf check spec` fails a branch that changes
non-exempt paths and adds none, and `mf check records` fails a number that is reused, a
gap in the sequence, or a record that was deleted. A superseded spec is marked in place
and keeps its file. The PR's Spec Link points at the file on the default branch.

Skip the spec only for changes too small to have a design (a typo, a one-line fix).

### 5. Make your changes (test-first)

- Write the test before the implementation: red (watch it fail), green (minimal
  implementation passes), refactor. Each Acceptance Criterion in the spec becomes a test.
- Follow the existing code style (`ruff` enforces lint and formatting)
- Keep changes surgical — touch only what is necessary

### 6. Run tests

```bash
# Test suite (infra-bound tests excluded via the requires_infra marker)
pytest tests/ -m "not requires_infra"

# Lint
ruff check .
ruff format --check .

# Type check
mypy retrieval/ generation/ memory/ --strict
```

### 7. Commit

This project uses **Conventional Commits** — single line, no body, no co-authored-by:

```bash
git commit -m "feat(auth): add password reset endpoint"
```

### 8. Open a Pull Request

- Fill in `.github/PULL_REQUEST_TEMPLATE.md` with real content, including the
  review-layers record. `roles.r2.backends` is a fallback chain, not a panel: the
  runner takes the **first backend that is actually available** and names it, so the
  record is one reviewer plus the ones ahead of it that were skipped, with the
  reason each was skipped. Write down which backend ran R1; which backend ran R2,
  against which Author provider and model, and the cross-provider state it
  resolved to (`verified`, `declared`, `unknown`); which backends it skipped and
  why (quota, authentication, network, not installed); or that R2 did not run at
  all, when no backend in the chain was reachable. R3 is not configured here.

  R2 runs on push via `mf review --role r2`, which prints all of this. Record what
  it actually reported, including a finding you rejected and the reason — never a
  status nobody observed.
- Review your own diff in the Files Changed tab before requesting review (the RA stage
  of `.standards/docs/standards/crura_method.md`).
- Make sure CI passes

## Project conventions

| Item | Rule |
|------|------|
| Commits | `type(scope): subject` — no body, no co-authored-by |
| Branches | `type/NNN-short-description` (NNN = issue number) |
| Spec | Durable `docs/specs/NNNN-<slug>.md` per `.standards/docs/standards/spec_method.md` for non-trivial changes |
| Tests | Test-first (red-green-refactor); required for new features and bug fixes |
| Review | R1 internal + R2 cross-provider on push (`mf review --role r2`) + human CRURA review; each recorded per PR |
| Lint | `ruff check .` must pass with no errors |

## Reporting bugs

Open an [issue](https://github.com/LukeSantossz/sb100_agents/issues) with a clear description, steps to reproduce, and expected vs actual behavior.

## Code of Conduct

When contributing, you are expected to:

- Treat all participants with respect
- Accept constructive criticism
- Focus on what is best for the project
- Show empathy towards other contributors

Unacceptable behavior includes: harassment, offensive language, personal attacks, and publishing private information without consent.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
