    # 📖 DOCUMENTAÇÃO COMPLETA — SmartB100 (Squad 5)

    > **Última atualização:** 09/07/2026  
    > **Gerado por:** Antigravity (Claude Opus 4.6)  
    > **Escopo:** Análise completa de cada pasta, cada arquivo, cada tecnologia e tradeoffs

    ---

    ## 📋 Índice

    1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
    2. [Arquitetura Geral](#2-arquitetura-geral)
    3. [Stack Tecnológico e Tradeoffs](#3-stack-tecnológico-e-tradeoffs)
    4. [Estrutura de Pastas e Arquivos](#4-estrutura-de-pastas-e-arquivos)
    - [4.1 Raiz do Projeto](#41-raiz-do-projeto)
    - [4.2 `api/` — Camada de API REST](#42-api--camada-de-api-rest)
    - [4.3 `core/` — Configuração e Schemas](#43-core--configuração-e-schemas)
    - [4.4 `retrieval/` — Busca Vetorial](#44-retrieval--busca-vetorial)
    - [4.5 `generation/` — Geração de Respostas com LLM](#45-generation--geração-de-respostas-com-llm)
    - [4.6 `memory/` — Histórico de Conversa](#46-memory--histórico-de-conversa)
    - [4.7 `verification/` — Detecção de Alucinação](#47-verification--detecção-de-alucinação)
    - [4.8 `database/` — Banco de Dados e Indexação de PDFs](#48-database--banco-de-dados-e-indexação-de-pdfs)
    - [4.9 `agent/` — Camada Agêntica](#49-agent--camada-agêntica)
    - [4.10 `ui/` — Interface Gradio](#410-ui--interface-gradio)
    - [4.11 `eval/` — Pipeline de Avaliação](#411-eval--pipeline-de-avaliação)
    - [4.12 `tests/` — Testes Automatizados](#412-tests--testes-automatizados)
    - [4.13 `scripts/` — Scripts Utilitários](#413-scripts--scripts-utilitários)
    - [4.14 `docs/` — Documentação Técnica](#414-docs--documentação-técnica)
    - [4.15 `.github/` — CI/CD e Templates](#415-github--cicd-e-templates)
    - [4.16 `archives/` — PDFs Fonte](#416-archives--pdfs-fonte)
    5. [Fluxo Completo de uma Requisição](#5-fluxo-completo-de-uma-requisição)
    6. [Decisões Arquiteturais (ADRs)](#6-decisões-arquiteturais-adrs)
    7. [Como Rodar o Projeto](#7-como-rodar-o-projeto)
    8. [Glossário de Termos](#8-glossário-de-termos)

    ---

    ## 1. Visão Geral do Projeto

    O **SmartB100** é um **assistente de IA para agricultura** que responde perguntas técnicas baseando-se em manuais e boletins agrícolas em PDF. Ele **NÃO inventa respostas** — toda resposta é fundamentada em documentos reais indexados pelo sistema.

    ### O que ele faz em termos simples:

    1. **Recebe PDFs agrícolas** (manuais de plantio, boletins técnicos, etc.)
    2. **"Corta" os PDFs em pedaços inteligentes** (chunks semânticos) e transforma cada pedaço em um vetor numérico (embedding)
    3. **Armazena esses vetores** em um banco de dados vetorial (Qdrant)
    4. Quando o usuário faz uma **pergunta**, o sistema:
    - Transforma a pergunta em vetor
    - Busca os pedaços mais parecidos no banco
    - Monta uma resposta usando esses pedaços como contexto
    - **Verifica se a resposta é confiável** usando entropia semântica
    5. **Adapta a linguagem** da resposta ao nível do usuário (iniciante, intermediário, expert)

    ### Pipeline RAG (Retrieval-Augmented Generation):

    ```
    Pergunta do Usuário
        ↓
    [1] Embedding (converte pergunta em vetor 768-dim)
        ↓
    [2] Busca Vetorial (encontra chunks similares no Qdrant)
        ↓
    [3] Geração (LLM cria resposta usando os chunks como base)
        ↓
    [4] Verificação (entropia semântica pontua confiabilidade 0.0-1.0)
        ↓
    Resposta + Score de Alucinação
    ```

    ---

    ## 2. Arquitetura Geral

    O SmartB100 é um **monolito modular** — um único processo Python que carrega todos os módulos internamente. A comunicação entre módulos é por chamadas de função diretas, sem rede.

    ### Componentes externos (processos separados):

    | Componente | O que faz | Porta |
    |---|---|---|
    | **Qdrant** | Banco de dados vetorial | `:6333` (REST) / `:6334` (gRPC) |
    | **Ollama** | Servidor de IA local (chat + embeddings) | `:11434` |
    | **SQLite** | Banco relacional (usuários, conversas) | Arquivo local |

    ### Clientes:

    | Cliente | Descrição | Porta |
    |---|---|---|
    | **Gradio UI** | Interface web com chat | `:7860` |
    | **HTTP direto** | curl, scripts, apps | `:8000` |

    ### Por que monolito modular e não microserviços?

    O pipeline RAG (embed → busca → gera → verifica) compartilha o mesmo modelo de dados e roda sequencialmente dentro de uma única requisição. Dividir em microserviços adicionaria:
    - Latência de rede entre chamadas que hoje são in-process
    - Complexidade de versionamento de contratos
    - Sem ganho de escala independente na carga atual

    ---

    ## 3. Stack Tecnológico e Tradeoffs

    ### 3.1 Linguagem: Python 3.12+

    **Por que Python?**
    - Ecossistema de IA/ML mais maduro (LangChain, Ollama SDK, Qdrant client, etc.)
    - Prototipagem rápida
    - Comunidade massiva em NLP/IA

    **Tradeoff vs. outras linguagens:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Go** | Mais rápido, compilado, concorrência nativa | Ecossistema de IA muito menor, sem libs RAG maduras |
    | **TypeScript/Node** | Bom para APIs web, TypeScript tipado | Ecossistema de IA inferior ao Python, GIL não é issue aqui |
    | **Rust** | Performance máxima, segurança de memória | Curva de aprendizado alta, ecossistema IA nascente |

    ---

    ### 3.2 API: FastAPI + Uvicorn

    **O que é:** Framework web assíncrono para Python, rodando sobre o servidor ASGI Uvicorn.

    **Por que FastAPI?**
    - Geração automática de documentação (Swagger/OpenAPI)
    - Validação de dados com Pydantic embutida
    - Suporte nativo a injeção de dependências (ideal para auth)
    - Tipagem forte
    - Performance superior a Flask/Django para APIs

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Flask** | Mais simples, mais popular | Sem validação nativa, sem async nativo, sem docs automáticas |
    | **Django REST** | Mais completo (admin, ORM) | Pesado demais para uma API RAG, overhead desnecessário |
    | **Express (Node)** | Leve, rápido | Ecossistema Python perdido, menos integração com libs IA |

    ---

    ### 3.3 LLM Local: Ollama (llama3.2:3b + nomic-embed-text)

    **O que é:** Servidor que roda modelos de IA localmente, sem precisar de API paga.

    **Por que Ollama?**
    - **Gratuito** — sem custo por requisição
    - **Offline** — funciona sem internet
    - **Privacidade** — dados nunca saem da máquina
    - **Espaço de embeddings estável** — não muda entre versões da API

    **Modelos usados:**

    | Modelo | Função | Dimensão |
    |---|---|---|
    | `llama3.2:3b` | Gerar respostas de chat | — |
    | `nomic-embed-text` | Converter texto em vetores | 768 dimensões |

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **OpenAI API** | Melhor qualidade (GPT-4), mais rápido | Pago ($), dados enviados para fora, depende de internet |
    | **Anthropic Claude** | Qualidade excelente, janela de contexto grande | Pago ($), vendor lock-in |
    | **Google Gemini** | Gratuito (tier free), multimodal | Menos controle, depende de internet |
    | **Hugging Face local** | Mais modelos disponíveis | Setup mais complexo que Ollama |

    ---

    ### 3.4 Banco Vetorial: Qdrant

    **O que é:** Banco de dados especializado em guardar e buscar vetores (embeddings).

    **Por que Qdrant?**
    - Open-source, auto-hospedável
    - API REST e gRPC
    - Rápido em busca por similaridade (ANN — Approximate Nearest Neighbors)
    - Payload junto do vetor (guarda o texto do chunk + metadados)
    - Docker pronto

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Pinecone** | Totalmente gerenciado, escala fácil | Pago, vendor lock-in, dados fora |
    | **Weaviate** | Multimodal, GraphQL | Mais pesado, setup mais complexo |
    | **ChromaDB** | Simples, in-process | Menos maduro para produção, sem gRPC |
    | **FAISS** | Biblioteca (sem servidor), muito rápido | Sem persistência nativa, sem API REST |
    | **pgvector** | Usa PostgreSQL existente | Performance inferior para buscas vetoriais em escala |

    ---

    ### 3.5 Banco Relacional: SQLite

    **O que é:** Banco de dados embutido em arquivo — zero configuração.

    **Por que SQLite?**
    - Zero-ops: não precisa instalar servidor
    - Perfeito para single-node (um processo de API)
    - Arquivo único (`smartb100_v2.db`)

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **PostgreSQL** | Multi-escritor, escala horizontal | Precisa instalar/configurar servidor, mais complexo |
    | **MySQL** | Popular, maduro | Mesmo overhead do PostgreSQL sem os benefícios |
    | **MongoDB** | Schema flexível | Overkill para tabelas estruturadas simples |

    ---

    ### 3.6 Autenticação: bcrypt + JWT

    **O que é:** Senhas armazenadas com hash bcrypt; autenticação via tokens JWT.

    **Por que essa combinação?**
    - **bcrypt**: hash com salt aleatório embutido, resistente a ataques de força bruta
    - **JWT**: stateless (o servidor não precisa guardar sessões), revogável, padrão OAuth2

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Session cookies** | Mais simples para web | Stateful, não escala horizontalmente |
    | **API keys estáticas** | Mais simples | Sem expiração, sem identidade, vazamento = acesso permanente |
    | **OAuth2 com provider externo** | SSO, mais seguro | Complexidade alta, depende de serviço externo |

    ---

    ### 3.7 UI: Gradio

    **O que é:** Biblioteca Python para criar interfaces web de chat/demo rapidamente.

    **Por que Gradio?**
    - Deploy em 1 arquivo Python
    - Chat nativo
    - Integra com o ecossistema ML/IA Python
    - Não precisa de frontend separado

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Streamlit** | Mais bonito visualmente | Mais pesado, menos flexível para chat |
    | **React/Next.js** | Frontend profissional, UX customizável | Precisa de dev frontend, build separado |
    | **Chainlit** | Feito para LLMs, streaming nativo | Menos maduro, comunidade menor |

    ---

    ### 3.8 Verificação: Entropia Semântica (Multi-provider)

    **O que é:** Técnica para detectar alucinações. Gera N respostas para a mesma pergunta, agrupa por similaridade semântica, e calcula entropia de Shannon. Se as respostas são muito diferentes entre si (alta entropia), a resposta provavelmente é inventada.

    **Por que essa abordagem?**
    - Score contínuo (0.0 a 1.0) — não é binário (sim/não)
    - Não precisa de dados rotulados para treinar
    - Baseado em paper acadêmico (Farquhar et al., 2023)

    **Providers suportados:**

    | Provider | Modelo padrão | Custo | Velocidade |
    |---|---|---|---|
    | **Groq** (padrão) | `llama-3.1-8b-instant` | Gratuito (free tier) | Muito rápido |
    | **Ollama** (local) | `llama3.2:3b` | Gratuito | Lento em CPU |
    | **OpenRouter** | `google/gemma-4-31b-it` | Pago | Variável |

    **Tradeoff:**

    | Alternativa | Prós | Contras |
    |---|---|---|
    | **Classificador binário** | Mais rápido, resultado simples | Precisa de dados rotulados, sem gradação |
    | **LLM-as-Judge** | Explicação do motivo | Mais caro (2 calls LLM), subjetivo |
    | **HHEM (classificador)** | Rápido | Binário, sem score contínuo |

    ---

    ## 4. Estrutura de Pastas e Arquivos

    ### 4.1 Raiz do Projeto

    ```
    sb100_agents/
    ├── .dockerignore        → Arquivos ignorados no build Docker
    ├── .env                 → Variáveis de ambiente (NÃO commitado)
    ├── .env.example         → Template de variáveis de ambiente
    ├── .gitignore           → Arquivos ignorados pelo Git
    ├── .gitmodules          → Submódulos Git
    ├── .python-version      → Versão do Python (3.12)
    ├── CLAUDE.md            → Instruções para Claude Code
    ├── CONTEXT.md           → Glossário de domínio da aplicação
    ├── CONTRIBUTING.md      → Guia de contribuição
    ├── Dockerfile.api       → Build Docker multi-stage
    ├── LICENSE              → Licença MIT
    ├── README.md            → Documentação principal
    ├── SETUP.md             → Guia de setup detalhado
    ├── docker-compose.yml   → Orquestração de containers
    ├── pyproject.toml       → Configuração do projeto Python
    ├── requirements.txt     → Dependências congeladas (gerado por uv)
    ├── smartb100_v2.db      → Banco SQLite (auth + conversas)
    ├── start.bat            → Script de inicialização (Windows CMD)
    ├── start.ps1            → Script de inicialização (PowerShell)
    └── uv.lock              → Lock file do gerenciador uv
    ```

    #### Arquivos-chave explicados:

    **`pyproject.toml`** — O "coração" da configuração do projeto. Define:
    - Nome do projeto (`smartb100`), versão, Python mínimo (3.12)
    - Todas as dependências (FastAPI, Ollama, Qdrant, etc.)
    - Configuração do Ruff (linter), MyPy (type-checker), Pytest (testes)
    - Cobertura de código

    **`docker-compose.yml`** — Orquestra 3 containers:
    - `qdrant` (profile `infra`) — Banco vetorial na porta 6333
    - `api` (profile `app`) — API FastAPI na porta 8000
    - `gradio` (profile `app`) — UI na porta 7860
    - Inclui healthchecks, rotação de logs, rede privada

    **`Dockerfile.api`** — Build multi-stage:
    - **Stage 1 (builder)**: Instala `build-essential` + dependências Python → cria venv
    - **Stage 2 (runtime)**: Copia só o venv pronto → imagem final leve (sem compiladores)

    **`.env.example`** — Template com TODAS as variáveis de ambiente documentadas. Categorias:
    - Qdrant (local ou remoto)
    - Modelos Ollama (chat + embeddings)
    - Configurações RAG (top_k, max_tokens, threshold)
    - APIs externas (Groq, OpenRouter)
    - JWT (chave secreta obrigatória)
    - Rate limiting

    **`start.bat` / `start.ps1`** — Scripts que automatizam:
    1. Verificam se o Docker/Ollama estão instalados
    2. Sobem o Qdrant via Docker Compose
    3. Baixam modelos Ollama se necessário
    4. Iniciam API + Gradio em janelas separadas

    ---

    ### 4.2 `api/` — Camada de API REST

    ```
    api/
    ├── __init__.py          → Descrição do módulo
    ├── dependencies.py      → Dependências compartilhadas (JWT, rate limit)
    ├── main.py              → Entry point do FastAPI
    └── routes/
        ├── __init__.py       → Descrição do módulo de rotas
        ├── auth.py           → Endpoints de autenticação
        ├── chat.py           → Endpoint principal de chat RAG
        └── health.py         → Health check
    ```

    #### `main.py` — O Ponto de Entrada

    **O que faz:** Cria e configura a aplicação FastAPI.

    Funcionalidades:
    - **CORS Middleware**: Permite que o Gradio (porta 7860) e o Swagger (porta 8000) façam requisições à API
    - **Rate Limiter**: Limita requisições por IP/usuário (via slowapi)
    - **Lifespan**: No startup, cria as tabelas do SQLite automaticamente
    - **Routers**: Registra os 3 grupos de endpoints (auth, chat, health)

    #### `dependencies.py` — Autenticação JWT Centralizada

    **O que faz:** Valida o token JWT em cada requisição protegida.

    Fluxo:
    1. Extrai o token do header `Authorization: Bearer <token>`
    2. Decodifica o JWT com a chave secreta usando algoritmo HS256
    3. Extrai o `username` do campo `sub` do payload
    4. Busca o usuário no SQLite
    5. Se qualquer passo falhar → retorna 401 Unauthorized

    Também expõe:
    - `limiter`: instância global do slowapi para rate limiting
    - `oauth2_scheme`: esquema OAuth2 para o Swagger UI

    #### `routes/auth.py` — Registro e Login

    **Endpoints:**

    | Endpoint | Método | O que faz | Rate Limit |
    |---|---|---|---|
    | `/auth/register` | POST | Cria novo usuário | 3/hora por IP |
    | `/auth/token` | POST | Login → retorna JWT | 5/15min por IP |

    **Detalhes técnicos:**
    - **Senhas**: Hash bcrypt com salt aleatório (`passlib[bcrypt]`)
    - **JWT**: Token com validade de 7 dias, algoritmo HS256
    - **Validação de username**: Regex `^[a-zA-Z0-9_-]+$`, máximo 50 chars
    - **Validação de senha**: Mínimo 8 caracteres
    - **Verificação timing-safe**: `passlib.verify()` impede ataques de timing

    #### `routes/chat.py` — O Endpoint Principal RAG

    **Endpoint:** `POST /chat` (requer JWT)

    **O que faz (pipeline completo):**

    1. **Verifica autenticação** (JWT válido)
    2. **Obtém/cria buffer de conversa** (cache LRU com TTL de 1 hora, máximo 1000 sessões)
    3. **Se modo agente habilitado:**
    - Filtra domínio (pergunta é sobre agricultura?)
    - Invoca o agente deepagents com Groq
    4. **Se modo legado:**
    - Gera embedding da pergunta (Ollama)
    - Busca chunks similares no Qdrant
    - Gera resposta adaptada ao perfil do usuário
    - (Opcional) Verifica alucinação via entropia semântica
    5. **Atualiza histórico** da conversa

    **Segurança do cache de sessão:**
    - Chave = `{user_id}:{session_id}` → impede um usuário de acessar sessão de outro (IDOR)
    - TTL de 1 hora com limpeza lazy (até 10 sessões expiradas por chamada)
    - LRU eviction quando atinge 1000 sessões
    - Thread-safe via `threading.Lock`

    **Rate limiting:**
    - Chaveado pelo `sub` do JWT (não pelo IP)
    - Assim, usuários atrás do mesmo NAT têm limites independentes
    - Configurável via `CHAT_RATE_LIMIT` (padrão: 30/minuto)

    #### `routes/health.py` — Health Check

    **Endpoint:** `GET /health`

    Retorna `{"status": "ok"}`. Não verifica dependências (Ollama, Qdrant) para evitar overhead. Usado por:
    - Docker healthchecks
    - Load balancers
    - Monitoramento

    ---

    ### 4.3 `core/` — Configuração e Schemas

    ```
    core/
    ├── __init__.py          → Exporta settings + schemas
    ├── config.py            → Classe Settings (Pydantic Settings)
    ├── ollama_clients.py    → Singletons de clientes Ollama
    └── schemas.py           → Modelos Pydantic para request/response
    ```

    #### `config.py` — Configurações do Sistema

    **O que faz:** Carrega configurações de variáveis de ambiente (`.env`) com validação forte.

    **Classe `Settings`** (herda `BaseSettings` do Pydantic):

    | Setting | Tipo | Padrão | Validação |
    |---|---|---|---|
    | `chat_model` | str | `llama3.2:3b` | — |
    | `embed_model` | str | `nomic-embed-text` | — |
    | `qdrant_url` | str | `http://localhost:6333` | — |
    | `top_k` | int | 3 | 1 ≤ x ≤ 100 |
    | `llm_max_tokens` | int | 256 | 1 ≤ x ≤ 4096 |
    | `hallucination_threshold` | float | 0.5 | 0.0 ≤ x ≤ 1.0 |
    | `verification_enabled` | bool | `true` | — |
    | `verification_provider` | enum | `groq` | `groq \| ollama \| openrouter` |
    | `entropy_num_samples` | int | 2 | ≥ 2 |
    | `jwt_secret_key` | str | — | **Obrigatório**, ≥ 32 caracteres |
    | `chat_rate_limit` | str | `30/minute` | Formato slowapi validado no boot |

    **Validações fail-fast:**
    - Se `JWT_SECRET_KEY` não existir ou tiver < 32 chars → **erro no boot** (não em runtime)
    - Se `CHAT_RATE_LIMIT` for inválido → **erro no boot**

    #### `schemas.py` — Contratos da API

    **O que faz:** Define os modelos Pydantic que formam o contrato público da API.

    | Schema | Campos | Uso |
    |---|---|---|
    | `ExpertiseLevel` | `beginner`, `intermediate`, `expert` | Enum de níveis |
    | `UserProfile` | `name`, `expertise` | Perfil do usuário |
    | `ChatRequest` | `session_id`, `question`, `profile` | Corpo da requisição `/chat` |
    | `ChatResponse` | `answer`, `hallucination_score` | Corpo da resposta |

    #### `ollama_clients.py` — Clientes Ollama Singleton

    **O que faz:** Centraliza os clientes HTTP para o Ollama com timeout configurável.

    Dois singletons thread-safe (double-checked locking):
    - `get_chat_client()` — para geração de respostas (timeout: 240s)
    - `get_embed_client()` — para embeddings (timeout: 5s)

    **Por que separar?** Embedding é rápido (< 1s), chat pode demorar minutos em CPU. Timeouts diferentes evitam que um bloqueie o outro.

    ---

    ### 4.4 `retrieval/` — Busca Vetorial

    ```
    retrieval/
    ├── __init__.py            → Exporta generate_embedding + search_context
    ├── embedder.py            → Interface de alto nível para embeddings
    ├── ollama_embeddings.py   → Chamadas Ollama com retry e truncation
    └── vector_store.py        → Busca no Qdrant (ANN)
    ```

    #### `embedder.py` — Geração de Embeddings

    **O que faz:** Converte texto em vetor de 768 dimensões usando `nomic-embed-text`.

    É uma fachada simples que delega para `ollama_embeddings.py`.

    #### `ollama_embeddings.py` — Chamadas com Resiliência

    **O que faz:** Faz a chamada real ao Ollama para gerar embeddings, com:

    - **Truncation**: Limita a 8192 caracteres (limite do modelo)
    - **Retries**: Até 4 tentativas com backoff exponencial (0.75s → 1.5s → 2.0s)
    - **Erros tratados**: `ResponseError`, `RequestError`, `ConnectionError`, `TimeoutError`

    **Por que retry?** O Ollama local no Windows pode retornar 500 ou dropar conexão sob carga. Retries com backoff reduzem falhas intermitentes.

    #### `vector_store.py` — Busca no Qdrant

    **O que faz:** Realiza busca ANN (Approximate Nearest Neighbors) no Qdrant.

    Duas funções:
    - `search_context(embedding)` → Retorna `top_k` chunks mais similares como lista de strings
    - `top_similarity(embedding)` → Retorna o score do chunk mais similar (usado pelo filtro de domínio)

    **Validação:** Rejeita embeddings com dimensão ≠ 768 antes de chamar o Qdrant.

    **Singleton thread-safe** para reutilizar a conexão TCP/HTTP.

    ---

    ### 4.5 `generation/` — Geração de Respostas com LLM

    ```
    generation/
    ├── __init__.py    → Exporta generate
    └── llm.py         → Lógica de geração + anti-injection
    ```

    #### `llm.py` — O Coração da Geração

    **O que faz:** Monta o prompt, chama o LLM via Ollama, e retorna a resposta.

    **3 System Prompts baseados no expertise:**

    | Nível | Tom | Detalhes |
    |---|---|---|
    | `beginner` | Didático, simples | Evita termos técnicos, usa exemplos práticos |
    | `intermediate` | Claro e objetivo | Termos técnicos com explicações breves |
    | `expert` | Preciso e avançado | Terminologia técnica, dados quantitativos, referências |

    **Anti-Injection (3 camadas de defesa):**

    1. **Sanitização do input**: Remove tokens de controle do modelo (`[SYSTEM]`, `[INST]`, `<<SYS>>`, `<|im_start|>`, `### System:`, etc.)
    2. **Delimitador semântico**: Envolve o contexto RAG em `[RETRIEVED DOCUMENT ...]` / `[/RETRIEVED DOCUMENT]`
    3. **Aviso no System Prompt**: Instrui o modelo a tratar documentos como dados, nunca como ordens

    **Por que tanta proteção?** Um atacante pode inserir instruções maliciosas em um PDF que será indexado no Qdrant. Quando o chunk é recuperado, ele faria parte do prompt. Sem proteção, o LLM poderia seguir instruções do atacante em vez do sistema.

    ---

    ### 4.6 `memory/` — Histórico de Conversa

    ```
    memory/
    ├── __init__.py        → Exporta ConversationBuffer
    └── conversation.py    → Buffer FIFO com deque
    ```

    #### `conversation.py` — Buffer de Conversa FIFO

    **O que faz:** Mantém uma janela deslizante das últimas N mensagens (padrão: 10 turnos).

    **Como funciona:**
    - Usa um `deque` do Python com `maxlen`
    - Quando atinge o limite, descarta automaticamente as mensagens mais antigas
    - Cada mensagem tem `role` ("user" ou "assistant") e `content`
    - Valida que o role e content não são vazios

    **Por que FIFO com limite?** 
    - Evita que o prompt cresça indefinidamente (LLMs têm limite de contexto)
    - Mantém o histórico recente sem consumir memória infinita
    - Simples e previsível

    ---

    ### 4.7 `verification/` — Detecção de Alucinação

    ```
    verification/
    ├── __init__.py    → Exporta compute_entropy_score + evaluate
    ├── entropy.py     → Cálculo de entropia semântica
    └── gate.py        → Gate de verificação com retry
    ```

    #### `entropy.py` — Entropia Semântica

    **O que faz:** Implementa o paper "Semantic Uncertainty" (Farquhar et al., 2023) para detectar alucinações.

    **Algoritmo passo a passo:**

    1. **Gera N amostras** da mesma pergunta (padrão: 2) via provider configurado
    2. **Computa embeddings** de cada amostra
    3. **Agrupa por similaridade** (threshold 0.85) — respostas parecidas vão pro mesmo cluster
    4. **Calcula entropia de Shannon normalizada** sobre os clusters:
    - Se todas as respostas são parecidas → 1 cluster → entropia = 0.0 → **confiável**
    - Se cada resposta é diferente → N clusters → entropia alta → **possível alucinação**

    **Tolerância a falhas:** Se uma amostra falhar, continua com as que conseguiu. Só propaga erro se TODAS falharem.

    #### `gate.py` — Gate de Verificação

    **O que faz:** Orquestra geração + verificação com retry automático.

    **Lógica:**
    1. Gera resposta via LLM
    2. Computa score de entropia
    3. Se score ≤ threshold (0.5) → retorna resposta ✅
    4. Se score > threshold → regenera (até 2 tentativas)
    5. Se todas tentativas falharam → retorna mensagem fallback
    6. Se a verificação em si falhar → retorna resposta com score neutro (0.5)

    **Princípio:** A verificação é **opcional** — sua falha nunca deve bloquear a resposta. Erros de geração são reais (503); erros de verificação degradam graciosamente.

    ---

    ### 4.8 `database/` — Banco de Dados e Indexação de PDFs

    ```
    database/
    ├── db.py                → Engine SQLAlchemy + sessão
    ├── models.py            → Modelos ORM (User, Conversation, Message)
    └── semantic_chunker.py  → Pipeline de indexação de PDFs
    ```

    #### `db.py` — Configuração do SQLAlchemy

    **O que faz:** Configura o engine e sessão SQLAlchemy para SQLite.

    **Hardening:**
    - `timeout=10` na conexão (evita `database is locked`)
    - `PRAGMA foreign_keys=ON` ativado via listener (necessário para CASCADE funcionar no SQLite)
    - `get_db()` faz rollback explícito em exceção antes de fechar a sessão
    - Detecção de diretório: se `smartb100_v2.db` é um diretório (bug do Docker), lança erro claro

    #### `models.py` — Modelos do Banco

    **3 tabelas:**

    | Modelo | Campos | Relação |
    |---|---|---|
    | `User` | `id`, `username`, `hashed_password`, `created_at` | 1:N com Conversation |
    | `Conversation` | `id`, `user_id`, `title`, `created_at` | N:1 com User, 1:N com Message |
    | `Message` | `id`, `conversation_id`, `role`, `content`, `is_hallucinated`, `created_at` | N:1 com Conversation |

    **CASCADE**: Deletar um User deleta suas Conversations e Messages automaticamente.

    #### `semantic_chunker.py` — O Indexador de PDFs

    **O que faz:** Transforma PDFs agrícolas em chunks semânticos indexados no Qdrant.

    **Pipeline (6 etapas):**

    ```
    PDF → Texto → Sentenças → Embeddings → Chunks Semânticos → Qdrant
    ```

    1. **Extração de texto**: PyMuPDF (`fitz`) lê todas as páginas do PDF
    2. **Divisão em sentenças**: Regex que funciona para português e inglês
    3. **Embeddings por sentença**: Gera vetor de 768 dim para cada sentença
    4. **Chunking semântico**: Agrupa sentenças por similaridade:
    - Compara cada sentença com a média do chunk atual
    - Se similaridade < 0.75 → novo chunk
    - Respeita min 3 e max 20 sentenças por chunk
    5. **Embedding do chunk**: Média dos embeddings das sentenças
    6. **Upsert no Qdrant**: Salva com payload (`text`, `source_file`, `num_sentences`)

    **CLI:** 
    ```bash
    python database/semantic_chunker.py index ./archives/
    python database/semantic_chunker.py search "plantio de soja"
    ```

    ---

    ### 4.9 `agent/` — Camada Agêntica

    ```
    agent/
    ├── __init__.py    → Exporta todas as funções públicas
    ├── factory.py     → Cria o agente deepagents + Groq
    ├── intent.py      → Filtro de domínio agrícola
    ├── prompt.py      → System prompt do agente
    ├── runner.py      → Executor síncrono do agente
    └── tools.py       → Ferramenta search_corpus para o agente
    ```

    #### `factory.py` — Fábrica do Agente

    **O que faz:** Cria o agente usando `deepagents` (wrapper sobre LangGraph) com modelo Groq hospedado.

    **Componentes:**
    - **Modelo**: `ChatGroq` (Groq API gratuita)
    - **Tools**: `search_corpus` (busca no corpus)
    - **System Prompt**: Instruções do assistente agrícola + anti-injection

    #### `intent.py` — Filtro de Domínio

    **O que faz:** Decide se a pergunta é sobre agricultura **antes** de rodar o agente.

    **Como funciona:**
    1. Gera embedding da pergunta
    2. Busca o chunk mais similar no corpus (top-1)
    3. Se o score de similaridade < `intent_threshold` (0.3) → **fora do domínio**
    4. Retorna mensagem: "Só respondo sobre temas agrícolas cobertos pela base de documentos."

    **Fail-open:** Em caso de erro (Qdrant offline, embedding falha), trata como "in domain" e deixa o agente lidar.

    **Por que usar score do corpus ao invés de classificador?**
    - Mais barato (1 embedding + 1 query vs. chamada LLM)
    - Reutiliza a infraestrutura existente
    - Proxy de cobertura: se o corpus não tem nada parecido, não vale a pena responder

    #### `runner.py` — Executor do Agente

    **O que faz:** Invoca o agente de forma síncrona e extrai resposta + contexto.

    **Fluxo:**
    1. Monta input com histórico + pergunta sanitizada + preamble de expertise
    2. Chama `graph.invoke(...)` — síncrono
    3. Extrai a última `AIMessage` como resposta
    4. Coleta os `ToolMessage` do `search_corpus` como contexto
    5. Retorna `AgentOutcome(answer, context)`

    #### `tools.py` — Ferramenta de Busca

    **O que faz:** Expõe o retrieval como ferramenta `@tool` do LangChain.

    Quando o agente decide buscar informação:
    1. Gera embedding da query
    2. Busca chunks no Qdrant
    3. Sanitiza e retorna o contexto delimitado
    4. Se falhar → retorna mensagem de erro (não crash)

    ---

    ### 4.10 `ui/` — Interface Gradio

    ```
    ui/
    ├── __init__.py    → Package marker
    └── chat_ui.py     → Interface completa (609 linhas)
    ```

    #### `chat_ui.py` — Interface Web de Chat

    **O que faz:** Interface web completa que consome a API via HTTP.

    **Funcionalidades:**
    - **Login**: Formulário de credenciais → troca por JWT via `POST /auth/token`
    - **Chat**: Envia pergunta com `Authorization: Bearer <token>`
    - **Perfil**: Configuração de nome e nível de expertise
    - **Score visual**: Badge colorido mostrando risco de alucinação:
    - 🟢 Verde (< 0.3): Baixo risco
    - 🟡 Amarelo (0.3 - 0.6): Risco moderado
    - 🔴 Vermelho (≥ 0.6): Alto risco
    - **Sessão**: Cada aba do browser tem sessão independente (estado `gr.State`)
    - **Retry automático**: Backoff exponencial para erros 503/504/timeout
    - **Loading state**: Placeholder "Processando..." enquanto espera a API

    **Estado por browser:**
    ```python
    {"token": str | None, "session_id": str, "api_url": str}
    ```

    **Segurança:**
    - Nunca exibe URLs ou detalhes técnicos ao usuário (só loga)
    - HTML escapado por defesa em profundidade
    - Token limpo do estado em caso de 401

    ---

    ### 4.11 `eval/` — Pipeline de Avaliação

    ```
    eval/
    ├── README.md                → Documentação do pipeline
    ├── __init__.py              → Package marker
    ├── _utils.py                → Utilitários compartilhados
    ├── collect_references.py    → Coleta respostas de referência
    ├── generate_questions.py    → Gera perguntas a partir dos documentos
    ├── judge.py                 → Julgamento automático por LLM
    ├── report.py                → Gera relatório e amostra humana
    ├── run_evaluation.py        → Roda perguntas contra o SmartB100
    ├── dataset/                 → Datasets de perguntas e referências
    └── results/                 → Resultados das avaliações
    ```

    **Pipeline de 5 etapas:**

    ```
    PDFs → [1] Gera Perguntas → [2] Coleta Referências → [3] Roda Avaliação → [4] Julgamento LLM → [5] Relatório
    ```

    1. **`generate_questions.py`**: Extrai perguntas agrícolas dos PDFs usando LLM (Groq ou Ollama)
    2. **`collect_references.py`**: Coleta respostas "gold standard" de modelos de referência
    3. **`run_evaluation.py`**: Envia cada pergunta ao SmartB100 via `POST /chat` (autenticado)
    4. **`judge.py`**: Um LLM juiz compara resposta do SmartB100 vs. referência → score 0-10 + veredicto
    5. **`report.py`**: Gera relatório markdown + amostra CSV para validação humana

    **Reprodutibilidade:** `random.seed(42)`, session_id único por pergunta, perfil fixo.

    ---

    ### 4.12 `tests/` — Testes Automatizados

    ```
    tests/
    ├── conftest.py                    → Fixtures compartilhadas
    ├── test_agent.py                  → Testes do agente deepagents
    ├── test_auth.py                   → Testes de autenticação
    ├── test_chat_concurrency.py       → Testes de concorrência
    ├── test_chat_rate_limit.py        → Testes de rate limiting
    ├── test_chat_ui.py                → Testes da interface Gradio
    ├── test_ci_submodule_checkout.py  → Testes de CI
    ├── test_claude_md_paths.py        → Testes de paths do Claude
    ├── test_compose_config.py         → Testes do docker-compose
    ├── test_config.py                 → Testes de configuração
    ├── test_conversation.py           → Testes do buffer de conversa
    ├── test_db.py                     → Testes do banco de dados
    ├── test_embedder.py               → Testes de embeddings
    ├── test_eval.py                   → Testes do pipeline de avaliação
    ├── test_integration.py            → Testes de integração
    ├── test_intent.py                 → Testes do filtro de domínio
    ├── test_llm.py                    → Testes de geração LLM
    ├── test_ollama_clients.py         → Testes dos clientes Ollama
    ├── test_pytest_config.py          → Testes da config do pytest
    ├── test_schemas.py                → Testes dos schemas
    ├── test_vector_store.py           → Testes do vector store
    └── test_verification.py           → Testes da verificação
    ```

    **Stats:** ~205 testes, ~83% de cobertura

    **Marker especial:** `@pytest.mark.requires_infra` — testes que precisam de Ollama/Qdrant rodando. Excluídos do CI.

    **Ferramentas:**
    - **pytest** — runner de testes
    - **pytest-cov** — relatório de cobertura
    - **ruff** — linter e formatter
    - **mypy --strict** — type checking rigoroso

    ---

    ### 4.13 `scripts/` — Scripts Utilitários

    ```
    scripts/
    └── ingest.py    → Wrapper simplificado do semantic_chunker
    ```

    **`ingest.py`** — Script de ingestão de PDFs. Delega para `semantic_chunker.py` com interface simplificada:
    ```bash
    python scripts/ingest.py ./archives/
    ```

    ---

    ### 4.14 `docs/` — Documentação Técnica

    ```
    docs/
    ├── roadmap.md   → Roadmap de migração agêntica (Waves A-D)
    └── adr/         → Architecture Decision Records (10 ADRs)
        ├── 0001-modular-monolith.md
        ├── 0002-semantic-entropy-hallucination-score.md
        ├── 0003-local-first-inference-via-ollama.md
        ├── 0004-multi-provider-verification-dispatch.md
        ├── 0005-synchronous-chat-handler.md
        ├── 0006-bcrypt-jwt-auth-gate.md
        ├── 0007-sqlite-persistence.md
        ├── 0008-deepagents-orchestration-substrate.md
        ├── 0009-groq-agent-model.md
        └── 0010-domain-gate-retrieval-score.md
    ```

    **`roadmap.md`** — Organiza o trabalho futuro em 4 Waves:

    | Wave | Objetivo |
    |---|---|
    | **A — Agentic Core** | `/chat` roda via agente deepagents + Groq |
    | **B — Retrieval Quality** | Citações, score threshold, busca híbrida, reranking |
    | **C — Verification & Trust** | Verificação por claim, sinais de qualidade |
    | **D — Conversation UX** | Histórico durável, streaming SSE, feedback |

    ---

    ### 4.15 `.github/` — CI/CD e Templates

    ```
    .github/
    ├── ISSUE_TEMPLATE/              → Templates de issue
    ├── PULL_REQUEST_TEMPLATE.md     → Template de PR
    └── workflows/
        ├── ci.yml                   → CI principal (lint + typecheck + test)
        ├── claude-auto.yml          → Automação Claude Code
        ├── claude-respond.yml       → Claude responde issues/PRs
        └── docker-build.yml         → Build e push da imagem Docker
    ```

    #### `ci.yml` — Pipeline de CI

    **4 jobs paralelos:**
    1. **validate-requirements**: Verifica sync entre `uv.lock` e `requirements.txt`
    2. **lint**: `ruff check .` + `ruff format --check .`
    3. **typecheck**: `mypy retrieval/ generation/ memory/ --strict`
    4. **test**: `pytest tests/ -m "not requires_infra"` com cobertura

    **Triggers:** Push em `main`/`dev`, PRs para `main`

    ---

    ### 4.16 `archives/` — PDFs Fonte

    ```
    archives/
    └── smart_boletim.pdf    → Boletim agrícola (~8MB)
    ```

    O documento base que alimenta o sistema. Contém informações técnicas sobre agricultura brasileira que são indexadas e consultadas pelo RAG.

    ---

    ## 5. Fluxo Completo de uma Requisição

    ```
    [Usuário digita pergunta no Gradio]
                        ↓
    [1] Gradio POST /auth/token → recebe JWT
    [2] Gradio POST /chat (com Bearer token)
                        ↓
    [3] FastAPI valida JWT (dependencies.py)
                        ↓
    [4] Rate limit check (por usuário JWT)
                        ↓
    [5] Obtém/cria ConversationBuffer (LRU cache, TTL 1h)
                        ↓
    [6] Se AGENT_ENABLED:
        ├─ classify_domain() → embed pergunta → top_similarity no Qdrant
        ├─ Se fora do domínio → "Só respondo sobre agricultura"
        └─ invoke_agent() → deepagents + Groq + search_corpus tool
        
        Se LEGADO:
        ├─ generate_embedding(pergunta) → Ollama nomic-embed-text → vetor[768]
        ├─ search_context(vetor) → Qdrant → top_k chunks
        ├─ context = join(chunks)
        └─ Se VERIFICATION_ENABLED:
        │   ├─ generate(pergunta, context, history, profile) → Ollama llama3.2:3b → resposta
        │   ├─ compute_entropy_score(pergunta, context) → gera N amostras → clusteriza → Shannon
        │   ├─ Se score ≤ 0.5 → retorna
        │   └─ Se score > 0.5 → regenera (até 2x) → fallback
        └─ Se VERIFICATION_DISABLED:
            └─ generate() → resposta com score=0.0
                        ↓
    [7] buffer.add("user", pergunta)
        buffer.add("assistant", resposta)
                        ↓
    [8] Retorna ChatResponse { answer, hallucination_score }
                        ↓
    [9] Gradio exibe resposta + badge colorido do score
    ```

    ---

    ## 6. Decisões Arquiteturais (ADRs)

    | # | Decisão | Alternativa rejeitada | Motivo |
    |---|---|---|---|
    | 0001 | Monolito modular | Microserviço por etapa RAG | Pipeline síncrono, modelo compartilhado |
    | 0002 | Entropia semântica | Classificador binário / LLM juiz | Score contínuo sem dados rotulados |
    | 0003 | Ollama local | Embeddings hospedados | Offline, gratuito, espaço de embedding estável |
    | 0004 | Multi-provider | OpenAI only | Remove dependência de API paga |
    | 0005 | Handler síncrono | `async def` handler | Threadpool mantém event loop livre |
    | 0006 | bcrypt + JWT | Session cookies / API keys | Stateless, revogável |
    | 0007 | SQLite | PostgreSQL | Zero-ops em single-node |
    | 0008 | deepagents + LangGraph | Loop manual / LangGraph puro | Planejamento, sub-agentes, filesystem built-in |
    | 0009 | Groq hospedado | LLM local maior / Claude | Sem GPU local, reutiliza provider |
    | 0010 | Gate de domínio via corpus | Classificador few-shot / LLM juiz | Barato, proxy de cobertura |

    ---

    ## 7. Como Rodar o Projeto

    ### Pré-requisitos:
    - Python 3.12+
    - Docker Desktop (para Qdrant)
    - Ollama instalado

    ### Passos:

    ```bash
    # 1. Clonar e instalar
    git clone https://github.com/LukeSantossz/sb100_agents.git
    cd sb100_agents
    uv sync                                    # instala dependências

    # 2. Configurar
    cp .env.example .env                       # ajustar JWT_SECRET_KEY obrigatoriamente

    # 3. Baixar modelos
    ollama pull llama3.2:3b
    ollama pull nomic-embed-text

    # 4. Subir Qdrant
    docker compose --profile infra up -d

    # 5. Indexar documentos (primeira vez)
    .venv\Scripts\python.exe database/semantic_chunker.py index ./archives/

    # 6. Iniciar API
    .venv\Scripts\python.exe -m uvicorn api.main:app --reload

    # 7. (Opcional) Iniciar Gradio
    .venv\Scripts\python.exe ui/chat_ui.py
    ```

    ### Atalho Windows:
    ```powershell
    .\start.ps1    # ou start.bat
    ```

    ### Verificar:
    ```bash
    curl http://localhost:6333/healthz    # Qdrant
    curl http://localhost:8000/health     # API
    ```

    ---

    ## 8. Glossário de Termos

    | Termo | O que é |
    |---|---|
    | **RAG** | Retrieval-Augmented Generation — pipeline que busca documentos antes de gerar resposta |
    | **Chunk** | Pedaço de um PDF cortado por similaridade semântica |
    | **Embedding** | Vetor numérico (768 dims) que representa o significado de um texto |
    | **Context** | Chunks recuperados que servem de base para a resposta |
    | **Hallucination Score** | Nota 0.0-1.0 indicando confiança na resposta (0 = confiável) |
    | **Semantic Entropy** | Método de detecção de alucinação por concordância entre múltiplas respostas |
    | **Verification Gate** | Componente que gera + verifica + faz retry automático |
    | **Neutral Score** | 0.5 retornado quando a verificação falha (degradação graciosa) |
    | **ConversationBuffer** | Janela FIFO das últimas N mensagens da sessão |
    | **ANN** | Approximate Nearest Neighbors — algoritmo de busca vetorial rápida |
    | **JWT** | JSON Web Token — token de autenticação stateless |
    | **bcrypt** | Algoritmo de hash para senhas com salt aleatório |
    | **deepagents** | Biblioteca que cria agentes sobre LangGraph |
    | **LangGraph** | Framework para criar agentes como grafos de estado |
    | **Groq** | Provedor de inferência LLM com tier gratuito |
    | **Qdrant** | Banco de dados vetorial open-source |
    | **Ollama** | Servidor que roda LLMs localmente |
    | **FastAPI** | Framework web Python para APIs REST |
    | **Gradio** | Biblioteca Python para interfaces web de ML |
    | **Pydantic** | Biblioteca de validação de dados com types |
    | **SQLAlchemy** | ORM para Python |
    | **slowapi** | Rate limiting para FastAPI |
    | **ruff** | Linter + formatter Python ultra-rápido |
    | **mypy** | Type checker estático para Python |

    ---

    > **Nota:** Este documento foi gerado após leitura completa de todos os arquivos do projeto. Qualquer dúvida, pergunte ao time do Squad 5 ou consulte os ADRs em `docs/adr/`.
