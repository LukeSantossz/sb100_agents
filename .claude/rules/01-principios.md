# 1. Princípios Fundamentais

Estas regras regem todo comportamento do agente, independentemente do modo de operação ativo.

## 1.1 Pense Antes de Codar

Não assuma. Não esconda dúvidas. Exponha trade-offs.

Antes de implementar qualquer coisa:

- Declare suas premissas explicitamente. Se houver incerteza, pergunte.
- Se existirem múltiplas interpretações para a solicitação, apresente-as — não escolha silenciosamente.
- Se uma abordagem mais simples existir, diga. Empurre de volta quando necessário.
- Se algo estiver ambíguo, pare. Nomeie o que está confuso. Pergunte.

## 1.2 Simplicidade Primeiro

Código mínimo que resolve o problema. Nada especulativo.

- Nenhuma feature além do que foi pedido.
- Nenhuma abstração para código de uso único.
- Nenhuma "flexibilidade" ou "configurabilidade" que não foi solicitada.
- Nenhum tratamento de erro para cenários impossíveis.
- Se você escreveu 200 linhas e 50 resolveriam, reescreva.

Teste mental: "Um engenheiro sênior diria que isso está overengineered?" Se sim, simplifique.

## 1.3 Mudanças Cirúrgicas

Toque apenas no que é necessário. Limpe apenas a sua própria sujeira.

Ao editar código existente:

- Não "melhore" código adjacente, comentários ou formatação.
- Não refatore o que não está quebrado.
- Siga o estilo existente, mesmo que você faria diferente.
- Se notar código morto não relacionado à task, mencione — não delete.

Quando suas mudanças criarem órfãos (imports, variáveis, funções que ficaram sem uso por causa da sua alteração), remova-os. Não remova código morto pré-existente sem ser solicitado.

Regra de validação: toda linha alterada deve ter rastreabilidade direta à solicitação do usuário.

## 1.4 Execução Orientada a Objetivos

Defina critérios de sucesso. Itere até verificar.

Transforme tasks em objetivos verificáveis:

- "Adicionar validação" → "Escrever testes para inputs inválidos, depois fazê-los passar"
- "Corrigir o bug" → "Escrever teste que reproduz, depois fazê-lo passar"
- "Refatorar X" → "Garantir que testes passam antes e depois"

Para tasks com múltiplos passos, declare um plano breve antes de iniciar:

```
1. [Passo] → verificar: [critério]
2. [Passo] → verificar: [critério]
3. [Passo] → verificar: [critério]
```

## 1.5 Validação dos Princípios

Estes princípios estão funcionando quando:

- Diffs contêm menos mudanças desnecessárias a cada sessão.
- Reescritas por overengineering diminuem ao longo do tempo.
- Perguntas de esclarecimento acontecem antes da implementação, não depois de erros.

Registre essas observações na seção de Padrões Recorrentes do Registro de Projeto para acompanhar a evolução.
