# 12. Portfólio Público — GitHub como Artefato de Trabalho

> Esta regra define como o trabalho realizado sob as regras 00-11 se apresenta publicamente no GitHub. As regras anteriores garantem qualidade interna do projeto; esta regra garante que essa qualidade seja legível para terceiros (recrutador, tech lead avaliador, contribuidor externo).
> Complementa as regras 05 (Convenções) e 06 (CRURA).

## 12.0 Princípio

O GitHub não é depósito de código — é vitrine profissional. Cada repositório público comunica capacidade técnica e maturidade de trabalho em time. Quantidade não substitui qualidade: três projetos bem documentados produzem mais sinal do que trezentos exercícios de tutorial.

O leitor externo decide em segundos se vale a pena explorar um perfil. README ausente, repositórios sem contexto e commits genéricos comunicam amadorismo independentemente da qualidade real do código.

## 12.1 Curadoria de Repositórios

Toda configuração inicial de portfólio começa por curadoria. O agente, ao orientar publicação ou organização do GitHub, deve seguir:

- **Arquivar** repositórios de curso, exercícios isolados, forks abandonados e projetos descartados. O `archive` no GitHub remove o repositório da listagem ativa sem apagar o histórico.
- **Manter públicos** apenas repositórios que satisfaçam todas as condições:
  1. Resolvem um problema real, não um exercício de tutorial.
  2. Foram desenvolvidos seguindo o fluxo destas regras (Conventional Commits, PRs preenchidos, registro de decisões).
  3. Possuem README conforme 12.2.
- **Fixar no máximo seis repositórios.** Os pinned repositories são a vitrine — selecione os que melhor representam capacidade técnica em domínios distintos.

Para cada repositório fixado:

| Elemento | Diretriz |
|----------|----------|
| Título | Descreve o problema resolvido, não o estado interno. Use `crop-disease-detector`, não `project-final-v2`. |
| Descrição curta | Foco no problema, não na ferramenta. "Reduz erro de previsão de perda de safra" comunica mais do que "Built with TensorFlow". |
| Tags de linguagem | Configuradas corretamente no GitHub para indexação em buscas. |

## 12.2 README Obrigatório

Todo repositório público segue este padrão. Idioma: inglês — o mercado leitor é internacional.

Estrutura mínima:

1. **Contexto de negócio.** Por que o sistema existe e qual problema do mundo real ele resolve. Não descreva o que o código faz; descreva por que ele foi escrito.
2. **Diagrama de arquitetura.** Mermaid embutido ou imagem. Demonstra pensamento em fluxos e sistemas, não apenas em arquivos isolados.
3. **Decisões de engenharia.** Escolhas técnicas relevantes com justificativa breve. Ex: "Redis em vez de Memcached por suporte a estruturas de dados além de chave-valor". Esta seção é o reflexo público da seção *Decisões Técnicas Relevantes* do `registry.md` — o agente deve manter coerência entre os dois.
4. **Como executar.** Setup em uma linha quando possível. Para projetos com múltiplos serviços, `docker-compose.yml` impecável. Se o leitor precisar configurar banco manualmente para testar, ele desiste.

Itens opcionais conforme natureza do projeto: badges de build, screenshots, link para deploy, roadmap.

## 12.3 README de Perfil (Bio)

O README do perfil (repositório com nome igual ao usuário) é a primeira leitura. Deve conter:

- **Posicionamento técnico claro.** Padrão sugerido: `[papel] specialized in [domínio]. [resultado mensurável].`
- **Métrica de impacto.** Números provam contribuição onde adjetivos falham. "Reduced X by 30%" comunica mais do que "passionate about Y".
- **Sinais de atividade contínua** (12.5).

Evite frases genéricas como "I love coffee and coding" — ocupam espaço sem produzir sinal.

## 12.4 Histórico Visível

O histórico do GitHub é prova passiva do processo. Os pontos abaixo já são exigidos pelas regras 05 e 06 para o trabalho interno; aqui se registra que o leitor externo *vê* esse trabalho:

- **Commits.** Conventional Commits (regra 05.2) é também posicionamento público. `update`, `fix`, `ajustes finais` no histórico de um repositório fixado comunica amadorismo independentemente da qualidade do código.
- **Pull Requests.** PRs preenchidos via `pr-template.md` (regra 06.3) ficam públicos no histórico do repositório. A qualidade da argumentação técnica registrada é uma soft skill visível — demonstra como o autor sugere mudanças sem ser difícil de trabalhar.
- **Issues.** Issues bem descritas via `issue-template.md` mostram capacidade de identificar e comunicar problemas técnicos.

## 12.5 Sinais de Atividade Contínua

O leitor externo distingue entre quem *codou em algum momento* e quem *coda no presente*. Sinais que comunicam atividade contínua:

- **Gráfico de contribuições recente.** Não precisa ser denso, mas vazios prolongados em repositórios fixados levantam dúvida.
- **Última atualização visível** nos repositórios fixados. Repositórios fixados com último commit há anos enfraquecem o posicionamento.

## 12.6 Contribuições Externas

Contribuições open source registradas no histórico ampliam o sinal do portfólio. Estratégia de baixo custo:

- Comece pelas bibliotecas já usadas no dia a dia — você já conhece o contexto.
- Procure por `good first issue` em repositórios internacionais via GitHub Explore.
- Correções de documentação contam como contribuição válida.
- Um commit aceito em uma biblioteca de uso amplo produz mais sinal externo do que dezenas de certificados de curso.

A contribuição segue as mesmas regras deste sistema (Conventional Commits, PR argumentado), com adaptação às convenções do projeto receptor.

## 12.7 Conexão com o Fluxo Interno

O portfólio público é alimentado pelo trabalho interno, não construído à parte:

- O `registry.md` de cada projeto é a fonte das *Decisões de engenharia* do README público.
- O `tasks.md` não é exposto, mas o histórico de commits e PRs derivado dele é o que o leitor externo vê. Tasks bem registradas produzem histórico legível.
- Para projetos destinados ao portfólio, tasks `major` devem incluir, no Escopo Técnico, a atualização do README correspondente quando a mudança altera arquitetura, dependências relevantes ou decisões técnicas registradas.

## 12.8 Checklist de Portfólio

Use como autoavaliação periódica do estado público. Opera em camada diferente do checklist CRURA (6.1) — não o substitui.

- [ ] README de perfil com posicionamento técnico e ao menos uma métrica de impacto.
- [ ] No máximo seis repositórios fixados, com títulos orientados a problema e descrições focadas no domínio.
- [ ] READMEs em inglês com contexto de negócio, diagrama de arquitetura, decisões de engenharia e instruções de execução.
- [ ] Repositórios de curso, exercícios e projetos abandonados arquivados.
- [ ] Histórico de commits conforme regra 05.2 nos repositórios fixados.
- [ ] Pull Requests públicos preenchidos via `pr-template.md` visíveis no histórico.
- [ ] Ao menos uma contribuição open source registrada.
