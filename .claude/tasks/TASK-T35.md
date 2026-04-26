# TASK-T35 — Corrigir Badge de Coverage no README

- **Status:** concluída
- **Modo:** desenvolvimento
- **Complexidade:** patch
- **Data de criação:** 2026-04-25

## Objetivo

Atualizar o badge de coverage no `README.md` para refletir o valor real configurado no projeto (25%).

## Contexto

Revisão de codebase identificou divergência entre documentação e configuração:
- `README.md:6` exibe badge com 80% de coverage
- `pyproject.toml:112` define threshold real de 25%

Isso é documentação enganosa que pode criar expectativas incorretas sobre a qualidade do projeto.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 7.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `README.md`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (apenas documentação)

## Critérios de Aceite

- [x] Badge atualizado para `coverage-25%25-yellow` (amarelo para indicar baseline)
- [ ] ~~Ou remover badge estático e usar badge dinâmico do CI (preferível)~~ — mantido estático por simplicidade
- [x] Comentário no README sobre meta de aumentar coverage

## Restrições

- Manter honestidade na documentação
- Não alterar o threshold em pyproject.toml nesta task

## Referências

- `README.md:6`
- `pyproject.toml:112`
- [Shields.io](https://shields.io/)

## Log de Andamento

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| —    | —      | —              | —               |

## Resultado

- **Data de conclusão:** 2026-04-25
- **Branch:** fix/TASK-T35-coverage-badge
- **Commit(s):** 8b44df7
- **Avaliação pós-implementação:** aprovado
- **Observações:** Badge estático mantido (badge dinâmico seria escopo separado). Nota de cobertura adicionada em Known Issues.
