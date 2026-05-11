# Guia de Integração — Claude Code + Codex

> Guia operacional para orquestração dual Claude Code + Codex.
> Carregar apenas quando o projeto usa integração Codex (verificar `registry.md`, seção Decisões Técnicas).
> Complementa as regras 03 (Modos), 04 (Avaliação) e 06 (CRURA).

---

## 1. Princípio

O Claude Code é o **orquestrador primário** — dono do fluxo, do estado (`tasks.md`, `registry.md`) e das regras. O Codex é uma **ferramenta especializada** invocada em momentos definidos. Nenhum dos dois opera fora do fluxo CRURA.

## 2. Setup

```bash
# No terminal do Claude Code
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup

# Autenticação (se necessário)
!codex login
```

Config local (`.codex/config.toml`):

```toml
model = "gpt-5.4-mini"
model_reasoning_effort = "high"
```

Registrar no `registry.md` (Decisões Técnicas): "Integração Codex: plugin codex-plugin-cc ativo. Modelo: [modelo]. Review gate: [ativo/inativo]."

## 3. Comandos

| Comando | O que faz | Quando usar no CRURA |
|---------|-----------|---------------------|
| `/codex:review` | Review padrão | Etapa R — após avaliação pós-implementação |
| `/codex:review --background` | Review em background | Etapa R — não bloquear o fluxo |
| `/codex:adversarial-review --background [foco]` | Review adversarial focado | Etapa R — tasks `major` ou alto risco |
| `/codex:rescue [descrição]` | Delega tarefa ao Codex | Etapa C — bugs complexos |
| `/codex:status` | Verifica progresso | Após qualquer `--background` |
| `/codex:result` | Mostra resultado | Após conclusão |
| `/codex:cancel` | Cancela job ativo | Quando resultado não é mais necessário |
| `/codex:setup --enable-review-gate` | Review automático a cada resposta | Tasks `major` com supervisão ativa |
| `/codex:setup --disable-review-gate` | Desativa review automático | Após concluir task `major` |

## 4. Quando Usar por Complexidade

- **Patch:** Codex não necessário — avaliação pós do Claude Code é suficiente.
- **Minor:** `/codex:review` após avaliação pós-implementação.
- **Major:** `/codex:adversarial-review` com foco de risco + review gate opcional.

## 5. Regras de Integração

- O resultado do Codex é tratado como código gerado por IA — sujeito ao checklist unificado (regra 06.1).
- Findings que o Claude Code concorda devem ser corrigidos antes de avançar para Upload.
- Findings que o Claude Code discorda devem ser registrados nas Observações da task com justificativa.
- O Claude Code não deve ficar parado esperando o Codex — informar o desenvolvedor para aguardar ou prosseguir.
- O Codex não é usado no Modo Tutor (contradiz objetivo pedagógico), exceto para comparação conceitual.

## 6. Registro

No relatório de avaliação pós-implementação, adicionar:

```
✓ Review cruzado (Codex): [ok / findings e resolução | N/A]
```

No `tasks.md` (Log de Andamento), registrar interações:

```
| YYYY-MM-DD | N | Codex review — 2 findings, ambos corrigidos | em andamento |
```

## 7. Anti-Padrões

| Anti-Padrão | O que fazer |
|-------------|-------------|
| Codex como implementador primário | Claude Code implementa, Codex revisa |
| Aceitar output do rescue sem revisão | Sempre revisar diff antes de incorporar |
| Review gate ativo sem supervisão | Ativar apenas para tasks major |
| Delegar sem task registrada | Registrar task primeiro |
| Ignorar findings sem justificativa | Registrar concordância ou discordância |
