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

## 2.2 Validação de Compatibilidade (Viabilidade)

Verifique rapidamente se a implementação pretendida é compatível com o projeto existente:

- O código proposto segue a arquitetura existente ou introduziria padrões divergentes?
- As dependências necessárias já existem no projeto ou precisariam ser adicionadas?
- A estrutura de arquivos proposta é coerente com a organização atual?
- Há funcionalidade equivalente já existente na codebase?

Se qualquer resposta indicar divergência, sinalize ao usuário antes de prosseguir. Não analise qualidade de código nesta etapa — isso ocorre na avaliação pós-implementação.
