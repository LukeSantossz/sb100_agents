# 10. Seleção de Modelo e Rituais de Atenção

Esta regra complementa a trava de segurança (regra 00) com dois mecanismos: seleção de modelo proporcional à complexidade da task, e rituais de re-ancoragem para evitar drift de diretrizes em sessões longas.

## 10.1 Seleção de Modelo por Complexidade

O modelo do agente deve ser proporcional ao risco e à demanda cognitiva da task. Usar modelo acima do necessário desperdiça tokens; usar abaixo aumenta risco de falha processual ou de qualidade.

### 10.1.1 Mapeamento Padrão

| Cenário | Modelo piso recomendado |
|---------|-------------------------|
| Task `patch` | Sonnet |
| Task `minor` | Sonnet |
| Task `major` | Opus |
| Modo Review (qualquer complexidade) | Opus |
| Modo Tutor (padrão) | Sonnet |
| Modo Tutor em conceito denso (sob demanda do usuário) | Opus |
| Recuperação de sessão interrompida | Opus |
| Verificação pós-pull / merge / rebase | Opus |
| Decisão arquitetural fora de task (discussão) | Opus |

### 10.1.2 Princípios

- **Piso absoluto: Sonnet.** Haiku não é usado para writes em arquivos do projeto. A diferença de custo entre Haiku e Sonnet não compensa o risco de falha em cerimônia, validação de convenções ou detecção de conflito de escopo.
- **Recomendação é piso, não teto.** Se Sonnet falhar a cerimônia em uma task `minor` ou `patch` específica, o desenvolvedor sobe para Opus naquela sessão e o caso vira nota em Padrões Recorrentes do `registry.md`.
- **Na dúvida, suba um tier.** Mesma lógica da classificação de complexidade ("na dúvida, classifique para cima"). Custo de Opus desnecessário é menor que custo de retrabalho.
- **Não degradar regras para acomodar modelo menor.** Se uma task `minor` exige que se pule reconhecimento ou avaliação para caber no Sonnet, a task está mal classificada — não é `minor`, ou o modelo precisa subir.

### 10.1.3 Responsabilidade

A seleção do modelo é do desenvolvedor (configurada no cliente). O agente não pode trocar de modelo, mas pode e deve **sinalizar** quando perceber descompasso:

- Se for solicitado a executar uma task `major` em modelo abaixo do recomendado: avisar o usuário e pedir confirmação antes de prosseguir.
- Se notar repetidamente falhas de cerimônia em modelo Sonnet para uma classe de tasks: registrar em Padrões Recorrentes para o desenvolvedor reavaliar.

## 10.2 Micro-Checkpoint Pré-Escrita

Antes de **qualquer** invocação de ferramenta que crie, edite ou delete arquivo do projeto, o agente emite uma linha exatamente neste formato:

```
[CHECKPOINT] TASK-NNN | Modo: X | Complexidade: Y | Ação: Z
```

### 10.2.1 Campos

- **TASK-NNN:** número da task ativa em `tasks.md` (Tasks Ativas). Não inventar. Se não houver task ativa correspondente à ação, não é caso de checkpoint — é caso de parar.
- **Modo:** Desenvolvimento | Review | Tutor — o modo declarado pelo usuário na sessão.
- **Complexidade:** patch | minor | major — conforme classificada em `tasks.md`.
- **Ação:** descrição curta da operação prestes a ser executada (≤ 60 caracteres). Ex: "criar src/auth/login.ts", "renomear userData em 3 arquivos", "editar registry.md — entrada TASK-007".

### 10.2.2 Comportamento

- Se qualquer campo não puder ser preenchido com verdade, o agente **não executa o write**. Reporta ao usuário qual condição está pendente e aguarda orientação.
- O checkpoint vai no corpo da resposta, antes do tool call, em linha própria. É legível pelo usuário no transcript e funciona como prova rastreável.
- O checkpoint **não substitui** as outras condições da trava (regra 00). É adicional: a 5ª condição.
- Múltiplos writes na mesma operação lógica (ex: criar 3 arquivos da mesma feature) podem compartilhar um único checkpoint se a ação cobrir todos. Writes de naturezas distintas exigem checkpoints separados.

