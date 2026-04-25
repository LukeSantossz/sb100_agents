# TASK-T33 — Refatorar Caminho do Banco de Dados para Usar Pathlib

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-25

## Objetivo

Substituir a navegação frágil de diretórios em `database/db.py` por `pathlib.Path` para maior robustez e legibilidade.

## Contexto

Revisão de codebase identificou que `database/db.py:8-10` usa navegação relativa frágil:
```python
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "smartb100_v2.db"
)
```

Isso navega 3 níveis acima de `database/db.py` para encontrar a raiz. Se a estrutura de pastas mudar ou o arquivo for movido, o caminho quebra silenciosamente.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 5.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `database/db.py`
- **Dependências necessárias:** nenhuma (pathlib é stdlib)
- **Impacto em funcionalidades existentes:** nenhum (mesmo comportamento, código mais robusto)

## Critérios de Aceite

- [ ] `database/db.py` usa `pathlib.Path` em vez de `os.path`
- [ ] Caminho calculado como `Path(__file__).resolve().parents[2] / "smartb100_v2.db"`
- [ ] Testes existentes continuam passando
- [ ] Banco de dados criado no mesmo local de antes

## Restrições

- Manter o mesmo caminho final (`./smartb100_v2.db` na raiz do projeto)
- Não adicionar configuração via Settings nesta task (pode ser task futura)

## Referências

- `database/db.py:8-10`
- [pathlib documentation](https://docs.python.org/3/library/pathlib.html)

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
