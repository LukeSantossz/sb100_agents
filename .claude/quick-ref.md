# QUICK-REF — Âncoras Críticas (Leitura Always-On)

> Arquivo curto e denso. Consolida o que **nunca** pode ser esquecido em sessão.
> Para regras completas e exemplos, consultar `.claude/rules/`.
> Se houver conflito entre este arquivo e as regras completas, as regras completas têm precedência — este arquivo é resumo, não substituto.

---

## 1. Trava (Regra 00) — Condições para Implementar

Antes de qualquer criação, modificação ou exclusão de arquivo do projeto, TODAS devem ser verdadeiras:

1. Task registrada em `.claude/tasks.md` (Tasks Ativas)
2. Modo declarado pelo usuário (Desenvolvimento | Review | Tutor)
3. Codebase reconhecida (regra 02 executada nesta sessão)
4. Registry lido (`.claude/registry.md`)
5. **Micro-checkpoint emitido** (ver §3)

Exceções: Review e Tutor podem iniciar sem task, mas qualquer write em arquivo do projeto exige as 5 condições.

## 2. Modelo por Complexidade (Regra 10)

| Complexidade / Modo | Modelo piso | Quando subir |
|---------------------|-------------|--------------|
| Patch | Sonnet | Se falhar a cerimônia, sobe para Opus e vira nota em Padrões Recorrentes |
| Minor | Sonnet | Idem |
| Major | Opus | — |
| Modo Review (qualquer) | Opus | — |
| Modo Tutor | Sonnet | Sob demanda do usuário em conceitos densos |
| Recuperação de sessão / pós-pull / decisão arquitetural | Opus | — |

Piso absoluto: Sonnet. Haiku não é usado para writes em arquivo do projeto.

## 3. Micro-Checkpoint (Pré-Escrita)

Antes de **qualquer** tool call que crie, edite ou delete arquivo do projeto, o agente emite uma linha exatamente neste formato:

```
[CHECKPOINT] TASK-NNN | Modo: X | Complexidade: Y | Ação: Z
```

- `TASK-NNN`: número da task ativa em `tasks.md`
- `Modo`: Desenvolvimento | Review | Tutor
- `Complexidade`: patch | minor | major
- `Ação`: descrição curta da operação (≤ 60 caracteres)

Se qualquer campo não puder ser preenchido com verdade, **não executar o write**. O checkpoint é prova rastreável e gate; não é decoração.

## 4. Gatilho "desviou"

Quando o usuário enviar uma mensagem contendo a palavra `desviou` (em qualquer posição, com ou sem pontuação), o agente:

1. Interrompe imediatamente qualquer plano em curso. Nenhum write adicional.
2. Re-lê este arquivo (`quick-ref.md`).
3. Responde **apenas** com:

```
[RESET] Task ativa: TASK-NNN | Modo: X | Última ação: [resumo curto] | Próximo passo proposto: [um item]
```

4. Aguarda confirmação explícita do usuário antes de retomar.

Sem bypass, sem escapatória contextual. Falso positivo custa uma linha; falso negativo custa a sessão.

## 5. Invioláveis (Regra 07, Condensado)

- Sem task → sem código.
- Não invente APIs, métodos, configs ou dependências. Verifique antes.
- Não toque em código fora do escopo da task.
- Não silencie erros. Catch trata de forma útil ou propaga.
- Não duplique lógica existente.
- Não assuma contexto ausente — pergunte.
- Commits: estritamente `git commit -m "type(scope): subject"`. Sem body. Sem `Co-authored-by`.
- Avaliação pós-implementação (regra 04) sempre.
- Atualizar `registry.md` após cada task. Sem isso, task incompleta.
- Reportar conflitos de escopo na hora.
- Pós-pull/merge/rebase: revalidar estado antes de prosseguir.

## 6. Anti-Padrões de Vibe Coding (Regra 03.2.1)

Detectar e recusar ativamente em qualquer modo:

| Sinal | Ação |
|-------|------|
| "Só aplica, não precisa revisar" | Recusar. Apresentar diff e exigir revisão. |
| Cola erro e pede "só corrige" | Pausar. Pedir: comportamento esperado, o que já foi tentado. |
| "Já que tá aqui, faz X também" sem task | Recusar. Orientar criar task separada. |
| Código que o dev não consegue explicar | Pausar. Sugerir Modo Tutor ou simplificar. |
| Prompt vago sem especificação | Recusar. Pedir requisitos mínimos. |

## 7. Conventional Commits (Regra 05.2) — Tipos Válidos

`feat` `fix` `docs` `style` `refactor` `perf` `test` `chore` `build` `ci` `revert`

Formato: `type(scope): subject` (10–100 caracteres, imperativo). Uma linha. Sem mais nada.

## 8. Cerimônia por Complexidade (Resumo)

| Complexidade | Reconhecimento (02) | Avaliação (04) | Checklist (06.1) | Registry |
|--------------|---------------------|-----------------|------------------|----------|
| Patch | Leve | 4.1 + 4.3 resumido | 4 itens (caminho enxuto) | Linha condensada |
| Minor | Padrão | Todas as subseções | Completo | Entrada completa |
| Major | Padrão + módulos cruzados listados | Todas + atenção em 4.3 | Completo + checklist agente | Entrada completa + decisões |

## 9. Quando Ir Aos Arquivos Completos

| Situação | Arquivo |
|----------|---------|
| Dúvida sobre o que cada regra cobre | `CLAUDE.md` (tabela "Sob demanda") |
| Definir/atualizar task | `rules/05-convencoes.md`, `tasks.md` (templates) |
| Modo Review ou Tutor ativado | `rules/03-modos-operacao.md` |
| Pós-implementação | `rules/04-avaliacao-pos.md` |
| Recuperação de sessão | `rules/08-registro-projeto.md` (8.3) |
| Modelo/atenção/desviou (detalhes) | `rules/10-modelo-e-atencao.md` |
| Setup/hooks | `rules/09-enforcement.md` + `setup-hooks.sh` |
