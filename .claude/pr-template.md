# Template de Pull Request

> Copie o conteúdo abaixo ao criar uma PR. Preencha todos os campos aplicáveis.
> Referência: `rules/05-convencoes.md` (Commits), `rules/06-crura.md` (CRURA + Checklist).

---

## Título da PR
<!-- Formato: type(scope): descrição — ex: feat(auth): implementa recuperação de senha -->
<!-- O título segue Conventional Commits. Mesma regra dos commits. -->

### 1. Contexto
- **Motivação:** [Explique o porquê dessa mudança]
- **Link da Tarefa:** [Link do Jira/Trello/Asana/Issue]
- **Task ref.:** [TASK-NNN do tasks.md]

### 2. O que foi feito?
<!-- Liste as mudanças técnicas de forma resumida -->
- [ ] [Mudança 1]
- [ ] [Mudança 2]
- [ ] [Mudança 3]

### 3. Como testar?
1. Baixe a branch: `git checkout [nome-da-branch]`
2. Instale as dependências: `[comando]`
3. Rode o projeto: `[comando]`
4. Verifique: [o que o revisor deve validar]

### 4. Evidências
<!-- Screenshots ou vídeos se a mudança for visual. Remover se apenas backend/config. -->

### 5. Checklist de Auto-Revisão
- [ ] Realizei a auto-revisão na aba "Files Changed"
- [ ] Removi códigos comentados e console.logs desnecessários
- [ ] O código segue o guia de estilo do projeto
- [ ] As novas dependências funcionam sem quebrar o build atual
- [ ] Nomes seguem o VAR Method
- [ ] Commits seguem Conventional Commits (sem body, sem co-auth)
- [ ] Avaliação pós-implementação foi executada e aprovada