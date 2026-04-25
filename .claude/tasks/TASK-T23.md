### TASK-T23
- **Status:** pendente
- **Modo:** desenvolvimento
- **Complexidade:** major
- **Data de criação:** 2026-04-24
- **Sprint:** Backlog
- **Prioridade:** Alta

#### Objetivo (!obrigatório)
Revisar contratos entre camadas do pipeline — assinaturas, tipos de entrada/saída e anotações em todos os pontos de integração entre módulos. Zero Any implícito. mypy --strict passando.

#### Contexto (!obrigatório)
Garantir que nenhuma camada dependa de comportamento implícito da anterior e que os contratos estejam explícitos, tipados e compatíveis com mypy --strict. Task criada como parte do ciclo de qualidade pós-auditoria estrutural (T19).

#### Escopo Técnico (!obrigatório)
- **Arquivos/módulos envolvidos:** todos os módulos do `app/`, com foco nos pontos de integração: `api/routes/chat.py`, `generation/llm.py`, `retrieval/vector_store.py`, `verification/gate.py`
- **Dependências necessárias:** `mypy`
- **Impacto em funcionalidades existentes:** alterações de assinatura podem exigir atualizações em cadeia nos consumidores

#### Critérios de Aceite (!obrigatório)
- [ ] Todos os pontos de integração entre módulos com anotações de tipo completas (sem `Any` implícito)
- [ ] Nenhuma função pública retornando tipo não declarado
- [ ] `ChatRequest` e `ChatResponse` como únicos contratos de entrada/saída da camada `api` — sem vazamento de tipos internos
- [ ] Interfaces entre `retrieval`, `generation`, `memory`, `profiling` e `verification` documentadas e estáveis
- [ ] `mypy --strict` passando após as correções
- [ ] Commit: `refactor(contracts): enforce typed interfaces across module boundaries`

#### Restrições
- Depende de: T19 — estrutura correta; T21 — mypy configurado
- Bloqueia: T24 — auditoria final
- Estratégia: Mapear o fluxo de dados do endpoint até a resposta final e verificar que cada função na cadeia declara explicitamente o que recebe e o que retorna. Usar `reveal_type()` do mypy para identificar inferências implícitas
- Risco: Alterações de assinatura podem exigir atualizações em cadeia nos consumidores — avaliar impacto antes de cada mudança

#### Referências
- https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
- https://peps.python.org/pep-0484/

#### Log de Andamento (atualizado pelo agente)

| Data | Sessão | Ação Realizada | Status ao Final |
|------|--------|----------------|-----------------|
| 2026-04-24 | — | Task criada como parte do ciclo de qualidade pós-auditoria estrutural (T19) | pendente |

#### Resultado (preenchido ao concluir)
- **Data de conclusão:** [YYYY-MM-DD]
- **Branch:** refactor/TASK-T23-typed-contracts
- **Commit(s):** [hash ou mensagem]
- **Avaliação pós-implementação:** [aprovado / aprovado com ressalvas / reprovado]
- **Observações:** [notas relevantes]

---
