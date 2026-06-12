# SPEC: fix(config): remove working JWT secret from .env.example and SETUP.md

## Problem

The public repository ships a functional 38-character `JWT_SECRET_KEY` in `.env.example` (line 102) and `SETUP.md` (lines 94 and 121); it passes the `_validate_jwt_secret_key` check (`>= 32` chars), so a default `cp .env.example .env` boots an app that signs JWTs with a publicly known key — a complete authentication bypass (OWASP A05:2021).

## Design Decision

Set `JWT_SECRET_KEY` to **empty** in `.env.example` and in both `SETUP.md` copy-paste blocks, each preceded by a one-line instruction to generate a real secret (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). The already-existing validator (`core/config.py:68-76`) rejects an empty value (`if not value: raise ValueError(...)`), so the application now **fails loudly at boot** until the operator provides their own secret. No validator change is needed — the fix is to stop shipping a value that satisfies it. A regression test asserts that the value distributed in `.env.example` does not pass `Settings` validation, so this can never silently regress.

## Alternatives Considered

1. **Replace the value with a non-empty placeholder string** (e.g. `JWT_SECRET_KEY=CHANGE_ME_GENERATE_A_REAL_SECRET`). Rejected: any placeholder long enough to look meaningful is `>= 32` chars and therefore *passes* the validator, re-creating a shared known weak secret — exactly the bug. A placeholder is only safe if it fails validation, which is what "empty" already guarantees unambiguously.
2. **Generate a random secret at install time** (setup script / Makefile target writing a fresh key into `.env`). Rejected: adds tooling and a new install step for a one-line documentation fix; out of scope. The fail-loud validator path forces explicit operator action with zero new code.
3. **Keep a value but document rotation / warn in comments.** Rejected: does not remove the published secret, so the bypass remains exploitable on any default deploy.

## Scope

- **Includes:**
  - `.env.example:102` → `JWT_SECRET_KEY=` (empty), keeping/clarifying the adjacent generation comment.
  - `SETUP.md` lines 94 and 121 (the "Local Mode" and "Remote Mode" blocks) → `JWT_SECRET_KEY=` (empty) with a generation instruction line.
  - A regression test (`tests/test_config.py`) asserting the secret shipped in `.env.example` does not pass `Settings` validation.
- **Does NOT include:**
  - Rotating or invalidating any already-deployed/issued secret or token.
  - Any change to the validator logic in `core/config.py`.
  - The compose `JWT_SECRET_KEY` wiring to containers (that is issue #91).
  - Any other secret/credential in `.env.example` or docs (Groq/OpenRouter/Qdrant keys).

## Acceptance Criteria

- `env_example_jwt_secret_is_empty` — the `JWT_SECRET_KEY=` line in `.env.example` has no value.
- `env_example_jwt_secret_does_not_pass_settings_validation` — feeding the `.env.example` `JWT_SECRET_KEY` value into the `_validate_jwt_secret_key` validator (or constructing `Settings` with it) raises `ValidationError` / `ValueError`.
- `setup_md_contains_no_functional_secret` — `SETUP.md` no longer contains the literal `super-secret-key-replace-in-production`.
- No regression: `pytest tests/ --ignore=tests/test_integration.py` stays green (existing 210 tests + the new one).

## Reproducibility

- Versions: Python 3.12, `pydantic-settings>=2.0`, `uv 0.11.0`.
- Fail-loud proof: `cp .env.example .env` then `uv run python -c "from core.config import Settings; Settings()"` → raises `ValidationError` ("JWT_SECRET_KEY must be configured…"), i.e. the app refuses to boot with the shipped example.
- Test command: `uv run pytest tests/test_config.py -v`.

## Risks and Assumptions

- Assumption: the validator rejects empty values — confirmed at `core/config.py:72-73` (`if not value: raise ValueError`). Invalidated only if the validator is later relaxed to allow empty.
- Assumption: no test or fixture depends on the example's old literal — `tests/conftest.py` sets `JWT_SECRET_KEY` independently via `os.environ.setdefault`, so the suite is unaffected.
- Risk: operators who currently rely on the published default will see boot fail after updating `.env`; this is the intended, documented behavior (the generation command is shown inline). Note this in the PR so it is not mistaken for a regression.
