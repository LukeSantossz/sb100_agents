# Setup Guide — SmartB100

This guide gets SmartB100 configured and running in under 15 minutes.

The system supports two Qdrant operation modes:
- **Local Mode**: Qdrant via Docker on the development machine
- **Remote Mode**: Qdrant on a shared server via ZeroTier

---

## 1. Prerequisites

### Required (both modes)

| Component | Version | Check | Install |
|-----------|---------|-------|---------|
| Python | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| Ollama | latest | `ollama --version` | [ollama.com](https://ollama.com) |
| Git | any | `git --version` | [git-scm.com](https://git-scm.com) |

### Local Mode (additional)

| Component | Version | Check | Install |
|-----------|---------|-------|---------|
| Docker | 20+ | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop) |
| Docker Compose | v2+ | `docker compose version` | Included in Docker Desktop |

### Remote Mode (additional)

| Component | Version | Check | Install |
|-----------|---------|-------|---------|
| ZeroTier | latest | `zerotier-cli status` | [zerotier.com](https://www.zerotier.com/download/) |

---

## 2. Ollama Models (local)

Ollama must be installed and run **locally** (not via Docker). Run the commands below to download the required models:

```bash
# Chat model (answer generation)
ollama pull llama3.2:3b

# Embedding model (vectorization)
ollama pull nomic-embed-text
```

> **Note**: The default model is `llama3.2:3b` (lighter). For machines with more resources, use `llama3.1:8b` (adjust `CHAT_MODEL` in `.env`).

---

## 3. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/LukeSantossz/sb100_agents.git
cd sb100_agents

# Install Python dependencies (pick one)
uv sync                          # Recommended (faster)
# or
pip install -e .                 # pip alternative
```

---

## 4. `.env` Configuration

Copy the example file and configure it for your operation mode:

```bash
cp .env.example .env
```

### 4.1 Local Mode (Docker)

Edit `.env` with the following variables:

```env
# === Local Mode (Qdrant via Docker) ===
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=archives_v2

# Ollama models (runs locally, not via Docker)
CHAT_MODEL=llama3.2:3b
EMBED_MODEL=nomic-embed-text

# Search settings
TOP_K=3
HALLUCINATION_THRESHOLD=0.5
VERIFICATION_ENABLED=true

# JWT (change in production!)
JWT_SECRET_KEY=super-secret-key-replace-in-production
```

### 4.2 Remote Mode (ZeroTier)

To use the shared remote Qdrant server:

1. **Join the ZeroTier network** (request the Network ID from the Tech Lead)
2. **Get the server IP** (request it from the Tech Lead)
3. **Configure `.env`**:

```env
# === Remote Mode (Qdrant via ZeroTier) ===
QDRANT_URL=http://<REMOTE_HOST_ZEROTIER>:6333
QDRANT_API_KEY=<REQUEST_FROM_TECH_LEAD>
COLLECTION_NAME=archives_v2

# Ollama models (runs locally, not via Docker)
CHAT_MODEL=llama3.2:3b
EMBED_MODEL=nomic-embed-text

# Search settings
TOP_K=3
HALLUCINATION_THRESHOLD=0.5
VERIFICATION_ENABLED=true

# JWT (change in production!)
JWT_SECRET_KEY=super-secret-key-replace-in-production
```

> **Important**: The remote server credentials (`QDRANT_API_KEY`, host IP) are provided outside the repository for security reasons.

---

## 5. Starting the Services

### 5.1 Local Mode

```bash
# Start Qdrant via Docker Compose (Qdrant only — Ollama runs locally)
docker compose --profile infra up -d

# Check that Qdrant is running
curl http://localhost:6333/health
# Expected response: {"title":"qdrant - vector search engine","version":"..."}

# Check that Ollama is running locally
ollama list
```

### 5.2 Remote Mode

```bash
# Check the ZeroTier connection
zerotier-cli listnetworks

# Test connectivity to the server
curl http://<REMOTE_HOST_ZEROTIER>:6333/health
```

---

## 6. Document Ingestion

Before using the system, index the PDF documents into Qdrant:

```bash
# Index every PDF in the archives/ directory
python scripts/ingest.py ./archives/

# Or index a specific file
python scripts/ingest.py ./archives/agricultural_document.pdf
```

> **Alternative**: Use the semantic chunker directly:
> ```bash
> python database/semantic_chunker.py index ./archives/
> ```

The script processes the PDFs, extracts text, generates embeddings, and stores them in Qdrant.

---

## 7. Starting the API

### 7.1 Development Mode (hot-reload)

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 Production Mode

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7.3 Via Startup Scripts

```bash
# Windows (CMD)
.\start.bat

# Windows (PowerShell)
.\start.ps1
```

These scripts start the API and the Gradio interface automatically.

---

## 8. Testing the API

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Create a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```

### Ask a Question (RAG)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "question": "How do I correct soil acidity?",
    "profile": {
      "name": "Farmer",
      "expertise": "beginner"
    }
  }'
```

**Expected response:**
```json
{
  "answer": "To correct soil acidity, you can apply agricultural lime...",
  "hallucination_score": 0.25
}
```

---

## 9. Gradio Interface

The system includes a Gradio web interface for interactive testing.

### Start the Interface

```bash
python ui/chat_ui.py
```

### Open in the Browser

Go to: **http://localhost:7860**

### Via Docker Compose (API + Gradio)

```bash
docker compose --profile infra --profile app up -d
```

Access:
- API: http://localhost:8000
- Gradio: http://localhost:7860
- Qdrant Dashboard: http://localhost:6333/dashboard

> The compose stack uses a **multi-stage build** (Dockerfile.api) — the final
> image does not contain `build-essential`. **Healthchecks** enforce real
> startup order: `api` only starts after `qdrant` is healthy; `gradio` only
> starts after `api` is healthy. **Logging** with `max-size: 10m` and
> `max-file: 3` prevents disk exhaustion on long runs.

---

## 9.1 Native Linux Deploy

On native Linux (without Docker Desktop), `host.docker.internal` **does not
resolve by default**. Since Ollama runs outside Docker (on the host), there are
three options:

**(a) Override via `OLLAMA_HOST` in `.env`** — `docker0` gateway:
```env
OLLAMA_HOST=http://172.17.0.1:11434
```

**(b) Inline in the compose invocation:**
```bash
OLLAMA_HOST=http://172.17.0.1:11434 \
  docker compose --profile infra --profile app up -d
```

**(c) Map `host.docker.internal` to the host-gateway** — add to
`docker-compose.yml` (not enabled by default to preserve Docker Desktop
compatibility):
```yaml
api:
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

Check connectivity from the container:
```bash
docker compose exec api curl -fsS "$OLLAMA_HOST/api/tags"
```

> **Diagnostics**: to confirm the docker gateway IP on the Linux host, use
> `ip route | grep docker0` (third column). On hosts with a firewall (ufw),
> make sure port `11434` is open to the `docker0` network.

---

## 10. Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | REST endpoints |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Gradio UI | http://localhost:7860 | Chat interface |
| Qdrant Dashboard | http://localhost:6333/dashboard | Vector management |

---

## Troubleshooting

### Ollama not found

```
'ollama' is not recognized as an internal or external command
```

**Fix**: Add Ollama to the system PATH or reinstall.

### Qdrant connection refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Fix**: Check that Docker is running and the Qdrant container is up:
```bash
docker ps | grep qdrant
docker compose --profile infra up -d
```

### Model not found

```
ollama._exceptions.ResponseError: model 'llama3.2:3b' not found
```

**Fix**: Download the model:
```bash
ollama pull llama3.2:3b
```

### ZeroTier does not connect

```
zerotier-cli: command not found
```

**Fix**: Install ZeroTier and join the network:
```bash
# Windows (PowerShell as Admin)
winget install ZeroTier.ZeroTierOne

# Linux
curl -s https://install.zerotier.com | sudo bash

# Join the network
zerotier-cli join <NETWORK_ID>
```

---

## Command Summary

### Full Setup (Local Mode)

```bash
# 1. Models
ollama pull llama3.2:3b && ollama pull nomic-embed-text

# 2. Dependencies
uv sync

# 3. Configuration
cp .env.example .env

# 4. Infrastructure
docker compose --profile infra up -d

# 5. Ingestion
python scripts/ingest.py ./archives/

# 6. API
uvicorn api.main:app --reload
```

### Full Setup (Remote Mode)

```bash
# 1. Models
ollama pull llama3.2:3b && ollama pull nomic-embed-text

# 2. Dependencies
uv sync

# 3. ZeroTier
zerotier-cli join <NETWORK_ID>

# 4. Configuration (edit .env with the remote host)
cp .env.example .env

# 5. Ingestion (if needed)
python scripts/ingest.py ./archives/

# 6. API
uvicorn api.main:app --reload
```