### 10.2.3 O Que o Checkpoint Não É

- Não é confirmação pedida ao usuário. É anúncio.
- Não é justificativa da ação. É identificação.
- Não é opcional para "ações pequenas". Patch tem checkpoint igual a major.

## 10.3 Gatilho "desviou"

Mecanismo de re-ancoragem ativado pelo usuário quando perceber que o agente está saindo das diretrizes.

### 10.3.1 Ativação

O agente monitora **toda mensagem do usuário** pela presença da palavra `desviou`. A detecção é literal e ampla:

- Em qualquer posição da mensagem.
- Com ou sem pontuação adjacente.
- Independente de capitalização (`Desviou`, `DESVIOU` também disparam).
- Sem escapatória contextual — se o usuário usar a palavra em contexto não-gatilho, o agente ainda assim executa o protocolo. O custo de um falso positivo é uma linha de reset; o de um falso negativo é a sessão saindo dos trilhos.

### 10.3.2 Protocolo

Ao detectar o gatilho:

1. **Parar.** Nenhum tool call adicional. Nenhuma continuação de plano em curso.
2. **Re-ler `.claude/quick-ref.md`** integralmente.
3. **Responder apenas com o formato fixo:**

```
[RESET] Task ativa: TASK-NNN | Modo: X | Última ação: [resumo curto] | Próximo passo proposto: [um item]
```

4. **Aguardar confirmação explícita do usuário** antes de retomar qualquer ação. Confirmação implícita não conta — o usuário precisa dizer para prosseguir.

### 10.3.3 Campos do Reset

- **Task ativa:** TASK-NNN conforme `tasks.md`. Se não houver task ativa, escrever `nenhuma` e o próximo passo proposto deve ser "registrar task antes de prosseguir".
- **Modo:** o modo declarado para a sessão. Se nunca foi declarado, escrever `não declarado` e o próximo passo proposto deve incluir solicitação de declaração.
- **Última ação:** uma frase curta descrevendo o que o agente estava fazendo quando o gatilho disparou. Honesto, não maquiado.
- **Próximo passo proposto:** **uma** ação concreta, não uma lista. Se há múltiplos caminhos, o agente escolhe um e justifica em uma frase opcional após o bloco `[RESET]`.

### 10.3.4 Restrições

- Não justificar o reset com defesa do que estava fazendo. O usuário acionou o gatilho — isso é a única justificativa necessária.
- Não pedir desculpas elaboradas. Uma frase curta de reconhecimento, se for o caso, e segue.
- Não tentar adivinhar por que o usuário disparou. Se a causa for relevante para o próximo passo, o usuário dirá na resposta.
- Não combinar o reset com execução de outras solicitações da mesma mensagem do usuário. O reset é exclusivo da resposta.

## 10.4 Relação com Outras Regras

- **Regra 00 (trava):** o micro-checkpoint (§10.2) é a 5ª condição da trava. A regra 00 referencia esta seção.
- **Regra 03 (modos):** a seleção de modelo (§10.1) referencia os modos definidos lá. Não os altera.
- **Regra 04 (avaliação):** a complexidade da task continua sendo classificada em `tasks.md` e determinando o nível de cerimônia da avaliação. Esta regra só adiciona a dimensão de modelo.
- **Regra 08 (registry):** falhas repetidas de cerimônia em modelo Sonnet (10.1.2) são registradas em Padrões Recorrentes.
- **Quick-ref:** este conteúdo é resumido em `.claude/quick-ref.md` para leitura always-on. Em caso de conflito entre quick-ref e esta regra, esta regra tem precedência.
