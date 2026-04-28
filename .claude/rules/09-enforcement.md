# 9. Enforcement Automatizado

> As regras deste sistema dependem do agente segui-las voluntariamente. Esta seção define uma camada de verificação automatizada que valida o cumprimento do fluxo independentemente do agente ou do desenvolvedor.

## 9.1 Escopo da Validação

O enforcement opera via git hooks (stack-agnóstico, puro bash + git) e valida as seguintes regras automaticamente:

**`commit-msg` — Executa a cada commit:**

- A mensagem segue o formato `type(scope): subject` com type válido.
- Não há body, rodapé, ou linhas além da primeira.
- Não há trailers de co-autoria (`Co-authored-by`, `Signed-off-by`).
- O subject está no imperativo e tem entre 10 e 100 caracteres.

**`pre-commit` — Executa antes de cada commit:**

- Não há `console.log`, `print()`, `debugger`, ou equivalentes nos arquivos staged (configurável por linguagem).
- Não há arquivos staged fora do escopo declarado na task ativa (validação por lista de arquivos em `tasks.md`, campo Escopo Técnico).

**`pre-push` — Executa antes de cada push:**

- A branch ativa segue o formato `type/TASK-NNN-descricao-curta`.
- Existe uma task com status `em andamento` em `tasks.md` cujo número corresponde ao `TASK-NNN` da branch.
- O Registro de Projeto possui entrada para cada task concluída referenciada nos commits sendo enviados.

**`post-merge` — Executa após pull/merge:**

- Sinaliza ao desenvolvedor que o estado da codebase pode ter mudado e que a verificação pós-pull deve ser executada na próxima sessão com o agente.

## 9.2 Princípios de Implementação

- **Stack-agnóstico:** Os hooks usam exclusivamente bash, git, grep e sed. Nenhuma dependência de runtime (Node, Python, etc.) é necessária para o enforcement funcionar.
- **Configurável:** Padrões de debug log (`console.log`, `print`, `debugger`) são definidos em um arquivo `.claude/enforcement.conf` que lista os patterns por linguagem. O hook lê este arquivo se existir; caso contrário, usa um conjunto padrão.
- **Não-bloqueante em caso de dúvida:** Se um hook não conseguir determinar com certeza se há violação (ex: `tasks.md` com formato inesperado), ele emite warning em vez de bloquear. Falsos positivos que impedem o trabalho são piores que falsos negativos.
- **Bypass documentado:** O desenvolvedor pode usar `git commit --no-verify` para pular hooks em situações excepcionais. Toda ocorrência de `--no-verify` deve ser justificada na próxima sessão com o agente e registrada nas Notas de Sessão.

## 9.3 Instalação

Os hooks são instalados na primeira sessão de desenvolvimento via **TASK-000** — a task de bootstrap obrigatória para qualquer projeto que adote este sistema. Registre-a em `tasks.md` como a primeira task do projeto, com complexidade `major`.

Após a instalação, o diretório `.claude/hooks/` contém os scripts e o comando `git config core.hooksPath .claude/hooks` redireciona o git para usá-los. Isso garante que os hooks são versionados junto ao repositório e compartilhados entre todos os desenvolvedores do projeto.
