# Guia de Configuração — Claude Code + Codex Plugin

> Guia prático para integrar o plugin `codex-plugin-cc` ao framework de desenvolvimento `.claude/`.

---

## 1. Instalação

### 1.1 Pré-requisitos

- Claude Code instalado e funcional
- Node.js 18.18+
- Conta ChatGPT (inclui Free) ou API key da OpenAI

### 1.2 Instalar o Plugin

No terminal do Claude Code, execute em sequência:

```bash
# Adicionar o marketplace
/plugin marketplace add openai/codex-plugin-cc

# Instalar o plugin
/plugin install codex@openai-codex

# Recarregar plugins
/reload-plugins

# Verificar instalação
/codex:setup
```

Se o Codex CLI não estiver instalado, o `/codex:setup` oferece instalar automaticamente.
Caso prefira instalar manualmente:

```bash
npm install -g @openai/codex
```

### 1.3 Autenticação

```bash
# Se nunca usou o Codex antes
!codex login
```

O login aceita conta ChatGPT ou API key.

---

## 2. Configuração do Projeto

### 2.1 Config do Codex (`.codex/config.toml`)

Crie na raiz do projeto:

```toml
# .codex/config.toml

# Modelo padrão para reviews e rescues
model = "gpt-5.4-mini"

# Nível de raciocínio: low | medium | high | xhigh
model_reasoning_effort = "high"
```

**Nota:** O projeto precisa ser trusted pelo Codex para que o config local seja carregado.

### 2.2 Estrutura Atualizada do Projeto

```
projeto/
├── .claude/
│   ├── enforcement.conf
│   ├── hooks/
│   │   ├── commit-msg
│   │   ├── post-merge
│   │   ├── pre-commit
│   │   └── pre-push
│   ├── issue-template.md
│   ├── pr-template.md
│   ├── registry.md
│   ├── rules/
│   │   ├── 00-trava-seguranca.md
│   │   ├── 01-principios.md
│   │   ├── 02-reconhecimento.md
│   │   ├── 03-modos-operacao.md
│   │   ├── 04-avaliacao-pos.md
│   │   ├── 05-convencoes.md
│   │   ├── 06-crura.md
│   │   ├── 07-integridade.md
│   │   ├── 08-registro-projeto.md
│   │   ├── 09-enforcement.md
│   │   ├── 10-engenharia-agentica.md
│   │   ├── 11-integracao-codex.md       ← NOVO
│   │   └── 12-portfolio-publico.md      ← NOVO
│   ├── setup-hooks.sh
│   └── tasks.md
├── .codex/
│   └── config.toml                       ← NOVO
└── ...
```

### 2.3 Registrar no Registry

Adicione na seção **Decisões Técnicas Relevantes** do `registry.md`:

```markdown
| Data | Decisão | Justificativa |
|------|---------|---------------|
| YYYY-MM-DD | Integração Codex via plugin codex-plugin-cc v1.0.2 | Review cruzado dual-agent. Claude Code como orquestrador, Codex como revisor/auxiliar. Modelo padrão: gpt-5.4-mini. Review gate: desativado (ativar apenas para tasks major com supervisão). |
```

---

## 3. Comandos Rápidos — Referência

| Comando | O que faz | Quando usar no CRURA |
|---------|-----------|---------------------|
| `/codex:review` | Review padrão das mudanças atuais | Etapa R — após avaliação pós-implementação |
| `/codex:review --base main` | Review comparando branch vs main | Etapa R — review de branch completa |
| `/codex:review --background` | Review em background | Etapa R — para não bloquear o fluxo |
| `/codex:adversarial-review` | Review adversarial (desafia decisões) | Etapa R — tasks `major` ou alto risco |
| `/codex:adversarial-review --background [foco]` | Review adversarial focado em background | Etapa R — segurança, concorrência, dados |
| `/codex:rescue [descrição]` | Delega tarefa ao Codex | Etapa C — bugs complexos, investigação |
| `/codex:status` | Verifica progresso de jobs | Após qualquer `--background` |
| `/codex:result` | Mostra resultado de job concluído | Após `/codex:status` indicar conclusão |
| `/codex:cancel` | Cancela job ativo | Quando resultado não é mais necessário |
| `/codex:setup --enable-review-gate` | Ativa review automático a cada resposta | Tasks `major` com supervisão ativa |
| `/codex:setup --disable-review-gate` | Desativa review automático | Após concluir task `major` |

---

## 4. Fluxos Práticos

