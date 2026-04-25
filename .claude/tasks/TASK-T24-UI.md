### TASK-T24-UI
- **Status:** em andamento
- **Modo:** desenvolvimento
- **Complexidade:** major
- **Data de criação:** 2026-04-24
- **Sprint:** Backlog
- **Prioridade:** Média
- **⚠ Nota:** Este ID conflita com T24 (auditoria). Renomear no board.

#### Objetivo (!obrigatório)
Criar interface de chat funcional com Gradio que consuma o endpoint POST /chat e permita demonstrar e testar interativamente todas as capacidades do agente SB100-S5, incluindo refatoração do docker-compose.yml.

#### Contexto (!obrigatório)
A interface deve expor: envio de perguntas em linguagem natural, configuração interativa do UserProfile (tipo de produtor, cultura, região), exibição do hallucination_score, controle de session_id com reset, e histórico de conversa via gr.ChatInterface.

Escopo expandido em 2026-04-24: inclui refatoração do docker-compose.yml com profiles `infra` e `app`, remoção de serviços fora do MVP (frontend React, nginx, ollama-pull) e adição do serviço gradio.

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:**
  - `sb100_agents/ui/chat_ui.py` — interface Gradio
  - `docker-compose.yml` — refatoração com profiles
  - `pyproject.toml` — adicionar `gradio>=4.0` nas dependencies
  - `requirements.txt` — regenerar via `uv export --frozen --no-dev -o requirements.txt`
- **Dependências necessárias:** `gradio>=4.0`; adicionar `"ui*"` ao bloco `tool.setuptools.packages.find.include`
- **Impacto em funcionalidades existentes:** docker-compose.yml será reestruturado — serviços `frontend`, `nginx`, `ollama-pull` serão removidos

#### Critérios de Aceite (!obrigatório)
- [ ] Enviar uma pergunta agrícola com perfil configurado e receber resposta
- [ ] Visualizar o `hallucination_score` na interface
- [ ] Resetar sessão e iniciar nova conversa
- [ ] Interface inicializável com `python ui/chat_ui.py` ou via `docker compose --profile app`
- [ ] `docker-compose.yml` sem referências a arquivos não versionados
- [ ] Profile `infra` sobe apenas `qdrant` (:6333) + `ollama` (:11434)
- [ ] Profile `app` sobe `api` (:8000) + `gradio` (:7860)
- [ ] `docker compose --profile infra up -d` funciona isoladamente
- [ ] `docker compose --profile infra --profile app up -d` sobe tudo
- [ ] Serviços removidos: `frontend` (React), `nginx` (sem config versionada), `ollama-pull` (movido para SETUP.md como passo manual)
- [ ] `pyproject.toml` e `requirements.txt` com `gradio>=4.0` incluído
- [ ] Commit: `feat(ui): add Gradio chat interface and refactor docker-compose with profiles`

#### Restrições
- Depende de: T18 — README atualizado (contratos do ChatResponse documentados); T16 — teste e2e (API estável)
- Bloqueia: T25 — Guia de Setup (a UI e os profiles do compose são referenciados no documento)
- Stack: Gradio com `gr.ChatInterface` e componentes auxiliares. Interface como processo separado, consumindo a API FastAPI via `requests` ou `httpx`

#### Referências
- Gradio docs: https://www.gradio.app/docs

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-24 | — | Task criada. Stack Gradio definida. Escopo expandido com refatoração docker-compose | pendente |
| 2026-04-25 | 1 | Implementação completa: ui/chat_ui.py criado, docker-compose.yml refatorado com profiles infra/app, pyproject.toml e requirements.txt atualizados com gradio>=4.0. Ruff check OK, 18 testes passando. | em andamento |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** feat/TASK-T24UI-gradio-interface
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Observações:** [notas relevantes]

---
