# TASK-T30 — Alinhar COLLECTION_NAME entre config.py e .env.example

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** patch
- **Data de criação:** 2026-04-25

## Objetivo

Sincronizar o nome da coleção Qdrant entre `core/config.py` e `.env.example` para evitar busca em coleção inexistente.

## Contexto

Revisão de codebase identificou divergência no nome da coleção:
- `core/config.py` (default): `archives_v2`
- `.env.example`: `sb100_knowledge`

Se o usuário indexar PDFs sem `.env`, a coleção será `archives_v2`. Se depois criar `.env` baseado no template, buscará em `sb100_knowledge` (que estará vazia), resultando em respostas sem contexto.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 2.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `.env.example`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (apenas alinhamento de configuração)

## Critérios de Aceite

- [ ] `.env.example` atualizado para `COLLECTION_NAME=archives_v2`
- [ ] Comentário explicando a convenção de nomenclatura

## Restrições

- Manter `archives_v2` como nome padrão (já em uso no código)
- Não alterar `core/config.py` (já está correto)

## Referências

- `core/config.py:42`
- Relatório de revisão em `.claude/instructions.md` Seção 9

## Log de Andamento

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-25 | 1 | Alterado .env.example COLLECTION_NAME para archives_v2 | concluída |

## Resultado

- **Data de conclusão:** 2026-04-25
- **Branch:** fix/TASK-T30-align-collection-name
- **Commit(s):** pendente
- **Avaliação pós-implementação:** aprovado
- **Observações:** Alinhamento com default de core/config.py
