# 6. Fluxo de Trabalho — Método CRURA

Todo código produzido segue obrigatoriamente este fluxo antes de ser submetido:

| Etapa | Nome | Ação | Responsável |
|-------|------|------|-------------|
| **C** | Change | Codifique a feature, ajuste ou refatoração com atenção e intenção. | Agente (Modo Dev) ou Desenvolvedor (Modo Tutor) |
| **R** | Review | Revise os arquivos alterados localmente. Faça commits atômicos para mudanças relacionadas. | Agente executa a avaliação pós-implementação e reporta. Desenvolvedor valida. |
| **U** | Upload | Execute `git push`. Use mensagens de commit seguindo Conventional Commits. | Desenvolvedor. O agente sugere a mensagem de commit e o nome da branch, mas o push é do desenvolvedor. |
| **R** | Review Again | Crie a Pull Request, vá na aba Files Changed e revise tudo novamente antes de pedir revisão. Corrija detalhes esquecidos: logs, nomes ruins, código comentado. | Desenvolvedor. O agente pode auxiliar preenchendo o template de PR (`.claude/templates/pr-template.md`). |
| **A** | Auto-Revisão | Execute o checklist de auto-revisão (6.1) antes de solicitar review externo. | Desenvolvedor, com suporte do agente para verificação automatizada. |

**Ponto de transferência:** O agente conclui sua responsabilidade ao final da etapa R (Review), após entregar a avaliação pós-implementação e atualizar o Registro de Projeto. A partir da etapa U (Upload), a responsabilidade é do desenvolvedor. O agente permanece disponível para suporte, mas não executa ações de git sem instrução explícita.

## 6.1 Checklist Unificado de Auto-Revisão

Antes de solicitar revisão, confirme:

**Base (toda task):**

- [ ] Realizei a auto-revisão na aba "Files Changed".
- [ ] Removi códigos comentados e console.logs desnecessários.
- [ ] O código segue o guia de estilo e convenções do projeto.
- [ ] As novas dependências funcionam sem quebrar o build atual.
- [ ] Nomes de variáveis e funções seguem o VAR Method.
- [ ] Commits seguem Conventional Commits (sem body, sem co-auth).
- [ ] Avaliação pós-implementação (regra 04) foi executada e passou.

**Para código gerado por agente (adicionar aos itens acima):**

- [ ] Todo diff foi revisado — nenhum output foi aceito cegamente.
- [ ] O desenvolvedor (ou agente em auto-revisão) consegue explicar o que cada módulo alterado faz.
- [ ] Sem coerência superficial: o código funciona em cenários não triviais, não apenas no caso feliz.
- [ ] Sem abstração excessiva: padrões de design são justificados pelo contexto, não aplicados genericamente.
- [ ] Sem tratamento decorativo de erros: todo catch trata o erro de forma útil.
- [ ] Sem dependências fantasma: todo import referencia uma biblioteca instalada no projeto.
- [ ] Sem código plausível mas inventado: métodos, parâmetros de API e configurações foram verificados contra documentação oficial.
- [ ] Sem repetição disfarçada: lógica duplicada com variações cosméticas foi consolidada.

**Para tasks com integração Codex (se aplicável):**

- [ ] Review cruzado do Codex foi executado e findings tratados (minor/major).

## 6.2 Protocolo de Reversão

Quando uma implementação aprovada revelar problemas após a conclusão (bugs descobertos em uso, conflitos com merge posterior, requisito mal interpretado), o seguinte procedimento se aplica:

1. **Registrar o problema:** Crie uma nova task em `tasks.md` com tipo `fix` ou `revert`, referenciando a task original que causou o problema.
2. **Reverter com commit adequado:** Use `git revert` para desfazer o commit problemático. A mensagem segue o padrão: `revert(scope): reverte TASK-NNN - [motivo breve]`.
3. **Atualizar o Registro de Projeto:** Registre a reversão no histórico com o motivo e a referência à task original.
4. **Atualizar a task original:** Na seção de resultado da task original em `tasks.md`, adicione uma nota indicando que foi revertida, com a data e referência à nova task.
5. **Avaliar a causa raiz:** Antes de reimplementar, identifique por que a avaliação pós-implementação não detectou o problema. Registre o padrão na seção de Padrões Recorrentes se for recorrente.

## 6.3 Templates

Os templates de PR e Issue são mantidos em `.claude/templates/`. O agente deve consultá-los quando necessário:

- **Pull Request:** `.claude/templates/pr-template.md` — usar ao criar ou auxiliar na criação de PRs.
- **Issue:** `.claude/templates/issue-template.md` — usar ao criar ou auxiliar na criação de issues.

O agente preenche os templates com base nos dados da task ativa e na avaliação pós-implementação. Os campos de checklist devem refletir o resultado real da verificação, não ser marcados automaticamente.
