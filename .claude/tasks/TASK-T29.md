# TASK-T29 — Alinhar CHAT_MODEL em Todos os Arquivos

- **Status:** concluída
- **Modo:** desenvolvimento
- **Complexidade:** patch
- **Data de criação:** 2026-04-25

## Objetivo

Sincronizar o valor de `CHAT_MODEL` em todos os arquivos de configuração e documentação para eliminar divergência.

## Contexto

Revisão de codebase identificou que o modelo de chat está definido com valores diferentes em múltiplos locais:
- `core/config.py` (default): `llama3.2:3b`
- `.env.example`: `llama3.1:8b`
- `start.bat` (pull): `llama3.2:3b`
- `docker-compose.yml` (env): `llama3.1:8b`
- `README.md`: `llama3.2:3b`

Se o usuário copiar `.env.example` → `.env`, o sistema esperará `llama3.1:8b`, mas `start.bat` baixa apenas `llama3.2:3b`, causando erro de modelo não encontrado.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 1.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `.env.example`
  - `docker-compose.yml`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (apenas alinhamento de configuração)

## Critérios de Aceite

- [ ] Todos os arquivos usam o mesmo modelo default: `llama3.2:3b`
- [ ] `.env.example` atualizado para `CHAT_MODEL=llama3.2:3b`
- [ ] `docker-compose.yml` atualizado para `CHAT_MODEL=llama3.2:3b`
- [ ] Comentário em `.env.example` menciona `llama3.1:8b` como alternativa para mais recursos

## Restrições

- Manter `llama3.2:3b` como default (mais leve, menor barreira de entrada)
- Não alterar `core/config.py` (já está correto)
- Não alterar `README.md` (já está correto)

## Referências

- [Ollama Models](https://ollama.com/library)
- Relatório de revisão em `.claude/instructions.md` Seção 9

## Log de Andamento

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-25 | 1 | Alterado .env.example e docker-compose.yml | concluída |

## Resultado

- **Data de conclusão:** 2026-04-25
- **Branch:** fix/TASK-T29-align-chat-model
- **Commit(s):** bef939a
- **PR:** [#29](https://github.com/LukeSantossz/sb100_agents/pull/29)
- **Avaliação pós-implementação:** aprovado
- **Observações:** Alinhamento para llama3.2:3b como default em todos os arquivos
