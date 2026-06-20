# SPEC: fix(config): ignore unknown .env keys instead of failing Settings startup

## Problem
Loading a `.env` that contains keys not declared as `Settings` fields (e.g. `OLLAMA_HOST`,
`EVAL_*`) aborts application startup with a pydantic `extra_forbidden` ValidationError.

## Design Decision
Add `extra="ignore"` to the existing `SettingsConfigDict` in `core/config.py`. `Settings` then
parses only its declared fields and ignores any other dotenv/environment key, while every
field-level validator (numeric bounds, `jwt_secret_key`, `chat_rate_limit`) stays intact. This is
a one-line configuration change; no field is added or removed.

## Alternatives Considered
- Declare `OLLAMA_HOST`/`EVAL_*` as `Settings` fields — rejected: they are owned and consumed by
  other components (the `ollama` library reads `OLLAMA_HOST` straight from the environment;
  `EVAL_*` are used by `eval/`). Adding them to `Settings` creates a misleading second owner and
  unused fields.
- Document "trim your .env" in SETUP instead of fixing code — rejected: the `.env.example` we ship
  would itself break boot, defeating the example's purpose and pushing a foot-gun onto every fresh
  setup.

## Scope
- Includes: `extra="ignore"` in `SettingsConfigDict`; regression tests in `tests/test_config.py`
  for (a) load succeeds when the `.env` carries unknown keys, (b) an invalid declared field still
  raises even with unknown keys present.
- Does NOT include: changing any field, default, or validator; adding new env keys; editing
  `.env.example`, `SETUP.md`, or the `eval/`/`ollama` consumers.

## Acceptance Criteria
- `settings_loads_when_env_has_unknown_keys`: building `Settings` from a `.env` that contains
  `OLLAMA_HOST` and `EVAL_USERNAME` succeeds and the declared `jwt_secret_key` is parsed from that
  file.
- `settings_still_rejects_invalid_declared_field`: a `.env` with an empty `JWT_SECRET_KEY` (plus an
  unknown key) still raises `ValidationError`, proving `extra="ignore"` does not weaken field
  validation.

## Reproducibility
- `uv run pytest tests/test_config.py -o addopts= -v`
- Versions: pydantic-settings 2.14.2, pydantic 2.12.x, Python 3.12.

## Risks and Assumptions
- Assumption: nothing relies on `Settings` *forbidding* extra keys; the forbid behavior was
  implicit (never asserted by a test or a caller).
- Assumption: ignoring extras could mask a typo in a declared key, which would fall back to its
  default instead of erroring. Accepted: required fields with validators (`jwt_secret_key`) still
  fail loudly, and the config-decoupling benefit outweighs the risk.
