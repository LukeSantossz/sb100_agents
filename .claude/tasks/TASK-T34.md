# TASK-T34 — Substituir datetime.utcnow() por datetime.now(UTC)

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** patch
- **Data de criação:** 2026-04-25

## Objetivo

Substituir uso deprecado de `datetime.utcnow()` por `datetime.now(datetime.UTC)` em `api/routes/auth.py`.

## Contexto

Revisão de codebase identificou uso de API deprecada em `auth.py:74-76`:
```python
expire = datetime.utcnow() + expires_delta
```

`datetime.utcnow()` está deprecado desde Python 3.12 (PEP 587). O método recomendado é `datetime.now(datetime.UTC)` que retorna um datetime timezone-aware.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 6.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `api/routes/auth.py`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (mesmo comportamento, API moderna)

## Critérios de Aceite

- [ ] `auth.py` usa `datetime.now(datetime.UTC)` em vez de `datetime.utcnow()`
- [ ] Import de `datetime.UTC` (ou `from datetime import UTC`)
- [ ] Nenhum DeprecationWarning ao rodar com Python 3.12+
- [ ] Testes de autenticação continuam passando

## Restrições

- Manter compatibilidade com PyJWT (verificar se aceita timezone-aware datetime)
- Atualizar todas as ocorrências no arquivo

## Referências

- `api/routes/auth.py:74-76`
- [PEP 587](https://peps.python.org/pep-0587/)
- [datetime documentation](https://docs.python.org/3/library/datetime.html#datetime.datetime.now)

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
