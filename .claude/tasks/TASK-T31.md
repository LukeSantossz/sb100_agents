# TASK-T31 — Corrigir auth.py para Usar settings.jwt_secret_key

- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-25

## Objetivo

Substituir `os.environ.get("JWT_SECRET_KEY")` por `settings.jwt_secret_key` em `api/routes/auth.py` para garantir que o valor do `.env` seja carregado corretamente.

## Contexto

Revisão de codebase identificou que `auth.py:27` usa `os.environ.get()` diretamente:
```python
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "super-secret-key-replace-in-production")
```

O problema é que `os.environ.get()` só lê variáveis de ambiente do **sistema operacional**, não do arquivo `.env`. O Pydantic Settings (`core/config.py`) carrega o `.env` automaticamente, mas essa lógica é bypassada.

**Impacto:** Mesmo com `JWT_SECRET_KEY` configurado no `.env`, o código usará o fallback inseguro se a variável não estiver exportada no ambiente do sistema.

**Referência:** Relatório de revisão de 2026-04-25 — Inconsistência 3.

## Escopo Técnico

- **Arquivos/módulos envolvidos:**
  - `api/routes/auth.py`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum (comportamento correto quando `.env` está configurado)

## Critérios de Aceite

- [ ] `auth.py` importa `from core.config import settings`
- [ ] `SECRET_KEY` usa `settings.jwt_secret_key`
- [ ] Fallback vazio em `settings.jwt_secret_key` gera erro claro se não configurado
- [ ] Testes existentes continuam passando

## Restrições

- Manter compatibilidade com OAuth2PasswordRequestForm
- Não alterar a lógica de criação/verificação de tokens

## Referências

- `core/config.py:50` — definição de `jwt_secret_key`
- `api/routes/auth.py:27` — uso atual incorreto
- Pydantic Settings documentation

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
