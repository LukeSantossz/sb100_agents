# Passo a passo para rodar o banco de dados

## Rodar docker com imagem Qdrant
```bash
docker-compose up -d
```

## Baixando modelo LLaMA 3.1:8b

### Windows (via winget): 
```bash
winget install Ollama.Ollama
ollama pull llama3.1:8b
```

### Linux/Mac (via Curl):
```bash
curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh
ollama pull llama3.1:8b
```

## Rodar o semantic_chunker.py
```bash
uv run python .\database\semantic_chunker.py index ./archives/
```

## Rodar a API
```bash
uv run uvicorn agents.agent:app --reload 
```

## Testar a API
```bash
curl "http://localhost:8000/chat?question=O%20que%20devo%20utilizar%20para%20corrigir%20a%20acidez%20do%20solo?"
```