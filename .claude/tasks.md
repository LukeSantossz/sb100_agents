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

### TASK-T30 — Alinhar COLLECTION_NAME entre config.py e .env.example
- **Status:** pendente
- **Complexidade:** patch
- **Detalhes:** `.claude/tasks/TASK-T30.md`

### TASK-T31 — Corrigir auth.py para Usar settings.jwt_secret_key
- **Status:** pendente
- **Complexidade:** minor
- **Detalhes:** `.claude/tasks/TASK-T31.md`

### TASK-T32 — Remover Ollama do Docker e Documentar Uso Local Exclusivo
- **Status:** pendente
- **Complexidade:** minor
- **Detalhes:** `.claude/tasks/TASK-T32.md`

### TASK-T33 — Refatorar Caminho do Banco de Dados para Usar Pathlib
- **Status:** pendente
- **Complexidade:** minor
- **Detalhes:** `.claude/tasks/TASK-T33.md`

### TASK-T34 — Substituir datetime.utcnow() por datetime.now(UTC)
- **Status:** pendente
- **Complexidade:** patch
- **Detalhes:** `.claude/tasks/TASK-T34.md`

### TASK-T35 — Corrigir Badge de Coverage no README
- **Status:** pendente
- **Complexidade:** patch
- **Detalhes:** `.claude/tasks/TASK-T35.md`

### TASK-T36 — Remover Módulo Duplicado semantic_entropy
- **Status:** pendente
- **Complexidade:** minor
- **Detalhes:** `.claude/tasks/TASK-T36.md`

---

## Tasks Concluídas

> Tasks finalizadas. Movidas para cá após conclusão e atualização do Registro de Projeto (instructions.md Seção 9). Nunca remova entradas — o histórico é cumulativo.

### TASK-T29 — Alinhar CHAT_MODEL em Todos os Arquivos ✓
- **Concluída em:** 2026-04-25
- **Branch:** main (pendente de commit)
- **Commit:** pendente
- **Avaliação:** aprovado
- **Nota:** .env.example e docker-compose.yml alinhados para llama3.2:3b

### TASK-T28 — Remoção completa de referências ao frontend React/npm ✓
- **Concluída em:** 2026-04-25
- **Branch:** docs/TASK-T28-readme-sync
- **Commits:** 870152e, 1be0a84, 0bff84b
- **PRs:** [#27](https://github.com/LukeSantossz/sb100_agents/pull/27), [#28](https://github.com/LukeSantossz/sb100_agents/pull/28)
- **Avaliação:** aprovado
- **Nota:** 12 arquivos alterados, package.json e package-lock.json removidos. Node.js não é mais dependência do projeto.

### TASK-T18 — Atualização README MVP ✓
- **Concluída em:** 2026-04-25
- **Branch:** docs/TASK-T18-readme-mvp
- **Commit:** f055c2a docs: update README for MVP release
- **Detalhes:** `.claude/tasks/TASK-T18.md`
- **Nota:** README completo com estrutura de diretórios, exemplos de API e Known Issues

### TASK-T26 — Fix Caminhos Hardcoded Ollama ✓
- **Concluída em:** 2026-04-25
- **Branch:** fix/TASK-T26-hardcoded-paths
- **Commit:** 76503b3 fix(scripts): replace hardcoded Ollama paths with dynamic PATH resolution
- **Detalhes:** `.claude/tasks/TASK-T26.md`
- **Nota:** Resolução dinâmica via PATH — portabilidade restaurada

### TASK-T25 — Guia de Setup com Modos Local e Remoto ✓
- **Concluída em:** 2026-04-25
- **Branch:** docs/TASK-T25-setup-guide
- **Commit:** 261a509 docs: add SETUP.md with local and remote Qdrant modes
- **Detalhes:** `.claude/tasks/TASK-T25.md`
- **Nota:** Escopo expandido: suporte QDRANT_API_KEY adicionado ao código

### TASK-T24 — Auditoria Clean Code, SOLID e Design Patterns ✓
- **Concluída em:** 2026-04-25
- **Branch:** refactor/TASK-T24-clean-code-audit
- **Commit:** refactor(quality): apply clean code and SOLID audit across codebase
- **Detalhes:** `.claude/tasks/TASK-T24.md`
- **Nota:** Auditoria completa + fixes menores (datetime.UTC, remoção alias redundante)

### TASK-T27 — Fix Formatação Ruff ✓
- **Concluída em:** 2026-04-25
- **Branch:** dev (commit direto — violação documentada)
- **Commit:** 76997b4 style(ui): format chat_ui.py with ruff
- **Detalhes:** `.claude/tasks/TASK-T27.md`
- **Nota:** Task retroativa — violações de fluxo documentadas

### TASK-T24-UI — Interface Gradio Chat ✓
- **Concluída em:** 2026-04-25
- **Branch:** feat/TASK-T24UI-gradio-interface
- **Commit:** d4922f6 feat(ui): add Gradio chat interface and refactor docker-compose with profiles
- **Detalhes:** `.claude/tasks/TASK-T24-UI.md`

### TASK-T17 — CI GitHub Actions ✓
- **Concluída em:** 2026-04-25
- **Branch:** ci/TASK-T17-github-actions
- **Commit:** 0e962f2 ci: add GitHub Actions workflow with lint, type check and RAG pipeline tests
- **Detalhes:** `.claude/tasks/TASK-T17.md`

### TASK-T23 — Contratos Tipados ✓
- **Concluída em:** 2026-04-24
- **Branch:** refactor/TASK-T23-typed-contracts
- **Commit:** docs(tasks): verify typed contracts and update task registry
- **Detalhes:** `.claude/tasks/TASK-T23.md`

### TASK-T22 — Docstrings e Comentários ✓
- **Concluída em:** 2026-04-24
- **Branch:** docs/TASK-T22-docstrings
- **Commit:** 1ee802c docs(modules): add docstrings and inline comments across all modules
- **Detalhes:** `.claude/tasks/TASK-T22.md`

### TASK-T21 — Configuração de Qualidade ✓
- **Concluída em:** 2026-04-24
- **Branch:** chore/TASK-T21-static-analysis-coverage
- **Commit:** c530b42 chore(quality): configure ruff, mypy and pytest-cov with coverage threshold
- **Detalhes:** `.claude/tasks/TASK-T21.md`

### TASK-000 — Enforcement Hooks ✓
- **Concluída em:** 2026-04-24
- **Branch:** chore/TASK-000-enforcement-hooks
- **Commit:** 266aed0
- **Detalhes:** Hooks git para enforcement do fluxo de trabalho

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