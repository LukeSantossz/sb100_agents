# TASK-T36 — Remover Módulo Duplicado semantic_entropy

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-25

## Objetivo

Remover o diretório `semantic_entropy/` que é duplicata não utilizada do módulo `verification/`.

## Contexto

Revisão de codebase identificou dois módulos com funcionalidade similar:
- `verification/` — módulo ativo, usado pelo código em `api/routes/chat.py`
- `semantic_entropy/` — módulo inativo, marcado como duplicado no `.gitignore`

O `.gitignore` contém comentário: "Duplicate verification module (to be consolidated)".

A presença de código morto causa confusão sobre qual módulo usar e aumenta a carga de manutenção.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 8.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `semantic_entropy/` (diretório a ser removido)
  - `.gitignore` (remover comentário sobre consolidação)
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (módulo não é importado)

## Critérios de Aceite

- [ ] Diretório `semantic_entropy/` removido do repositório
- [ ] Nenhum import quebrado (verificar com `ruff check .`)
- [ ] Comentário sobre consolidação removido do `.gitignore`
- [ ] Testes continuam passando

## Restrições

- Verificar que nenhum código importa de `semantic_entropy` antes de remover
- Manter backup local temporário caso haja funcionalidade única não migrada

## Referências

- `api/routes/chat.py` — confirmar que importa de `verification.gate`
- `.gitignore` — comentário sobre duplicação
- `pyproject.toml:41` — `semantic_entropy*` já excluído de packages

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
