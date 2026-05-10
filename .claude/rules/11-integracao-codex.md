# 11. Integração Claude Code + Codex — Orquestração Dual

> **Referência:** Plugin oficial `openai/codex-plugin-cc` v1.0.2
> Esta regra complementa as regras 03 (Modos de Operação), 04 (Avaliação Pós-Implementação), 06 (CRURA) e 10 (Engenharia Agêntica).

## 11.0 Princípio Fundamental

O Claude Code é o **orquestrador primário** — dono do fluxo, do estado (`tasks.md`, `registry.md`) e das regras 00-10. O Codex é uma **ferramenta especializada** invocada pelo Claude Code em momentos definidos. Nenhum dos dois opera fora do fluxo CRURA.

**Divisão de responsabilidades:**

| Responsabilidade | Claude Code | Codex |
|-----------------|-------------|-------|
| Gerenciar tasks, registry, estado | ✓ | — |
| Reconhecimento de codebase | ✓ | — |
| Implementação (Modo Dev) | ✓ | Via `/codex:rescue` quando delegado |
| Avaliação pós-implementação | ✓ | — |
| Review de código | ✓ (auto-review) | ✓ (review cruzado via plugin) |
| Review adversarial | — | ✓ (`/codex:adversarial-review`) |
| Investigação de bugs | ✓ | ✓ (delegável via `/codex:rescue`) |
| Atualização do registry | ✓ | — |

## 11.1 Setup Obrigatório

Antes de usar a integração, o desenvolvedor deve:

1. Instalar o plugin no Claude Code:
   ```
   /plugin marketplace add openai/codex-plugin-cc
   /plugin install codex@openai-codex
   /reload-plugins
   ```

2. Verificar a instalação:
   ```
   /codex:setup
   ```

3. Autenticar o Codex (se necessário):
   ```
   !codex login
   ```

4. (Opcional) Configurar modelo e esforço padrão em `.codex/config.toml`:
   ```toml
   model = "gpt-5.4-mini"
   model_reasoning_effort = "high"
   ```

5. Registrar a configuração no `registry.md`, seção Decisões Técnicas:
   ```
   Integração Codex: plugin codex-plugin-cc ativo. Modelo: [modelo]. Review gate: [ativo/inativo].
   ```

**Sobre o Review Gate:** O review gate (`/codex:setup --enable-review-gate`) instala um hook Stop que executa review do Codex automaticamente a cada resposta do Claude Code. **Usar com cautela** — consome limites de uso rapidamente e pode criar loops longos. Recomendado apenas para tasks `major` com supervisão ativa. Registrar no `registry.md` quando ativado/desativado.

## 11.2 Integração com o Fluxo CRURA

O Codex se encaixa em pontos específicos do CRURA:

### Etapa C (Change) — Implementação

**Padrão:** Claude Code implementa normalmente.

**Delegação ao Codex:** Quando a task envolver investigação de bug complexo, correção isolada, ou tarefa que se beneficie de um segundo agente trabalhando em paralelo, o Claude Code pode delegar via:

```
/codex:rescue [descrição clara da tarefa, referenciando TASK-NNN]
```

**Regras de delegação:**
- A task deve estar registrada em `tasks.md` antes da delegação.
- O Claude Code deve incluir na descrição do rescue: o objetivo da task, os arquivos envolvidos e as restrições.
- O resultado do Codex (`/codex:result`) deve ser revisado pelo Claude Code antes de incorporar à codebase — nunca aceito cegamente (regra 10.1.2).
- O Claude Code registra no Log de Andamento da task: "Delegado ao Codex — rescue [motivo]".

### Etapa R (Review) — Revisão

**Review padrão (toda task `minor` e `major`):**

Após a avaliação pós-implementação do Claude Code (regra 04), executar:

```
/codex:review --background
```

Quando concluído, verificar com `/codex:status` e `/codex:result`.

**Review adversarial (tasks `major` ou de alto risco):**

Para tasks que envolvem segurança, persistência de dados, autenticação, concorrência ou mudanças arquiteturais:

```
/codex:adversarial-review --background [foco específico do desafio]
```

Exemplos de foco:
- `challenge whether this auth flow handles token expiration correctly`
- `look for race conditions in the concurrent state updates`
- `question whether this caching strategy handles invalidation`

**Regras de review cruzado:**
- Findings do Codex que o Claude Code concorda devem ser corrigidos antes de avançar para Upload.
- Findings que o Claude Code discorda devem ser registrados nas Observações da task com justificativa.
- O resultado do review é registrado no Relatório de Avaliação (regra 04.4) como linha adicional:
  ```
  ✓ Review cruzado (Codex): [ok / pontos levantados e resolução]
  ```

### Etapa U (Upload) — Push

Sem alteração. Responsabilidade do desenvolvedor.

### Etapa RA (Review Again + Auto-Revisão)

