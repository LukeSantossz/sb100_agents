# TASK-T32 — Remover Ollama do Docker e Documentar Uso Local Exclusivo

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-25

## Objetivo

Remover o serviço Ollama do `docker-compose.yml` e documentar que Ollama deve ser executado **apenas localmente**.

## Contexto

Revisão de codebase identificou ambiguidade:
- `docker-compose.yml` define serviço Ollama no profile `infra`
- `start.bat` e `start.ps1` assumem Ollama instalado localmente (via PATH)
- `README.md` instrui `ollama pull` como comando local
- O código conecta a `localhost:11434` por default

A presença do Ollama no docker-compose causa confusão e potencial conflito de porta. Decisão: **Ollama roda apenas localmente**.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 4.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `docker-compose.yml` (remover serviço ollama e volume)
  - `README.md` (atualizar documentação)
  - `SETUP.md` (atualizar documentação)
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** Usuários que usavam Ollama via Docker precisarão instalar localmente

## Critérios de Aceite

- [ ] Serviço `ollama` removido do `docker-compose.yml`
- [ ] Volume `ollama_data` removido do `docker-compose.yml`
- [ ] Dependência `ollama` removida do serviço `api` em docker-compose
- [ ] `README.md` seção "Prerequisites" enfatiza instalação local do Ollama
- [ ] `SETUP.md` atualizado para refletir uso local exclusivo
- [ ] Nenhuma referência a Ollama Docker na documentação

## Restrições

- Manter o serviço Qdrant no docker-compose (apenas Ollama é removido)
- Profile `infra` passa a conter apenas Qdrant

## Referências

- `docker-compose.yml:20-30`
- `start.bat:6-14`
- [Ollama installation](https://ollama.com)

## Log de Andamento

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| —    | —      | —              | —               |

## Resultado

- **Data de conclusão:** —
- **Branch:** —
- **Commit(s):** —
- **Avaliação pós-implementação:** —
- **Observações:** —
