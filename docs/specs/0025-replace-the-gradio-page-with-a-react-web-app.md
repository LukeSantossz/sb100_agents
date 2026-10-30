# SPEC: feat(web): replace the Gradio page with a React web app

## Problem

The browser UI is a Gradio page in `ui/chat_ui.py`. Gradio 6.15 requires `pillow<13.0`,
and `main` has 41 open Dependabot alerts on Pillow in `uv.lock` (5 critical, 23 high,
13 medium), all fixed only in Pillow 13.0.0. Nothing else in the project needs Pillow. The page cannot carry the identity in `docs/brand/`: its layout,
colours and favicon are Gradio's. Its retry also re-sends `POST /chat` after a timeout or
a 504, which is not idempotent, so one question can be answered and recorded twice
(#99).

## Design Decision

A single-page app in `web/`, written in React and TypeScript and built with Vite. It
calls the same API the Gradio page called and adds one small read-only endpoint. The
Gradio page, its tests and its dependency leave in the same change.

- **Same origin, no CORS.** The app calls `/api/...`. In development the Vite dev server
  proxies `/api` to `http://localhost:8000`; in Docker an nginx container serves the
  built files and proxies `/api` to the `api` service. Both strip the `/api` prefix, so
  the API routes do not change. The two Gradio origins (`:7860`) leave `ALLOWED_ORIGINS`.
- **One source for the two values the page needs.** The Gradio page read
  `hallucination_threshold` and `chat_timeout` from `Settings` in its own process. A
  browser cannot, so `GET /config` returns exactly those two, unauthenticated, read from
  `Settings` at request time. Neither is a secret. `CHAT_TIMEOUT` keeps its meaning: how
  long the page waits for `/chat`.
- **No automatic re-send.** A failed `POST /chat` (timeout, 503, 504, network error) is
  sent once. The page keeps the question in the input and says what happened; on a
  timeout it also says the server may still finish and record the answer. The user
  resends by hand. This closes #99.
- **The token lives in memory only.** As with Gradio's per-browser state, the JWT is
  held in React state and lost on reload; nothing goes to `localStorage`,
  `sessionStorage` or a cookie.
- **Same features as the Gradio page:** sign in, profile name and expertise, the
  session id with a New session button that keeps the sign-in, the conversation, and
  the hallucination score in three bands derived from the threshold (low below 0.6 x
  threshold, moderate below 1.2 x threshold, high otherwise). Two changes: each score
  sits under the answer it belongs to instead of in one side panel that the next answer
  overwrites (part 1 of #125), and the Clear chat button goes, because it cleared the
  screen but not the server-side history the next question is answered with.
- **Answers render as Markdown**, as the Gradio chatbot did, with `react-markdown` and
  no raw HTML: an answer containing markup shows it as text.
- **Identity.** The page imports `docs/brand/tokens/tokens.css` and serves
  `docs/brand/favicon/` as its public directory, so the brand files have one copy. The
  wordmark is the outlined `smartb100-logo` SVG; body text uses the system font stack,
  and no font is downloaded. The score bands get three status colours of their own, not
  the brand amber, which `docs/brand/README.md` keeps for retrieved evidence. Each band
  is also named in text, so colour is never the only signal.
- **Tooling:** npm, which ships with Node, and its `package-lock.json`. Vitest with
  Testing Library and jsdom for tests, `tsc --noEmit` in strict mode for types. Node 22
  LTS in CI and in the image.
- **Docker.** `web/Dockerfile` builds the app in a Node stage and serves it from an
  nginx stage. The build context is the repository root, because the app reads
  `docs/brand/`; `web/Dockerfile.dockerignore` limits it to `web/` and `docs/brand/`.
  The `gradio` compose service becomes `web` in the `app` profile, on port 8080, started
  after `api` is healthy. nginx's `proxy_read_timeout` is 3600 s, the upper bound of
  `chat_timeout`, so the page's own timeout is always the one that fires.
- **ADR 0016** records the move from Gradio to a separate web app.

## Alternatives Considered

- **Keep Gradio and wait for it to lift the Pillow cap.** No work, and the 41 alerts, the
  duplicate turns and the borrowed look all stay.
- **FastAPI serves the built app.** One container and one origin, but a Node stage in
  `Dockerfile.api` and a frontend release tied to every API image build.
- **Build-time `VITE_HALLUCINATION_THRESHOLD`.** No API change, but a second default for
  a value `.env` already sets, which goes stale the day an operator changes it.
- **A threshold field on every `ChatResponse`.** Also one source, but it widens the
  contract of every answer for a value that changes only on restart.
- **Plain text answers.** No Markdown dependency, and the answers the model writes
  today, with bold headings and lists, show their asterisks.
- **Retry only 503.** Safer than today's retry, but a 503 from the generator can come
  after the turn is recorded, so it is not provably idempotent either. A manual resend
  is the honest option until `/chat` takes an idempotency key.
- **Next.js, or another framework with server rendering.** A server the app does not
  need: every screen sits behind sign-in and nothing is indexed.

## Scope

- Includes:
  - `web/`: the app, its tests, `package.json` and `package-lock.json`, `vite.config.ts`,
    `tsconfig.json`, `Dockerfile`, `Dockerfile.dockerignore` and the nginx config.
  - `GET /config` in `api/` with its test.
  - `ALLOWED_ORIGINS` without the two `:7860` origins.
  - The removal of `ui/`, `tests/test_chat_ui.py`, the `gradio` dependency (Pillow leaves
    with it, since nothing else requires it) and every `ui` entry in `pyproject.toml`.
  - The compose `web` service in place of `gradio`, and `tests/test_compose_config.py`
    moved to it.
  - A `web` job in `.github/workflows/ci.yml` (`npm ci`, typecheck, test, build), and
    the web image built in `.github/workflows/docker-build.yml`.
  - `start.bat` and `start.ps1` starting the Vite dev server instead of Gradio.
  - Every mention of Gradio, `ui/chat_ui.py` and `:7860` in `README.md`, `SETUP.md`,
    `CONTEXT.md`, `.env.example` and `docker-compose.yml`.
  - `docs/adr/0016-react-web-app-replaces-gradio.md`.
- Does NOT include:
  - Creating an account from the page. `/auth/register` stays curl-only, as today, and
    the README keeps saying so.
  - Telling a measured score from one that was never computed (#249), source citations
    (#123), the empty-context warning (part 2 of #125), exporting a conversation
    (#127), feedback buttons (#131) or streaming (#132).
  - Any change to `/chat`, `/auth` or `/health`.
  - A Dependabot configuration file. GitHub already raises alerts from
    `package-lock.json` without one.

## Acceptance Criteria

Python, in `tests/`:

- `config_exposes_what_the_page_needs`: `GET /config` without a token returns 200 with
  exactly `hallucination_threshold` and `chat_timeout`, equal to the values in
  `Settings`.
- `gradio_is_gone`: `uv.lock` names neither `gradio` nor `pillow`, there is no `ui/`
  package, and no `pyproject.toml` list names `ui`.
- `cors_names_no_gradio_origin`: no entry in `ALLOWED_ORIGINS` ends in `:7860`.
- `compose_serves_the_web_app`: the `app` profile has a `web` service built from
  `web/Dockerfile`, publishing 8080 and depending on a healthy `api`, and no `gradio`
  service.
- `the_proxy_outwaits_the_page`: the nginx config sets `proxy_read_timeout` to at least
  the upper bound of `chat_timeout` in `Settings`.

Web, in `web/src/`, with Vitest:

- `sign_in_keeps_the_token_in_memory`: a successful sign-in posts the form to
  `/api/auth/token`, enables the question input, and writes nothing to `localStorage`
  or `sessionStorage`.
- `a_question_carries_the_token_session_and_profile`: Send posts to `/api/chat` with
  `Authorization: Bearer <token>`, the session id, the question, and the profile name
  and expertise.
- `a_failed_question_is_not_resent`: for a timeout, a 503, a 504 and a network error,
  exactly one request is made, the question stays in the input, and a message names
  what happened.
- `unauthorized_signs_out`: a 401 clears the token and asks the user to sign in again.
- `score_bands_follow_the_threshold`: with the threshold from `/config`, the band edges
  sit at 0.6 x and 1.2 x the threshold, and each band shows its name in text.
- `each_score_sits_under_its_answer`: after two answers, both scores are on screen,
  each with its own answer.
- `new_session_keeps_the_sign_in`: New session gives a new session id and an empty
  conversation, and the next question still carries the token.
- `markdown_renders_without_html`: `**bold**` renders as bold, and `<img src=x
  onerror=alert(1)>` in an answer appears as text with no `img` element.
- `status_colours_pass_contrast`: each band colour has a contrast ratio of at least
  4.5:1 against the background of the theme it is used in, light and dark.

Both:

- `full_suite_stays_green`: `mf check`, `pytest tests/ -m "not requires_infra"`, ruff,
  the CI mypy invocation, and in `web/` `npm ci`, `npm run typecheck`, `npm test` and
  `npm run build` all pass.

## Reproducibility

- Docker: `docker compose --profile infra --profile app up -d --build`, then open
  `http://localhost:8080`, sign in with an account made with `POST /auth/register`, and
  ask a question.
- Native: `uv run uvicorn api.main:app`, then `npm --prefix web ci` once and
  `npm --prefix web run dev`, and open `http://localhost:5173`.
- Tests: `uv run --extra dev pytest tests/ -m "not requires_infra"` and
  `npm --prefix web test`.

## Risks and Assumptions

- Risk: the repository gains a second toolchain, Node, with its own dependency tree and
  its own Dependabot alerts. Accepted: it replaces a Python dependency that holds 41
  alerts open, and the runtime dependencies are three packages (`react`,
  `react-dom`, `react-markdown`).
- Risk: the token lives in page memory, so a reload signs the user out. Accepted: that
  is what the Gradio page did, and persisting a bearer token in `localStorage` would
  expose it to any script on the page.
- Risk: on a timeout the server keeps working and may record the turn, so a manual
  resend can still duplicate it. Accepted for now: the page says so, and only an
  idempotency key on `/chat` removes it.
- Assumption: #247 is merged before this branch is cut, because the app reads
  `docs/brand/`.
- Assumption: BuildKit honours `web/Dockerfile.dockerignore` for a Dockerfile at
  `web/Dockerfile`; Docker documents this for BuildKit, which Compose uses by default.
