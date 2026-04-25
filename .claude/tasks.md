# TASKS.md — Registro de Tasks para Implementação

> **Este arquivo é o ponto de entrada obrigatório para qualquer implementação.**
> Nenhum agente de IA pode modificar a codebase sem uma task formalmente registrada aqui.
> Consulte `instructions.md` Seção 0 (Trava de Segurança) para as regras completas.

---

## Como Usar

1. Copie o template da Seção "Template de Task" abaixo.
2. Preencha todos os campos obrigatórios (marcados com `!`).
3. Adicione a task preenchida na Seção "Tasks Ativas".
4. Inicie a sessão com o agente informando o modo de operação desejado (Desenvolvimento, Review ou Tutor).
5. Ao concluir, mova a task para "Tasks Concluídas" com o resultado preenchido.

---

## Template de Task

```markdown
### TASK-[NNN]
- **Status:** pendente | em andamento | concluída | descartada | revertida
- **Modo:** desenvolvimento | review | tutor
- **Complexidade:** patch | minor | major
- **Data de criação:** [YYYY-MM-DD]

#### Objetivo (!obrigatório)
[Descreva de forma direta o que precisa ser feito. Uma frase clara.
Teste: se alguém ler apenas esta linha, entende o que será entregue?]

#### Contexto (!obrigatório)
[Por que essa mudança é necessária? Qual problema resolve?
Se houver link de issue, PR, ou card de projeto, inclua aqui.]

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** [listar os arquivos ou áreas que serão tocados]
- **Dependências necessárias:** [novas dependências ou "nenhuma"]
- **Impacto em funcionalidades existentes:** [descrever ou "nenhum"]

#### Critérios de Aceite (!obrigatório)
[Liste as entregas concretas que definem a task como concluída.
Cada critério deve ser verificável — sim ou não, passou ou não passou.]
- [ ] [Critério 1]
- [ ] [Critério 2]
- [ ] [Critério 3]

#### Restrições (opcional)
[Limitações técnicas, de tempo, de escopo, ou decisões já tomadas que o agente deve respeitar.
Ex: "Não alterar o módulo X", "Manter compatibilidade com a versão Y", "Não adicionar dependências novas".]

#### Referências (opcional)
[Links de documentação, PRs anteriores, issues relacionadas, artigos técnicos relevantes.]

#### Log de Andamento (atualizado pelo agente)
> Registro cronológico do progresso da task. O agente adiciona uma entrada a cada sessão em que a task for trabalhada, incluindo sessões onde houve travamento ou interrupção. Nunca remova entradas anteriores.

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| —    | —      | —              | —               |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** [nome da branch utilizada]
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Observações:** [notas relevantes para futuras tasks]
```

### Classificação de Complexidade

A complexidade determina o nível de cerimônia na avaliação pós-implementação (ver `instructions.md` Seção 4.0):

| Nível | Quando usar | Exemplos |
|-------|-------------|----------|
| **patch** | Mudança trivial, sem risco de efeito colateral | Renomear variável, corrigir typo, ajustar espaçamento, remover import não utilizado |
| **minor** | Mudança localizada em um módulo, risco baixo | Implementar função isolada, corrigir bug em um arquivo, adicionar teste |
| **major** | Mudança estrutural, múltiplos arquivos, risco de impacto em cascata | Nova feature com múltiplos módulos, refatoração arquitetural, migração de dependência |

---

## Tasks Ativas

> Tasks em andamento ou pendentes de implementação. O agente só pode trabalhar em tasks listadas aqui.
> **Regra de ordenação:** A primeira task listada é a task ativa. O agente trabalha nela até conclusão, descarte ou bloqueio explícito pelo usuário. Para mudar a prioridade, o usuário reordena as tasks nesta seção.

[nenhuma task ativa no momento]

---

## Tasks Concluídas

> Tasks finalizadas. Movidas para cá após conclusão e atualização do Registro de Projeto (instructions.md Seção 9). Nunca remova entradas — o histórico é cumulativo.

### TASK-T18 — Atualização README MVP ✓
- **Concluída em:** 2026-04-25
- **Branch:** docs/TASK-T18-readme-mvp
- **Commit:** f055c2a docs: update README for MVP release
- **Detalhes:** `.claude/tasks/TASK-T18.md`
- **Nota:** README completo com estrutura de diretórios, exemplos de API e Known Issues

### TASK-000 — Enforcement Hooks ✓
- **Concluída em:** 2026-04-24
- **Branch:** chore/TASK-000-enforcement-hooks
- **Commit:** 266aed0
- **Detalhes:** Ver seção Tasks Ativas (mantida para referência)

---

## Tasks Descartadas

> Tasks que foram canceladas ou substituídas antes da implementação. Registre o motivo.

[nenhuma task descartada]

---

## Regras de Preenchimento

1. **O campo Objetivo deve caber em uma frase.** Se não cabe, a task é grande demais — quebre em subtasks.
2. **Uma task deve ser completável em uma sessão de desenvolvimento.** Se a estimativa de implementação excede uma sessão, ou se a task afeta mais de 10 arquivos, ela deve ser decomposta em subtasks independentes. Cada subtask recebe seu próprio TASK-NNN e segue o fluxo completo. O campo Contexto da subtask deve referenciar a task mãe.
3. **Critérios de Aceite são obrigatórios e verificáveis.** "Funcionar corretamente" não é critério. "Retornar status 200 para inputs válidos e 400 para inputs inválidos" é.
4. **Escopo Técnico deve listar arquivos concretos.** "Algumas telas" não serve. "src/screens/LoginScreen.tsx, src/services/authService.ts" serve.
5. **Uma task por implementação.** Se durante o desenvolvimento surgir necessidade de outra mudança fora do escopo, registre uma nova task — não expanda a atual.
6. **Tasks não são retroativas.** Código já implementado sem task registrada deve ser revisado (Modo Review) e documentado antes de prosseguir com novas tasks.
7. **O resultado é preenchido pelo agente** ao final da implementação, junto com a atualização do Registro de Projeto.
8. **Complexidade é obrigatória.** Toda task deve ser classificada como `patch`, `minor` ou `major`. Na dúvida, classifique para cima (minor em vez de patch, major em vez de minor). A classificação determina o nível de cerimônia da avaliação pós-implementação.
9. **A ordem na seção Tasks Ativas define prioridade.** A primeira task é a ativa. O agente não pula para a segunda sem que a primeira esteja concluída, descartada ou explicitamente pausada pelo usuário.
10. **O Log de Andamento é obrigatório para tasks `minor` e `major`.** O agente registra uma entrada a cada sessão em que trabalhar na task, incluindo interrupções e travamentos. Tasks `patch` podem omitir o log. O log captura o progresso intermediário; a conclusão final é registrada no Resultado da task e no Histórico de Implementações do `instructions.md` (Seção 9.3).
11. **Tasks revertidas não são deletadas.** Ao reverter uma implementação, a task original recebe status `revertida` com nota explicativa, e uma nova task `fix` ou `revert` é criada referenciando a original.