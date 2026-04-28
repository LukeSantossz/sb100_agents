# 4. Protocolo de Avaliação Pós-Implementação

Após cada implementação concluída, o agente executa obrigatoriamente esta verificação antes de apresentar o resultado ao usuário. Este protocolo é automático e não requer solicitação.

## 4.0 Nível de Cerimônia por Complexidade

A profundidade da avaliação é proporcional à complexidade da task, conforme classificada em `tasks.md`:

- **Patch** (renomear variável, corrigir typo, ajustar estilo, remover código morto): Verificação rápida — apenas 4.1 (conformidade) e 4.3 (impacto) em formato resumido. Relatório em uma linha.
- **Minor** (implementar função isolada, corrigir bug localizado, adicionar teste): Verificação padrão — todas as subseções (4.1 a 4.4) aplicadas.
- **Major** (nova feature com múltiplos arquivos, refatoração estrutural, migração de dependência): Verificação completa — todas as subseções com atenção redobrada em 4.3 (impacto no escopo). O agente deve listar explicitamente todos os módulos que interagem com o código alterado.

## 4.1 Verificação de Conformidade

Compare o que foi produzido contra o que foi solicitado:

- Todos os requisitos explícitos foram atendidos?
- Há critérios de aceite definidos? Todos foram cobertos?
- O código implementa exatamente o que foi pedido — nem mais, nem menos?
- Alguma premissa foi assumida sem validação com o usuário?

## 4.2 Verificação de Qualidade

Avalie o código produzido contra os padrões do projeto:

- Segue as convenções de nomenclatura do projeto (incluindo VAR Method)?
- Segue a arquitetura e padrões já estabelecidos na codebase?
- Tratamento de erros é real e útil, não cosmético?
- Edge cases foram considerados (inputs nulos, listas vazias, valores inesperados, estados concorrentes)?
- Não há código morto, imports não utilizados, console.logs, ou comentários residuais?
- A complexidade é proporcional ao problema?

## 4.3 Verificação de Impacto no Escopo

Analise se a implementação introduz conflitos com o restante da codebase:

- A mudança altera o comportamento de funcionalidades existentes?
- Há funções, componentes ou módulos que dependem do trecho alterado e que podem quebrar?
- Existe duplicação de lógica com código já existente?
- Dependências novas foram adicionadas? São compatíveis com as existentes?
- Testes existentes continuam passando?

Se qualquer conflito for identificado, reporte ao usuário com a seguinte estrutura:

```
⚠ CONFLITO DETECTADO
- Arquivo(s) afetado(s): [listar]
- Natureza do conflito: [descrever]
- Impacto potencial: [descrever]
- Recomendação: [ação sugerida]
```

## 4.4 Relatório de Avaliação

Ao concluir a verificação, apresente um resumo compacto:

```
AVALIAÇÃO PÓS-IMPLEMENTAÇÃO
✓ Conformidade: [ok / pendências listadas]
✓ Qualidade: [ok / pontos de atenção listados]
✓ Impacto no escopo: [ok / conflitos listados]
Decisão: [pronto para commit / requer ajustes]
```
