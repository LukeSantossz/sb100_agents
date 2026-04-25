# Guia de Setup — SmartB100

Este guia permite configurar e executar o sistema SmartB100 em menos de 15 minutos.

O sistema suporta dois modos de operação do Qdrant:
- **Modo Local**: Qdrant via Docker na máquina de desenvolvimento
- **Modo Remoto**: Qdrant em servidor compartilhado via ZeroTier

---

## 1. Pré-requisitos

### Obrigatórios (ambos os modos)

| Componente | Versão | Verificação | Instalação |
|------------|--------|-------------|------------|
| Python | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| Ollama | latest | `ollama --version` | [ollama.com](https://ollama.com) |
| Git | any | `git --version` | [git-scm.com](https://git-scm.com) |

### Modo Local (adicional)

| Componente | Versão | Verificação | Instalação |
|------------|--------|-------------|------------|
| Docker | 20+ | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop) |
| Docker Compose | v2+ | `docker compose version` | Incluído no Docker Desktop |

### Modo Remoto (adicional)

| Componente | Versão | Verificação | Instalação |
|------------|--------|-------------|------------|
| ZeroTier | latest | `zerotier-cli status` | [zerotier.com](https://www.zerotier.com/download/) |

---

## 2. Modelos Ollama

Execute os comandos abaixo para baixar os modelos necessários:

```bash
# Modelo de chat (geração de respostas)
ollama pull llama3.1:8b

# Modelo de embeddings (vetorização)
ollama pull nomic-embed-text
```

> **Nota**: O modelo `llama3.1:8b` requer ~5GB de VRAM. Para máquinas com menos recursos, use `llama3.2:3b` (ajuste no `.env`).

---

## 3. Clonar e Instalar Dependências

```bash
# Clonar o repositório
git clone https://github.com/LukeSantossz/sb100_agents.git
cd sb100_agents

# Instalar dependências Python (escolha um)
uv sync                          # Recomendado (mais rápido)
# ou
pip install -e .                 # Alternativa com pip
```

---

## 4. Configuração do `.env`

Copie o arquivo de exemplo e configure conforme seu modo de operação:

```bash
cp .env.example .env
```

### 4.1 Modo Local (Docker)

Edite o `.env` com as seguintes variáveis:

```env
# === Modo Local (Qdrant via Docker) ===
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=sb100_knowledge

# Modelos Ollama
CHAT_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text

# Configurações de busca
TOP_K=3
HALLUCINATION_THRESHOLD=0.5
VERIFICATION_ENABLED=true

# JWT (troque em produção!)
JWT_SECRET_KEY=super-secret-key-replace-in-production
```

### 4.2 Modo Remoto (ZeroTier)

Para usar o servidor Qdrant remoto compartilhado:

1. **Junte-se à rede ZeroTier** (solicite o Network ID ao Tech Lead)
2. **Obtenha o IP do servidor** (solicite ao Tech Lead)
3. **Configure o `.env`**:

```env
# === Modo Remoto (Qdrant via ZeroTier) ===
QDRANT_URL=http://<REMOTE_HOST_ZEROTIER>:6333
QDRANT_API_KEY=<SOLICITAR_AO_TECH_LEAD>
COLLECTION_NAME=sb100_knowledge

# Modelos Ollama (local)
CHAT_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text

# Configurações de busca
TOP_K=3
HALLUCINATION_THRESHOLD=0.5
VERIFICATION_ENABLED=true

# JWT (troque em produção!)
JWT_SECRET_KEY=super-secret-key-replace-in-production
```

> **Importante**: As credenciais do servidor remoto (`QDRANT_API_KEY`, IP do host) são fornecidas fora do repositório por questões de segurança.

---

## 5. Inicialização dos Serviços

### 5.1 Modo Local

```bash
# Iniciar Qdrant via Docker Compose
docker compose --profile infra up -d

# Verificar se Qdrant está rodando
curl http://localhost:6333/health
# Resposta esperada: {"title":"qdrant - vector search engine","version":"..."}
```

### 5.2 Modo Remoto

```bash
# Verificar conexão ZeroTier
zerotier-cli listnetworks

# Testar conectividade com o servidor
curl http://<REMOTE_HOST_ZEROTIER>:6333/health
```

---

## 6. Ingestão de Documentos

Antes de usar o sistema, indexe os documentos PDF no Qdrant:

```bash
# Indexar todos os PDFs do diretório archives/
python scripts/ingest.py ./archives/

# Ou indexar um arquivo específico
python scripts/ingest.py ./archives/documento_agricola.pdf
```

> **Alternativa**: Usar o semantic chunker diretamente:
> ```bash
> python database/semantic_chunker.py index ./archives/
> ```

O script processa os PDFs, extrai texto, gera embeddings e armazena no Qdrant.

---

## 7. Iniciar a API

### 7.1 Modo Desenvolvimento (hot-reload)

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 Modo Produção

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7.3 Via Scripts de Inicialização

```bash
# Windows (CMD)
.\start.bat

# Windows (PowerShell)
.\start.ps1
```

Esses scripts iniciam automaticamente a API e a interface Gradio.

---

## 8. Testar a API

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Criar Usuário

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```

### Fazer Pergunta (RAG)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "question": "Como corrigir acidez do solo?",
    "profile": {
      "name": "Agricultor",
      "expertise": "beginner"
    }
  }'
```

**Resposta esperada:**
```json
{
  "answer": "Para corrigir a acidez do solo, você pode utilizar calcário agrícola...",
  "hallucination_score": 0.25
}
```

---

## 9. Interface Gradio

O sistema inclui uma interface web via Gradio para testes interativos.

### Iniciar a Interface

```bash
python ui/chat_ui.py
```

### Acessar no Navegador

Abra: **http://localhost:7860**

### Via Docker Compose (API + Gradio)

```bash
docker compose --profile infra --profile app up -d
```

Acesse:
- API: http://localhost:8000
- Gradio: http://localhost:7860
- Qdrant Dashboard: http://localhost:6333/dashboard

---

## 10. URLs dos Serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| API | http://localhost:8000 | Endpoints REST |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Gradio UI | http://localhost:7860 | Interface de chat |
| Qdrant Dashboard | http://localhost:6333/dashboard | Gerenciamento de vetores |

---

## Troubleshooting

### Ollama não encontrado

```
'ollama' is not recognized as an internal or external command
```

**Solução**: Adicione o Ollama ao PATH do sistema ou reinstale.

### Qdrant connection refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solução**: Verifique se o Docker está rodando e o container do Qdrant está ativo:
```bash
docker ps | grep qdrant
docker compose --profile infra up -d
```

### Modelo não encontrado

```
ollama._exceptions.ResponseError: model 'llama3.1:8b' not found
```

**Solução**: Baixe o modelo:
```bash
ollama pull llama3.1:8b
```

### ZeroTier não conecta

```
zerotier-cli: command not found
```

**Solução**: Instale o ZeroTier e junte-se à rede:
```bash
# Windows (PowerShell como Admin)
winget install ZeroTier.ZeroTierOne

# Linux
curl -s https://install.zerotier.com | sudo bash

# Juntar à rede
zerotier-cli join <NETWORK_ID>
```

---

## Resumo dos Comandos

### Setup Completo (Modo Local)

```bash
# 1. Modelos
ollama pull llama3.1:8b && ollama pull nomic-embed-text

# 2. Dependências
uv sync

# 3. Configuração
cp .env.example .env

# 4. Infraestrutura
docker compose --profile infra up -d

# 5. Ingestão
python scripts/ingest.py ./archives/

# 6. API
uvicorn api.main:app --reload
```

### Setup Completo (Modo Remoto)

```bash
# 1. Modelos
ollama pull llama3.1:8b && ollama pull nomic-embed-text

# 2. Dependências
uv sync

# 3. ZeroTier
zerotier-cli join <NETWORK_ID>

# 4. Configuração (editar .env com host remoto)
cp .env.example .env

# 5. Ingestão (se necessário)
python scripts/ingest.py ./archives/

# 6. API
uvicorn api.main:app --reload
```