### 4.1 Task Minor — Fluxo Padrão

```
1. Registrar task em tasks.md (minor)
2. Declarar Modo Desenvolvimento
3. Claude Code faz reconhecimento (regra 02)
4. Claude Code implementa (C do CRURA)
5. Claude Code executa avaliação pós-implementação (regra 04)
6. /codex:review --background
7. /codex:status → aguardar conclusão
8. /codex:result → avaliar findings
9. Corrigir findings válidos (se houver)
10. Claude Code atualiza registry.md
11. Desenvolvedor faz Upload (U do CRURA)
```

### 4.2 Task Major — Fluxo Completo com Review Adversarial

```
1. Registrar task em tasks.md (major)
2. Declarar Modo Desenvolvimento
3. Claude Code faz reconhecimento (regra 02)
4. Claude Code implementa (C do CRURA)
5. Claude Code executa avaliação pós-implementação completa (regra 04)
6. /codex:adversarial-review --background [foco de risco]
7. /codex:status → aguardar conclusão
8. /codex:result → avaliar findings adversariais
9. Corrigir findings válidos / registrar discordâncias
10. Claude Code atualiza registry com "Review cruzado (Codex): aplicado"
11. Desenvolvedor faz Upload (U do CRURA)
```

### 4.3 Bug Complexo — Delegação ao Codex

```
1. Registrar task fix em tasks.md
2. Declarar Modo Desenvolvimento
3. Claude Code faz reconhecimento
4. Claude Code tenta diagnóstico inicial
5. Se necessário: /codex:rescue investigate [descrição do bug, ref TASK-NNN]
6. /codex:status → aguardar
7. /codex:result → Claude Code revisa o diagnóstico/fix proposto
8. Claude Code aplica a correção (nunca aceitar cegamente)
9. Avaliação pós-implementação + /codex:review
10. Claude Code atualiza registry
```

### 4.4 Modo Review — Código Externo com Dupla Revisão

```
1. Declarar Modo Review
2. Claude Code executa as 4 camadas de análise (regra 03.2)
3. /codex:adversarial-review --background challenge [aspecto específico]
4. /codex:result → consolidar com análise do Claude Code
5. Classificação final: incorporar / reescrever / descartar
```

---

## 5. Alterações nos Templates Existentes

### 5.1 Relatório de Avaliação Pós-Implementação (regra 04.4)

Adicionar linha de review cruzado:

```
AVALIAÇÃO PÓS-IMPLEMENTAÇÃO
✓ Conformidade: [ok / pendências listadas]
✓ Qualidade: [ok / pontos de atenção listados]
✓ Impacto no escopo: [ok / conflitos listados]
✓ Review cruzado (Codex): [ok / findings e resolução | N/A (patch)]
✓ Checklist agêntico: [aplicado / N/A]
Decisão: [pronto para commit / requer ajustes]
```

### 5.2 Checklist de Auto-Revisão (regra 06.1)

Adicionar item:

```
- [ ] Review cruzado do Codex foi executado e findings tratados (minor/major)
```

### 5.3 Template de Task (campo Resultado)

Adicionar campo:

```markdown
#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** [nome da branch utilizada]
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Review cruzado (Codex):** [aplicado — sem findings | aplicado — N findings corrigidos | N/A]
- **Observações:** [notas relevantes para futuras tasks]
```

### 5.4 PR Template (seção Checklist)

Adicionar item:

```markdown
- [ ] Review cruzado (Codex) executado para tasks minor/major
```

---

## 6. Boas Práticas

**Sobre custos e limites:** Reviews e rescues do Codex consomem seus limites de uso da OpenAI. Para tasks `patch`, o Codex não é necessário — a avaliação pós-implementação do Claude Code é suficiente. Reserve o Codex para `minor` e `major`.

**Sobre o review gate:** O review gate é poderoso mas perigoso. Ele cria um loop Claude→Codex→Claude que pode consumir limites rapidamente. Use apenas quando puder monitorar ativamente a sessão e desative ao concluir.

**Sobre conflitos entre agentes:** Se o Claude Code e o Codex discordarem sobre uma abordagem, registre ambas as perspectivas e deixe o desenvolvedor decidir. O agente nunca toma decisão unilateral em caso de conflito entre análises.

**Sobre o `/codex:rescue`:** O resultado do rescue é tratado como código gerado por IA — sujeito a todas as regras da seção 10 (Engenharia Agêntica). O Claude Code deve revisar o output com o mesmo rigor aplicado ao seu próprio código.
