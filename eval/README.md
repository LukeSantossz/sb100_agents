# Pipeline de Avaliacao - SB100

Pipeline automatizado para avaliacao do sistema RAG SB100 Science.

## Estrutura

```
eval/
├── dataset/
│   ├── questions.json          # Perguntas geradas (generate_questions.py)
│   └── reference_answers.json  # Perguntas + respostas de referencia
├── results/
│   ├── evaluation_results.json # Respostas do SB100
│   ├── judged_results.json     # Julgamentos do LLM
│   ├── report.md               # Relatorio sumario
│   └── human_sample.csv        # Amostra para validacao humana
├── generate_questions.py       # Gera perguntas a partir de documentos
├── collect_references.py       # Coleta respostas de modelos de referencia
├── run_evaluation.py           # Executa perguntas contra o SB100
├── judge.py                    # Julgamento automatico por LLM
├── report.py                   # Gera relatorio e amostra humana
└── README.md
```

## Requisitos

- Python 3.12+
- Dependencias do projeto (`pip install -e .`)
- **Para Groq API**: variavel `GROQ_API_KEY` definida
- **Para Ollama**: servidor Ollama rodando com modelos instalados

## Execucao Completa

### 1. Gerar Perguntas

Extrai perguntas de dominio agricola a partir de documentos PDF/TXT:

```bash
# Usando Groq API (recomendado para qualidade)
export GROQ_API_KEY=sua_chave_aqui
python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300

# Usando Ollama local
python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300 --provider ollama
```

**Saida:** `eval/dataset/questions.json`

### 2. Coletar Respostas de Referencia

Coleta respostas de modelos open-source para cada pergunta:

```bash
# Usando Groq API (llama-3.1-8b-instant + mixtral-8x7b-32768)
python eval/collect_references.py

# Usando Ollama (llama3:8b + mistral:7b)
python eval/collect_references.py --provider ollama

# Modelos customizados
python eval/collect_references.py --models llama3:8b,qwen2:7b --provider ollama
```

**Saida:** `eval/dataset/reference_answers.json`

### 3. Executar Avaliacao do SB100

Executa todas as perguntas contra o endpoint `POST /chat`:

```bash
# Certifique-se de que o SB100 esta rodando
# Inicie a API: .venv\Scripts\python.exe -m uvicorn api.main:app --reload
# Ou use: .\start.bat (Windows)

# Em outro terminal, execute a avaliacao
python eval/run_evaluation.py

# Com requests concorrentes (mais rapido, mas pode sobrecarregar)
python eval/run_evaluation.py --concurrent 5
```

**Saida:** `eval/results/evaluation_results.json`

### 4. Julgamento Automatico

Compara respostas do SB100 com referencias usando LLM juiz:

```bash
# Usando Groq API (llama-3.1-70b-versatile)
python eval/judge.py

# Usando Ollama
python eval/judge.py --provider ollama --model llama3:70b
```

**Saida:** `eval/results/judged_results.json`

### 5. Gerar Relatorio

Gera relatorio sumario e amostra para validacao humana:

```bash
python eval/report.py

# Amostra maior
python eval/report.py --sample-size 50
```

**Saidas:**
- `eval/results/report.md` - Relatorio com estatisticas
- `eval/results/human_sample.csv` - 30 questoes para revisao humana

## Opcoes dos Scripts

### generate_questions.py

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `input` | Arquivo ou diretorio com documentos | (obrigatorio) |
| `--num-questions` | Numero de perguntas a gerar | 300 |
| `--provider` | Provider LLM (groq/ollama) | groq |
| `--model` | Modelo LLM | (depende do provider) |
| `--output` | Arquivo de saida | eval/dataset/questions.json |

### collect_references.py

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `--input` | Dataset de perguntas | eval/dataset/questions.json |
| `--output` | Arquivo de saida | eval/dataset/reference_answers.json |
| `--provider` | Provider LLM (groq/ollama) | groq |
| `--models` | Modelos separados por virgula | (depende do provider) |

### run_evaluation.py

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `--input` | Dataset com referencias | eval/dataset/reference_answers.json |
| `--output` | Arquivo de saida | eval/results/evaluation_results.json |
| `--api-url` | URL da API SB100 | http://localhost:8000 |
| `--concurrent` | Requests simultaneos | 1 |

### judge.py

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `--input` | Resultados da avaliacao | eval/results/evaluation_results.json |
| `--output` | Arquivo de saida | eval/results/judged_results.json |
| `--provider` | Provider LLM (groq/ollama) | groq |
| `--model` | Modelo juiz | llama-3.1-70b-versatile |

### report.py

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `--input` | Resultados julgados | eval/results/judged_results.json |
| `--report` | Arquivo do relatorio | eval/results/report.md |
| `--sample` | Arquivo da amostra CSV | eval/results/human_sample.csv |
| `--sample-size` | Tamanho da amostra | 30 |

## Metricas do Relatorio

- **Score (0-10)**: Avaliacao numerica da qualidade da resposta SB100
- **Veredictos**:
  - `better`: SB100 teve resposta melhor que a referencia
  - `equivalent`: Qualidade similar
  - `worse`: Referencia teve resposta melhor

## Notas

- O pipeline usa `random.seed(42)` para reproducibilidade
- O juiz alterna a ordem das respostas (50%/50%) para evitar vies de posicao
- Cada pergunta e executada com `session_id` unico para evitar contaminacao de historico
- O perfil usado na avaliacao e fixo: `{"name": "eval", "expertise": "intermediate"}`