Sem alteração no checklist. O review do Codex já foi incorporado na etapa R.

## 11.3 Mapeamento por Modo de Operação

### Modo Desenvolvimento + Codex

| Momento | Comando Codex | Quando usar |
|---------|--------------|-------------|
| Após implementação | `/codex:review` | Sempre para `minor` e `major` |
| Após implementação de alto risco | `/codex:adversarial-review` | Tasks `major` com componente de segurança, dados ou concorrência |
| Bug complexo | `/codex:rescue` | Investigação que se beneficia de agente paralelo |
| Monitoramento | `/codex:status` + `/codex:result` | Após qualquer comando `--background` |

### Modo Review + Codex

Quando o Claude Code está revisando código gerado por IA (regra 03.2), o Codex pode ser usado como segunda camada de análise:

1. Claude Code executa as 4 camadas de análise (Estrutural, Lógica, Arquitetural, Robustez).
2. Em paralelo (background), o Codex executa review adversarial focado nos riscos de código IA (regra 03.2 — riscos específicos).
3. Claude Code consolida ambas as análises na classificação final.

### Modo Tutor + Codex

**Não aplicável.** O Modo Tutor prioriza compreensão sobre velocidade. Delegar ao Codex contradiz o objetivo pedagógico. O Codex não deve ser usado no Modo Tutor exceto para demonstrar ao desenvolvedor como diferentes agentes abordam o mesmo problema (uso comparativo, não produtivo).

## 11.4 Gerenciamento de Tasks em Background

O Codex opera de forma assíncrona quando usado com `--background`. O Claude Code deve:

1. **Ao delegar:** Registrar no Log de Andamento da task que há trabalho em background no Codex.
2. **Ao verificar:** Usar `/codex:status` para checar progresso antes de avançar no fluxo.
3. **Ao receber resultado:** Usar `/codex:result` e avaliar o output contra os critérios de aceite da task.
4. **Ao cancelar:** Usar `/codex:cancel` e registrar o motivo no Log de Andamento.

**Regra de não-bloqueio:** O Claude Code não deve ficar parado esperando o Codex. Se o resultado do Codex é necessário para avançar (ex: review cruzado antes de Upload), o desenvolvedor deve ser informado para aguardar ou prosseguir sob risco próprio.

## 11.5 Registro e Rastreabilidade

Toda interação com o Codex deve ser rastreável:

**No `tasks.md` (Log de Andamento):**

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| YYYY-MM-DD | N | Codex review executado — 2 findings, ambos corrigidos | em andamento |
| YYYY-MM-DD | N | Codex rescue — investigação de bug em [módulo] | em andamento |

**No `registry.md` (Observações da implementação):**
- Review cruzado (Codex): aplicado | N/A
- Checklist agêntico: aplicado (inclui validação do output do Codex)

**No Relatório de Avaliação Pós-Implementação:**
```
AVALIAÇÃO PÓS-IMPLEMENTAÇÃO
✓ Conformidade: [ok / pendências]
✓ Qualidade: [ok / pontos de atenção]
✓ Impacto no escopo: [ok / conflitos]
✓ Review cruzado (Codex): [ok / findings e resolução]
✓ Checklist agêntico: aplicado
Decisão: [pronto para commit / requer ajustes]
```

## 11.6 Anti-Padrões de Integração

| Anti-Padrão | Por que é problemático | O que fazer |
|-------------|----------------------|-------------|
| Codex como implementador primário | Perde o controle de estado (tasks, registry) | Claude Code implementa, Codex revisa ou auxilia |
| Aceitar output do `/codex:rescue` sem revisão | Vibe coding — regra 10.1.2 | Sempre revisar diff do Codex antes de incorporar |
| Review gate ativo sem supervisão | Loops longos, consumo excessivo de limites | Ativar apenas para tasks `major` com monitoramento |
| Delegar ao Codex sem task registrada | Viola regra 00 (Trava de Segurança) | Registrar task primeiro, depois delegar |
| Usar Codex no Modo Tutor para gerar código | Contradiz objetivo pedagógico | Usar apenas para comparação conceitual |
| Ignorar findings do Codex sem justificativa | Perde o valor do review cruzado | Registrar concordância ou discordância com motivo |

## 11.7 Fluxo Resumido — Decisão de Uso do Codex

```
Task registrada em tasks.md?
├─ NÃO → Registrar antes de qualquer ação
└─ SIM → Modo de operação?
    ├─ TUTOR → Codex não aplicável (exceto comparação)
    ├─ REVIEW → Claude Code revisa + /codex:adversarial-review como segunda camada
    └─ DESENVOLVIMENTO → Complexidade?
        ├─ PATCH → Claude Code implementa + avaliação leve. Codex não necessário.
        ├─ MINOR → Claude Code implementa + /codex:review após avaliação pós-implementação
        └─ MAJOR → Claude Code implementa + /codex:adversarial-review + review gate opcional
```
