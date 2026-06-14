# Evaluation Pipeline - SB100

Automated pipeline for evaluating the SB100 Science RAG system.

## Structure

```
eval/
├── dataset/
│   ├── questions.json          # Generated questions (generate_questions.py)
│   └── reference_answers.json  # Questions + reference answers
├── results/
│   ├── evaluation_results.json # SB100 answers
│   ├── judged_results.json     # LLM judgments
│   ├── report.md               # Summary report
│   └── human_sample.csv        # Sample for human validation
├── generate_questions.py       # Generates questions from documents
├── collect_references.py       # Collects answers from reference models
├── run_evaluation.py           # Runs questions against the SB100
├── judge.py                    # Automatic LLM judging
├── report.py                   # Generates report and human sample
└── README.md
```

## Requirements

- Python 3.12+
- Project dependencies (`pip install -e .`)
- **For Groq API**: `GROQ_API_KEY` variable set
- **For Ollama**: Ollama server running with models installed
- **For `run_evaluation.py`**: evaluation credentials, since `POST /chat` is
  authenticated — `EVAL_API_TOKEN`, or `EVAL_USERNAME`/`EVAL_PASSWORD` for a
  user registered via `POST /auth/register`

## Full Run

### 1. Generate Questions

Extracts agriculture-domain questions from PDF/TXT documents:

```bash
# Using Groq API (recommended for quality)
export GROQ_API_KEY=your_key_here
python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300

# Using local Ollama
python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300 --provider ollama
```

**Output:** `eval/dataset/questions.json`

### 2. Collect Reference Answers

Collects answers from open-source models for each question:

```bash
# Using Groq API (llama-3.1-8b-instant + mixtral-8x7b-32768)
python eval/collect_references.py

# Using Ollama (llama3:8b + mistral:7b)
python eval/collect_references.py --provider ollama

# Custom models
python eval/collect_references.py --models llama3:8b,qwen2:7b --provider ollama
```

**Output:** `eval/dataset/reference_answers.json`

### 3. Run the SB100 Evaluation

Runs every question against the authenticated `POST /chat` endpoint. Set
evaluation credentials first — either `EVAL_API_TOKEN`, or `EVAL_USERNAME` and
`EVAL_PASSWORD` for a user already registered via `POST /auth/register`. Without
them the run aborts immediately (it would otherwise only collect 401s):

```bash
# Make sure the SB100 is running
# Start the API: .venv\Scripts\python.exe -m uvicorn api.main:app --reload
# Or use: .\start.bat (Windows)

# Authenticate the evaluation (registered user) — or set EVAL_API_TOKEN directly
export EVAL_USERNAME=your_eval_user
export EVAL_PASSWORD=your_eval_password

# In another terminal, run the evaluation
python eval/run_evaluation.py

# With concurrent requests (faster, but may overload)
python eval/run_evaluation.py --concurrent 5
```

**Output:** `eval/results/evaluation_results.json`

### 4. Automatic Judging

Compares SB100 answers with references using an LLM judge:

```bash
# Using Groq API (llama-3.1-70b-versatile)
python eval/judge.py

# Using Ollama
python eval/judge.py --provider ollama --model llama3:70b
```

**Output:** `eval/results/judged_results.json`

### 5. Generate Report

Generates the summary report and a sample for human validation:

```bash
python eval/report.py

# Larger sample
python eval/report.py --sample-size 50
```

**Outputs:**
- `eval/results/report.md` - Report with statistics
- `eval/results/human_sample.csv` - 30 questions for human review

## Script Options

### generate_questions.py

| Option | Description | Default |
|--------|-------------|---------|
| `input` | File or directory with documents | (required) |
| `--num-questions` | Number of questions to generate | 300 |
| `--provider` | LLM provider (groq/ollama) | groq |
| `--model` | LLM model | (depends on provider) |
| `--output` | Output file | eval/dataset/questions.json |

### collect_references.py

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Question dataset | eval/dataset/questions.json |
| `--output` | Output file | eval/dataset/reference_answers.json |
| `--provider` | LLM provider (groq/ollama) | groq |
| `--models` | Comma-separated models | (depends on provider) |

### run_evaluation.py

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Dataset with references | eval/dataset/reference_answers.json |
| `--output` | Output file | eval/results/evaluation_results.json |
| `--api-url` | SB100 API URL | http://localhost:8000 |
| `--concurrent` | Concurrent requests | 1 |

### judge.py

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Evaluation results | eval/results/evaluation_results.json |
| `--output` | Output file | eval/results/judged_results.json |
| `--provider` | LLM provider (groq/ollama) | groq |
| `--model` | Judge model | llama-3.1-70b-versatile |

### report.py

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Judged results | eval/results/judged_results.json |
| `--report` | Report file | eval/results/report.md |
| `--sample` | Sample CSV file | eval/results/human_sample.csv |
| `--sample-size` | Sample size | 30 |

## Report Metrics

- **Score (0-10)**: Numeric rating of SB100 answer quality
- **Verdicts**:
  - `better`: SB100 answered better than the reference
  - `equivalent`: Similar quality
  - `worse`: The reference answered better

## Notes

- The pipeline uses `random.seed(42)` for reproducibility
- The judge alternates answer order (50%/50%) to avoid position bias
- Each question runs with a unique `session_id` to avoid history contamination
- The profile used in the evaluation is fixed: `{"name": "eval", "expertise": "intermediate"}`
