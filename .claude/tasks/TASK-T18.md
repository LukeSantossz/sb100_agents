### TASK-T18
- **Status:** em andamento
- **Modo:** desenvolvimento
- **Complexidade:** minor
- **Data de criação:** 2026-04-06
- **Sprint:** Sprint 5
- **Prioridade:** Baixa

#### Objetivo (!obrigatório)
Atualizar o README.md para refletir a nova estrutura de diretórios do MVP, incluir exemplo de POST /chat com body completo e mostrar o campo hallucination_score na resposta.

#### Contexto (!obrigatório)
O README atual não reflete o estado pós-MVP do projeto. Precisa documentar a nova estrutura de diretórios, exemplos de uso da API, e tabela de status de features atualizada. Task terminal do MVP — criada como parte da FASE 5.

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** `README.md`
- **Dependências necessárias:** nenhuma
- **Impacto em funcionalidades existentes:** nenhum — documentação

#### Critérios de Aceite (!obrigatório)
- [ ] Nova estrutura de diretórios documentada (`api/`, `core/`, `retrieval/`, `generation/`, `memory/`, `profiling/`, `verification/`)
- [ ] Exemplo de `POST /chat` com body `ChatRequest` completo
- [ ] Campo `hallucination_score` visível no exemplo de resposta
- [ ] Tabela de status de features atualizada
- [ ] Exemplo de curl funcional e testado com o sistema rodando
- [ ] README Model aplicado (o que faz, o que é, tecnologias, ambição, estágio atual, problemas conhecidos)
- [ ] Commit: `docs: update README for MVP release`

#### Restrições
- Depende de T16 (testes de integração) para garantir que os exemplos estejam corretos
- Bloqueia: nenhuma — task terminal do MVP

#### Referências
- https://github.com/LukeSantossz/sb100_agents

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-06 | — | Task criada como parte da FASE 5 do MVP | pendente |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** docs/TASK-T18-readme-mvp
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Observações:** [notas relevantes]

---

## Track 2 — Ciclo de Qualidade Pós-Auditoria Estrutural

