# A React web app replaces the Gradio page

The browser page was a Gradio app in `ui/chat_ui.py`, a second Python process that reached
the API over HTTP and read two values from `Settings` directly. Gradio 6.15 requires
`pillow<13.0`, and every one of the 41 Pillow alerts open on `main` is fixed only in Pillow
13.0.0; nothing else in the project needs Pillow. The page could not carry the identity in
`docs/brand/`, and its retry re-sent `POST /chat` after a timeout or a 504, so one question
could be answered and recorded twice (#99).

We replace it with a single-page app in `web/`, written in React and TypeScript and built
with Vite. It calls the API as `/api` on its own origin: the Vite dev server proxies that
path in development, and an nginx container does the same in Docker, both stripping the
prefix so the API routes do not change. The two values the page used to read from
`Settings` come from a new unauthenticated `GET /config`. A failed question is sent once
and never again automatically. Spec 0025 holds the full design and its tests.

## Status

Accepted. It supersedes the "transient-error retries" ADR-0003 lists among its
consequences: the page no longer retries, and `CHAT_TIMEOUT` is now how long the browser
waits for `/chat`. The rest of ADR-0003 stands.

## Considered Options

- **A React app in `web/`, served by its own nginx container (chosen)**: drops Gradio and
  Pillow from the Python dependency tree, lets the page use the brand tokens and favicon
  from `docs/brand/`, and keeps the frontend's release separate from the API image.
- **Keep Gradio until it lifts the Pillow cap**: no work, but the alerts, the duplicate
  turns and the borrowed look all stay for as long as upstream takes.
- **FastAPI serves the built app**: one container and one origin, but a Node stage inside
  `Dockerfile.api` and a frontend rebuild on every API image.
- **A framework with server rendering, such as Next.js**: a server the page does not need,
  since every screen sits behind sign-in and nothing is indexed.
- **Bake the threshold into the build (`VITE_HALLUCINATION_THRESHOLD`)**: no API change,
  but a second default for a value `.env` already sets, stale the day an operator changes it.

## Consequences

- The repository has a second toolchain. Node 22 and npm build and test `web/`, CI runs a
  `web` job, and `package-lock.json` raises its own Dependabot alerts. The page has three
  runtime dependencies: `react`, `react-dom` and `react-markdown`.
- The API gains `GET /config`, which returns `hallucination_threshold` and `chat_timeout`
  with no token. Neither is a secret, and both are read at request time, so the page always
  shows the bands the API actually uses.
- No browser origin needs CORS any more, because the page and its `/api` share an origin.
  `ALLOWED_ORIGINS` keeps only the local callers.
- A timed-out question is not re-sent, but the server may still finish and record it, so a
  manual resend can still duplicate a turn. The page says so. Only an idempotency key on
  `/chat` removes that.
- nginx's `proxy_read_timeout` is 3600 s, the upper bound of `chat_timeout`, so the page's
  own timeout always fires before the proxy gives up.
- The JWT lives in page memory only, as it did in Gradio's per-browser state: a reload
  signs the user out, and no script on the page can read the token back from storage.
