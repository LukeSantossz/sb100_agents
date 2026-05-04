# 10. Engenharia Agêntica — Metodologia Karpathy como Complemento Obrigatório

> **Referência:** Andrej Karpathy — de "Vibe Coding" (fev/2025) a "Agentic Engineering" (fev/2026).
> Esta regra é obrigatória e complementa as regras 01 (Princípios), 03 (Modos de Operação) e 06 (CRURA).

## 10.0 Contexto e Motivação

Em fevereiro de 2025, Andrej Karpathy cunhou o termo **vibe coding** para descrever uma forma de programação onde o desenvolvedor "se entrega às vibes, aceita tudo e esquece que o código existe". Um ano depois (fevereiro de 2026), Karpathy declarou o vibe coding ultrapassado e propôs a **engenharia agêntica** (agentic engineering): o uso profissional de agentes de IA para gerar código, com supervisão humana rigorosa e sem compromisso na qualidade.

A frase central de Karpathy define o paradigma:

> "Você não está escrevendo o código diretamente 99% do tempo. Você está orquestrando agentes que escrevem e atuando como supervisão."

Este sistema de regras adota a engenharia agêntica como padrão obrigatório. O vibe coding — aceitar output de IA sem revisão — é **explicitamente proibido** para qualquer código que entre na codebase do projeto.

## 10.1 Princípios da Engenharia Agêntica (Obrigatórios)

Estes princípios se aplicam a **toda interação onde o agente gera código**, independentemente do modo de operação:

### 10.1.1 Especificação Antes de Prompt

Não gere código sem plano. Antes de qualquer implementação:

- Defina a arquitetura e a abordagem técnica.
- Quebre o trabalho em tarefas bem delimitadas (alinhado com `tasks.md`).
- Declare premissas e restrições explicitamente.

Quanto melhor a especificação, melhor o output do agente. Pular o planejamento é o ponto onde projetos descarrilham.

**Conexão com regras existentes:** Este princípio reforça a regra 01 (Pense Antes de Codar) e a regra 00 (Trava de Segurança — task registrada como pré-condição).

### 10.1.2 Dirigir e Revisar — Nunca Aceitar Cegamente

O agente gera código; o humano (ou o próprio agente em modo de auto-revisão) revisa com o mesmo rigor aplicado a uma PR de um colega. A regra absoluta:

- **Se você não consegue explicar o que um módulo faz, ele não entra na codebase.**
- Aceitar output sem revisão de diff é vibe coding — e é proibido neste fluxo.
- Todo código gerado é tratado como **rascunho de um desenvolvedor júnior rápido porém não confiável** que precisa de supervisão constante.

**Conexão com regras existentes:** Este princípio é a base do Modo Review (regra 03.2) e do fluxo CRURA (regra 06 — etapa R: Review).

### 10.1.3 Testar Incansavelmente

Testes são o que transformam um agente não confiável em um sistema confiável:

- O agente deve, sempre que possível, escrever testes antes ou junto com a implementação.
- Sem testes, o agente declara "pronto" sobre código potencialmente quebrado.
- Testes existentes devem continuar passando após qualquer alteração (alinhado com a regra 04.3 — Verificação de Impacto).

**Regra prática:** Se a task não tem critérios de aceite verificáveis por teste, ela não está pronta para implementação.

### 10.1.4 O Humano é Dono da Codebase

O agente acelera o trabalho. O humano é responsável pelo sistema:

- Documentação, versionamento, CI e monitoramento são responsabilidade humana.
- O agente não toma decisões arquiteturais sem validação explícita.
- Código gerado por IA não tem autoria a ser creditada (alinhado com regra 05.2 — sem Co-authored-by).

### 10.1.5 Você Pode Delegar a Digitação, Não a Compreensão

A frase de Karpathy que sintetiza o paradigma: "Você pode terceirizar seu pensamento, mas não pode terceirizar sua compreensão."

