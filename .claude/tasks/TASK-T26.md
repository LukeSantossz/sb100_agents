### TASK-T26
- **Status:** concluída
- **Modo:** desenvolvimento
- **Complexidade:** patch
- **Data de criação:** 2026-04-24
- **Sprint:** Backlog
- **Prioridade:** Média

#### Objetivo (!obrigatório)
Corrigir start.bat e start.ps1 que contêm caminhos hardcoded para o executável do Ollama, substituindo por resolução dinâmica via PATH do sistema.

#### Contexto (!obrigatório)
Ambos os scripts assumem que o Ollama está instalado em `C:\Users\lucas\AppData\Local\Programs\Ollama`. Qualquer outro membro da equipe que execute esses scripts em sua própria máquina receberá erro imediatamente. Identificado como bloqueador de portabilidade do projeto. Caminhos hardcoded para máquina individual não devem existir em arquivos versionados.

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** `start.bat`, `start.ps1`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** scripts passam a funcionar em qualquer máquina com Ollama no PATH

#### Critérios de Aceite (!obrigatório)
- [ ] `start.bat` usa `where ollama` para localizar o executável dinamicamente
- [ ] `start.ps1` usa `Get-Command ollama` para localizar o executável dinamicamente
- [ ] Scripts executam corretamente em qualquer máquina com Ollama no PATH
- [ ] Scripts exibem mensagem de erro clara se Ollama não estiver instalado (com link https://ollama.com)
- [ ] Nenhum caminho absoluto de usuário específico permanece no código
- [ ] Commit: `fix(scripts): replace hardcoded Ollama paths with dynamic PATH resolution`

#### Restrições
- Depende de: T25 — Guia de Setup (os scripts são referenciados como alternativa ao Docker para setup rápido)

#### Referências
- Correção esperada para `start.bat`: `for /f "tokens=*" %%i in ('where ollama 2^>nul') do set OLLAMA_EXE=%%i`
- Correção esperada para `start.ps1`: `$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue`

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-24 | — | Task criada. Bloqueador de portabilidade identificado | pendente |
| 2026-04-25 | 1 | Iniciando implementação. Reconhecimento: 5 ocorrências em start.bat, 2 em start.ps1 | em andamento |
| 2026-04-25 | 1 | Implementação concluída. Todos critérios atendidos | concluída |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** 2026-04-25
- **Branch:** fix/TASK-T26-hardcoded-paths
- **Commit(s):** 76503b3 fix(scripts): replace hardcoded Ollama paths with dynamic PATH resolution
- **Avaliação pós-implementação:** aprovado
- **Observações:** Scripts agora usam `where ollama` (bat) e `Get-Command ollama` (ps1) para resolução dinâmica. Mensagem de erro clara com link para instalação.

