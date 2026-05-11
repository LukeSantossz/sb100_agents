# 2. Reconhecimento Obrigatório da Codebase (Pré-Implementação)

Análise de viabilidade executada antes de qualquer implementação. O objetivo é mapear o terreno e detectar incompatibilidades antes de escrever código — não auditar o que foi escrito (isso é responsabilidade da avaliação pós-implementação). Esta etapa deve ser leve e rápida: levantamento de fatos, não análise profunda.

Não avance para implementação sem concluí-la.

## 2.1 Inventário Técnico

Identifique e registre internamente:

- Linguagem(ns) e framework(s) em uso.
- Estrutura de diretórios e padrão arquitetural adotado.
- Convenções de código existentes: nomenclatura, organização de módulos, padrões de importação, estilo.
- Estado atual dos testes (existem? qual framework? qual cobertura?).
- Dependências do projeto e suas versões (package.json, pubspec.yaml, requirements.txt, etc.).
- Débitos técnicos visíveis, inconsistências e código morto.

## 2.2 Contexto do Produto

Se o projeto possui um PRD (`.claude/prd.md`), o agente deve lê-lo como parte do reconhecimento e registrar internamente:

- Escopo do MVP e funcionalidades definidas como "fora de escopo".
- Stack técnica declarada e suas justificativas.
- Arquitetura proposta e estrutura de diretórios planejada.
- Decisões em aberto que possam afetar a task atual.

O PRD é fonte de contexto, não de verdade absoluta — a codebase real tem precedência quando houver divergência.

## 2.3 Base de Conhecimento Externa

Se o `CLAUDE.md` indicar uma base de conhecimento externa (wiki, vault Obsidian), o agente deve consultar o índice para verificar se existem padrões catalogados relevantes para a task atual (soluções de debugging, decisões de stack recorrentes, anti-padrões documentados). Consultar sob demanda, não carregar integralmente.

## 2.4 Validação de Compatibilidade (Viabilidade)

Verifique rapidamente se a implementação pretendida é compatível com o projeto existente:

- O código proposto segue a arquitetura existente ou introduziria padrões divergentes?
- As dependências necessárias já existem no projeto ou precisariam ser adicionadas?
- A estrutura de arquivos proposta é coerente com a organização atual?
- Há funcionalidade equivalente já existente na codebase?

Se qualquer resposta indicar divergência, sinalize ao usuário antes de prosseguir. Não analise qualidade de código nesta etapa — isso ocorre na avaliação pós-implementação.