- O desenvolvedor deve entender cada módulo que entra na codebase.
- Se o desenvolvedor não sabe explicar o funcionamento do código em termos próprios, a revisão não avança (alinhado com Modo Review, regra 03.2).
- A engenharia agêntica beneficia desproporcionalmente desenvolvedores seniores que já sabem como "pronto" se parece. Para desenvolvedores em formação, o Modo Tutor (regra 03.3) é o caminho — aprender os fundamentos, não pular etapas com IA.

## 10.2 Anti-Padrão: Vibe Coding

O vibe coding é útil para protótipos descartáveis, scripts pessoais e exploração criativa. **Ele não é permitido para código que entra na codebase do projeto.**

Sinais de vibe coding que o agente deve detectar e recusar:

| Sinal | Descrição | Ação do Agente |
|-------|-----------|----------------|
| Aceitar sem revisar | Usuário pede para "só aplicar" sem olhar o diff | Recusar. Apresentar o diff e solicitar revisão. |
| Colar erro e seguir | Usuário cola stack trace pedindo "só corrige" sem contexto | Pausar. Perguntar: qual o comportamento esperado? O que já foi tentado? |
| Escopo inflado | "Já que tá aqui, faz X também" sem task registrada | Recusar. Orientar a criar task separada. |
| Código além da compreensão | Implementação que o desenvolvedor não consegue explicar | Pausar. Ativar Modo Tutor ou simplificar a abordagem. |
| Prompt vago sem especificação | "Faz um sistema de auth completo" sem requisitos definidos | Recusar. Solicitar especificação mínima antes de implementar. |

## 10.3 Checklist Agêntico (Complementa o Checklist CRURA 6.1)

Além do checklist de auto-revisão existente (regra 06.1), as seguintes verificações são obrigatórias para código gerado por agente:

- [ ] O código foi gerado a partir de uma especificação clara (task com escopo técnico definido).
- [ ] Todo diff foi revisado — nenhum output foi aceito cegamente.
- [ ] O desenvolvedor (ou agente em auto-revisão) consegue explicar o que cada módulo alterado faz.
- [ ] Não há coerência superficial: o código funciona em cenários não triviais, não apenas no caso feliz.
- [ ] Não há abstração excessiva: padrões de design são justificados pelo contexto, não aplicados genericamente.
- [ ] Não há tratamento decorativo de erros: todo catch trata o erro de forma útil.
- [ ] Não há dependências fantasma: todo import referencia uma biblioteca instalada no projeto.
- [ ] Não há código plausível mas inventado: métodos, parâmetros de API e configurações foram verificados contra documentação oficial.
- [ ] Não há repetição disfarçada: lógica duplicada com variações cosméticas foi consolidada.

## 10.4 Integração com os Modos de Operação

### Modo Desenvolvimento + Engenharia Agêntica

O agente opera como implementador, mas segue o ciclo: **especificar → gerar → revisar → testar → validar**. A avaliação pós-implementação (regra 04) inclui o checklist agêntico (10.3) como etapa obrigatória.

### Modo Review + Engenharia Agêntica

O protocolo de review (regra 03.2) já trata código de IA como rascunho. A engenharia agêntica reforça: se o desenvolvedor não souber explicar o código, a revisão não avança. Os riscos específicos de código gerado por IA listados na regra 03.2 são complementados pelo checklist 10.3.

### Modo Tutor + Engenharia Agêntica

O Modo Tutor prioriza compreensão sobre velocidade. A engenharia agêntica valida essa postura: a IA deve ser ferramenta de aprendizado, não muleta. O agente nunca fornece código pronto no Modo Tutor (regra 03.3), e a engenharia agêntica explica por quê — fundamentos importam mais, não menos, em um mundo com IA.

## 10.5 Registro de Conformidade

O Registro de Projeto (`registry.md`) deve incluir nas Observações de cada implementação se o checklist agêntico foi aplicado. A notação é simples:

- **Checklist agêntico: aplicado** — todas as verificações de 10.3 foram executadas.
- **Checklist agêntico: N/A** — a task não envolveu geração de código por agente (ex: documentação pura, configuração manual).

Isso permite rastrear a adoção do paradigma ao longo do tempo e identificar padrões de melhoria.
