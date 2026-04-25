### TASK-T18
- **Status:** concluída
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
- [x] Nova estrutura de diretórios documentada (`api/`, `core/`, `retrieval/`, `generation/`, `memory/`, `profiling/`, `verification/`)
- [x] Exemplo de `POST /chat` com body `ChatRequest` completo
- [x] Campo `hallucination_score` visível no exemplo de resposta
- [x] Tabela de status de features atualizada
- [x] Exemplo de curl funcional e testado com o sistema rodando
- [x] README Model aplicado (o que faz, o que é, tecnologias, ambição, estágio atual, problemas conhecidos)
- [x] Commit: `docs: update README for MVP release`

#### Restrições
- Depende de T16 (testes de integração) para garantir que os exemplos estejam corretos
- Bloqueia: nenhuma — task terminal do MVP

#### Referências
- https://github.com/LukeSantossz/sb100_agents

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-06 | — | Task criada como parte da FASE 5 do MVP | pendente |
| 2026-04-25 | 1 | Atualização completa do README: adição de ui/ e SETUP.md na estrutura, verificação de todos os critérios | concluída |
| 2026-04-25 | — | Task recuperada — ausente de tasks.md, status corrigido | pendente |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** 2026-04-25
- **Branch:** docs/TASK-T18-readme-mvp
- **Commit(s):** f055c2a docs: update README for MVP release
- **Avaliação pós-implementação:** aprovado
- **Observações:** README atualizado com estrutura completa incluindo ui/ e SETUP.md, exemplos de API com ChatRequest/ChatResponse, e seção Known Issues

---

## Track 2 — Ciclo de Qualidade Pós-Auditoria Estrutural

