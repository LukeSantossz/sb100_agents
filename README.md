![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![CI](https://github.com/LukeSantossz/sb100_agents/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

# SmartB100: Agriculture RAG Agent

Answers questions about agriculture from your own PDF manuals, adapts the wording to the
reader's expertise, and attaches a hallucination score to every answer. It runs on a local
Ollama model, so the core pipeline needs no paid API key.

## What It Does

You point it at a folder of agricultural PDFs. It splits them into semantically coherent
chunks, embeds them into a vector database, and then answers questions using only what it
retrieved.

- **Grounded answers.** Every reply is generated from chunks retrieved out of the indexed
  PDFs, with the retrieved text wrapped in a delimiter the model is told to treat as
  reference and not as instruction.
- **Three reader profiles.** The same retrieved context is rendered for `beginner`,
  `intermediate` or `expert` through different system prompts.
- **Hallucination score.** The API samples several answers to the same question, clusters
  them by embedding similarity and returns the normalized Shannon entropy of the clusters
  as a `0.0` to `1.0` value. Read the limits of this number in
  [Known Issues & Limitations](#known-issues--limitations) before trusting it.
- **Authenticated API.** Passwords are bcrypt hashed, `/chat` needs a JWT, and register,
  login and chat each carry their own rate limit.
- **Prompt injection hardening.** Model control tokens are stripped from the question and
  the retrieved context is delimited, on both the classic and the agent code path.

## What It Is

A REST API built with FastAPI, plus an optional Gradio web page that talks to it. It is one
process: `api/main.py` imports every domain module directly and calls it in the same
interpreter. Only two other processes exist, Qdrant for the vectors and Ollama for the
models, and user accounts sit in a SQLite file next to the code.

It is aimed at agricultural extension workers and agronomists who need an answer out of a
long technical manual without reading it, and who need to know when the answer is shaky.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| API and runtime | FastAPI, Uvicorn |
| Web page | Gradio |
| Vector database | Qdrant, collection `archives_v2`, 768 dimensions, cosine |
| Inference | Ollama: `llama3.2:3b` for chat, `nomic-embed-text` for embeddings |
| Verification | Semantic entropy over Groq, Ollama or OpenRouter samples |
| Agent path (off by default) | deepagents on LangGraph |
| Persistence | SQLite for user accounts |
| Auth | bcrypt via passlib, JWT via PyJWT, rate limiting via slowapi |
| Testing and CI | pytest, ruff, mypy, GitHub Actions |
| Packaging | uv, Docker |

## Architecture

One FastAPI process holds the whole pipeline. `POST /chat` embeds the question, searches
Qdrant, builds a profile specific prompt, calls Ollama, and optionally scores the answer
before returning it. Conversation history lives in a per session in memory buffer, not in
the database.

```mermaid
flowchart LR
    CLIENT["Gradio UI :7860<br/>or curl"] -->|"POST /chat + JWT"| API["FastAPI :8000"]
    API --> EMBED["Embedder<br/>nomic-embed-text"]
    EMBED --> SEARCH["Vector search<br/>top_k chunks"]
    SEARCH --> QDRANT[("Qdrant :6333<br/>archives_v2")]
    SEARCH --> PROMPT["Profile prompt<br/>beginner / intermediate / expert"]
    BUFFER["Conversation buffer<br/>in memory, FIFO"] --> PROMPT
    PROMPT --> LLM["Generator<br/>llama3.2:3b"]
    LLM --> GATE["Verification gate"]
    GATE -->|"sample and cluster"| ENTROPY["Semantic entropy"]
    ENTROPY --> GATE
    GATE --> RESP["ChatResponse<br/>answer + hallucination_score"]
    API --> AUTH["/auth/*"] --> SQLITE[("SQLite<br/>users")]
```

What runs where:

| Component | Role | How it runs | Reached over |
| --- | --- | --- | --- |
| Qdrant | vector database | `docker compose --profile infra` | HTTP `:6333`, gRPC `:6334` |
| Ollama | chat and embedding models | on the host, not in Docker | HTTP `:11434` |
| SQLite | user accounts | a file at the repository root | SQLAlchemy |
| API and Gradio | the application | native, or `docker compose --profile app` | HTTP `:8000` and `:7860` |

An agent path built on deepagents exists behind `AGENT_ENABLED` and is off by default. When
it is on, `/chat` runs a bounded LangGraph loop that calls retrieval as a tool instead of
calling it directly. See ADR-0008 and ADR-0012.

## Engineering Decisions

Each row points at the decision record holding the full rationale and the rejected options.

| Decision | Alternative considered | Record |
| --- | --- | --- |
| One modular monolith | a service per RAG step | [ADR-0001](./docs/adr/0001-modular-monolith.md) |
| Semantic entropy as the hallucination score | a trained classifier or an LLM judge | [ADR-0002](./docs/adr/0002-semantic-entropy-hallucination-score.md) |
| Local first inference via Ollama | hosted embeddings and a larger hosted model | [ADR-0003](./docs/adr/0003-local-first-inference-via-ollama.md) |
| Verification dispatched across providers | OpenAI only | [ADR-0004](./docs/adr/0004-multi-provider-verification-dispatch.md) |
| SQLite | PostgreSQL | [ADR-0007](./docs/adr/0007-sqlite-persistence.md) |
| deepagents as the agent substrate | raw LangGraph or a hand written loop | [ADR-0008](./docs/adr/0008-deepagents-orchestration-substrate.md) |
| Gate threshold and loop bounds set by measurement | guessed defaults | [ADR-0015](./docs/adr/0015-calibrated-agent-gate-and-loop-bounds.md) |

Fifteen records in total, including the ones behind the auth gate, the synchronous handler
and the Qdrant volume layout. They are in [`docs/adr/`](./docs/adr/).

## Getting Started

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://www.docker.com/products/docker-desktop/), for Qdrant
- [Ollama](https://ollama.com/download), running on the host

The two Ollama models are about 2.2 GB together. A GPU is not required, but read the
timings in [Known Issues & Limitations](#known-issues--limitations) before judging the
latency.

### Installation

```bash
git clone --recurse-submodules https://github.com/LukeSantossz/sb100_agents.git
cd sb100_agents

ollama pull llama3.2:3b
ollama pull nomic-embed-text

uv sync --extra dev
```

`--extra dev` is not optional: `ruff`, `mypy` and `pytest-cov` live there, and the pytest
options in `pyproject.toml` fail without `pytest-cov`.

### Configuration

```bash
cp .env.example .env
```

Then set one value in `.env`. `JWT_SECRET_KEY` has no default and nothing starts without
it, including the indexing script:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the output into `JWT_SECRET_KEY=`. Everything else in `.env.example` already has a
working local value. Two settings are worth knowing about:

| Variable | Default | What it changes |
| --- | --- | --- |
| `VERIFICATION_PROVIDER` | `groq` | Which model samples answers for the score. `groq` and `openrouter` need an API key; `ollama` needs none and runs locally. |
| `AGENT_ENABLED` | `false` | Routes `/chat` through the deepagents loop instead of the direct pipeline. |

Without a `GROQ_API_KEY` the score is not computed and every answer comes back with the
neutral `0.5`. Set `VERIFICATION_PROVIDER=ollama` for a real score with no key, or
`VERIFICATION_ENABLED=false` to skip scoring and get faster answers.

### Running

```bash
# 1. Vector database
docker compose --profile infra up -d

# 2. Index the PDFs in archives/ (first run only)
uv run python scripts/ingest.py ./archives/

# 3. API
uv run python -m uvicorn api.main:app --reload

# 4. Optional web page, in a second terminal
uv run python ui/chat_ui.py
```

Step 2 embeds one sentence at a time. The 511 page PDF shipped in `archives/` produced 519
chunks in 15 minutes 41 seconds on a CPU only Windows host. It is the slowest part of the
setup and it only happens once.

Checks that the stack is up:

```bash
curl http://localhost:6333/healthz   # healthz check passed
curl http://localhost:8000/health    # {"status":"ok"}
```

Windows users can run `.\start.bat` or `.\start.ps1` after installation; both scripts start
Qdrant, pull the models if missing, and open the API and the web page in separate windows.
Full Docker deployment is `docker compose --profile infra --profile app up -d`, which needs
`JWT_SECRET_KEY` exported in the host environment. Remote Qdrant and native Linux notes are
in [`SETUP.md`](./SETUP.md).

### Tests

```bash
uv run --extra dev pytest tests/ -m "not requires_infra"   # unit and integration suite
uv run --extra dev ruff check .                            # lint
uv run --extra dev ruff format --check .                   # formatting
uv run --extra dev mypy retrieval/ generation/ memory/     # types, as CI runs it
```

The `requires_infra` marker excludes the tests that need a live Ollama or Qdrant, which is
also what CI runs. Nothing in the default selection reaches the network.

## API Reference

| Method | Endpoint | Auth | Rate limit | Description |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/register` | none | 3 per hour per IP | Creates a user. JSON body. |
| `POST` | `/auth/token` | none | 5 per 15 min per IP | OAuth2 password form, returns a JWT valid for 7 days. |
| `POST` | `/chat` | Bearer JWT | 30 per minute per user | Runs the RAG pipeline and returns the answer plus its score. |
| `GET` | `/health` | none | none | Returns `{"status":"ok"}`. Does not check Qdrant or Ollama. |

Interactive docs are at `http://localhost:8000/docs` once the API is up.

A full run, from no account to an answer:

```bash
# 1. Create an account
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo-password-123"}'
# {"message":"User created successfully","username":"demo"}

# 2. Exchange the credentials for a token
curl -X POST http://localhost:8000/auth/token \
  -d "username=demo&password=demo-password-123"
# {"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}

# 3. Ask a question, pasting the access_token from step 2
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer PASTE_THE_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "question": "Como corrigir a acidez do solo?",
    "profile": {"name": "User", "expertise": "beginner"}
  }'
# {"answer":"A acidez do solo ...","hallucination_score":0.5}
```

With `jq` on the path, step 2 becomes
`TOKEN=$(curl -s -X POST http://localhost:8000/auth/token -d "username=demo&password=demo-password-123" | jq -r .access_token)`
and step 3 can send `-H "Authorization: Bearer $TOKEN"`.

The answer takes a while: see the timings in
[Known Issues & Limitations](#known-issues--limitations). The shipped corpus is a Portuguese
language agricultural bulletin, so ask in Portuguese. The answer follows the language of the
question.

Without the `Authorization` header `/chat` returns `401`.

| Request field | Type | Notes |
| --- | --- | --- |
| `session_id` | string | Groups turns into one conversation. Scoped to the caller. |
| `question` | string | 1 to 2000 characters. |
| `profile.name` | string | 1 to 255 characters. |
| `profile.expertise` | enum | `beginner`, `intermediate` or `expert`. |

| Response field | Type | Notes |
| --- | --- | --- |
| `answer` | string | The generated answer. |
| `hallucination_score` | float | `0.0` grounded to `1.0` likely hallucinated. `0.5` is also what the gate returns when verification could not run. |

The Gradio page at `:7860` logs in and chats, but it cannot create an account. Register
through the API or through `/docs` first.

## Project Structure

```
sb100_agents/
├── api/                # FastAPI app: main.py plus routes/ (chat, auth, health)
├── agent/              # deepagents loop, tools, intent gate, run bounds
├── core/               # settings (pydantic-settings) and the request/response schemas
├── retrieval/          # embedding calls and Qdrant search
├── generation/         # prompt building, sanitizing, and the Ollama chat call
├── memory/             # in memory conversation buffer
├── verification/       # semantic entropy and the score gate
├── database/           # SQLAlchemy models, session, PDF semantic chunker
├── ui/                 # Gradio page
├── eval/               # offline evaluation and agent-calibration scripts
├── scripts/ingest.py   # indexing entry point
├── tests/              # the whole test suite
├── docs/adr/           # decision records
├── docs/specs/         # approved specs
└── archives/           # the PDF corpus that gets indexed
```

Start reading at `api/routes/chat.py`. It is the whole pipeline in one function.

## Project Status

MVP complete and still being hardened.

Working:

- [x] PDF ingestion, semantic chunking, indexing into Qdrant
- [x] RAG chat with the three expertise profiles
- [x] Semantic entropy score with a provider choice and a neutral fallback
- [x] bcrypt and JWT auth with per IP and per user rate limits
- [x] Docker Compose deployment with healthchecks and log rotation
- [x] Offline evaluation pipeline in `eval/`
- [x] Agent path behind `AGENT_ENABLED`: retrieval as a tool, domain gate, bounded loop

`uv run --extra dev pytest tests/ -m "not requires_infra"` reports 370 passing tests and 90
percent line coverage over the modules listed under `[tool.coverage.run]` in
`pyproject.toml`. The CI floor is set far below that, at 23 percent, which is the gap the
next list names.

Not done:

- [ ] Turning `AGENT_ENABLED` on by default, which is a separate decision from building it
- [ ] Persisting conversation history, so it survives a restart
- [ ] Raising the CI coverage floor to match the coverage actually achieved
- [ ] Hybrid search, dense plus sparse with RRF fusion
- [ ] Claim level verification, splitting an answer into claims and checking each
- [ ] Streaming responses over SSE

The sequencing is in the [migration roadmap](./docs/roadmap.md).

## Known Issues & Limitations

- **Answers take minutes on CPU.** Measured on a CPU only Windows host with `llama3.2:3b`:
  138 seconds for a warm `/chat` call, 338 seconds for the first call after startup, and 478
  seconds with local scoring on, since scoring generates the answer plus one sample per
  `ENTROPY_NUM_SAMPLES`. The first call is the slow one because Ollama loads the model before
  generating; with the `Settings` default of 240 seconds it exceeded `OLLAMA_TIMEOUT` and
  returned a `503`, which is why `.env.example` ships 540. A GPU or a hosted provider removes
  the whole problem.
- **The score is coarse at the default sample count.** `ENTROPY_NUM_SAMPLES` defaults to 2.
  Entropy over two samples can only be `0.0` or `1.0`, so the value is effectively a yes or
  no. Raising the count gives intermediate values, and multiplies the generation cost by the
  same factor.
- **No key means no score.** The default `VERIFICATION_PROVIDER=groq` needs `GROQ_API_KEY`.
  Without it the gate returns the neutral `0.5` and logs a warning rather than failing the
  request. `VERIFICATION_PROVIDER=ollama` scores locally with no key.
- **Conversation history is not persisted.** It lives in a per process dictionary with a one
  hour idle TTL and a 1000 session cap. Restarting the API loses it. The `conversations` and
  `messages` tables exist in `database/models.py` and are created at startup, but nothing
  writes to them yet.
- **Re-indexing appends, it does not replace.** `scripts/ingest.py` assigns a fresh UUID to
  every chunk, so running it twice over the same PDF stores the content twice. Drop the
  Qdrant collection before re-indexing.
- **SQLite is single writer.** Fine for one API process, wrong for horizontal scaling. See
  ADR-0007 for when PostgreSQL becomes the answer.
- **The registration rate limit is tight.** Three registrations per hour per IP. A few failed
  attempts while exploring will lock the endpoint for the rest of the hour.
- **The Docker bind mount for SQLite needs the file to exist.** If `./smartb100_v2.db` is
  absent, Docker Desktop may create a directory with that name. The API raises an explicit
  `RuntimeError` when it finds one. Create the empty file before `docker compose --profile
  app up`.
- **Accounts predating the bcrypt gate do not work.** They were stored as SHA-256 hashes and
  have to be registered again.
- **The Qdrant client logs a version warning.** `qdrant-client` resolves to 1.17 while
  `qdrant/qdrant:latest` is on 1.19, so the client prints an incompatibility `UserWarning` on
  the first search. Search works; pin the image tag to match the client if the warning
  matters to you.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). In short: open an issue, branch as
`type/NNN-short-description`, write the test first, write a spec under `docs/specs/` for
anything non trivial, use Conventional Commits, open a PR.

## License

[MIT](./LICENSE)
