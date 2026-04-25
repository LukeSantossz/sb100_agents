### TASK-T25
- **Status:** em andamento
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-24
- **Sprint:** Backlog
- **Prioridade:** Alta

#### Objetivo (!obrigatório)
Criar SETUP.md com instruções de execução em dois modos (Qdrant local via Docker e Qdrant remoto via ZeroTier), permitindo setup operacional em menos de 15 minutos.

#### Contexto (!obrigatório)
Qualquer membro da equipe deve conseguir clonar o repositório e ter o sistema SB100-S5 operacional rapidamente, com suporte a dois modos de execução do Qdrant. Credenciais do servidor remoto a serem fornecidas fora do repositório.

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** `SETUP.md`, `.env.example`, `core/config.py`, `retrieval/vector_store.py`, `database/semantic_chunker.py`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** suporte a QDRANT_API_KEY adicionado para modo remoto autenticado

**Escopo expandido (2026-04-25):** Além da documentação, adicionado suporte a `QDRANT_API_KEY` no código para permitir conexão com servidores Qdrant autenticados. Mudança retrocompatível — API key é opcional (None por padrão).

#### Critérios de Aceite (!obrigatório)
- [ ] `.env.example` versionado com ambos os blocos documentados (local e remoto)
- [ ] Fluxo completo reproduzível nos dois modos sem consultar outros documentos
- [ ] Nenhuma credencial real presente no repositório
- [ ] Script de ingestão referenciado ou criado como sub-tarefa se não existir
- [ ] Estrutura do documento cobre: (1) Pré-requisitos (Python 3.11+, Docker, Ollama, ZeroTier para remoto), (2) Modelos Ollama (`ollama pull llama3.1:8b` e `ollama pull nomic-embed-text`), (3) Configuração do `.env`, (4) Ingestão do documento base agrícola, (5) Inicialização da API: `uvicorn api.main:app --reload`, (6) Exemplos de curl, (7) Acesso à interface Gradio
- [ ] Modo Local: variáveis `QDRANT_HOST=localhost`, `QDRANT_PORT=6333`, `QDRANT_COLLECTION_NAME=sb100_knowledge`
- [ ] Modo Local com Docker Compose: `docker compose --profile infra up -d`
- [ ] Modo Remoto: variáveis com `QDRANT_HOST=<REMOTE_HOST_ZEROTIER>`, `QDRANT_API_KEY=<SOLICITAR_AO_TECH_LEAD>`
- [ ] Commit: `docs: add SETUP.md with local and remote Qdrant modes`

#### Restrições
- Depende de: T18 — README base atualizado; T19 — estrutura de diretórios correta; T24-UI — UI referenciada como forma de teste
- Verificar antes da execução se o script de ingestão já existe em `database/`. Se não existir, criar issue rastreando a lacuna

#### Referências
- Repositório: https://github.com/LukeSantossz/sb100_agents

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-24 | — | Task criada. Dois modos de execução definidos | pendente |
| 2026-04-25 | 1 | Reconhecimento: .env.example existe, SETUP.md não existe, scripts de ingestão ok | em andamento |
| 2026-04-25 | 1 | Criado SETUP.md, atualizado .env.example, adicionado suporte QDRANT_API_KEY em config/vector_store/chunker | validando |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** docs/TASK-T25-setup-guide
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Observações:** [notas relevantes]

---
