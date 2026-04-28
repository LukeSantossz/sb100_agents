# 8. Registro de Projeto — Regras de Atualização

> **O registro de projeto (`registry.md`) é mandatório.** O agente DEVE atualizá-lo ao final de cada implementação concluída com sucesso. Implementação sem registro subsequente é considerada incompleta.

## 8.1 Após Cada Implementação

O agente deve, imediatamente após a avaliação pós-implementação, atualizar o `registry.md` com:

- Entrada no Histórico de Implementações com a task concluída.
- Estado atual da codebase (arquivos alterados, dependências adicionadas/removidas).
- Pendências conhecidas, se houver.
- Decisões técnicas tomadas durante a implementação.

Esta atualização é a última etapa do ciclo. O agente não pode considerar a task finalizada sem ela.

## 8.2 Ao Iniciar uma Nova Sessão

Antes de qualquer ação, o agente deve ler o `registry.md` e validar:

- Qual foi a última implementação registrada.
- Se há pendências documentadas da sessão anterior.
- Se o estado registrado é compatível com a nova task.

## 8.3 Ao Executar Pull, Merge ou Qualquer Ação que Altera a Codebase Externamente

Quando o usuário indicar que houve alterações externas (pull, merge, rebase, contribuição de terceiros), o agente deve:

1. Executar o reconhecimento da codebase novamente.
2. Comparar o estado atual com o último estado registrado.
3. Registrar as divergências encontradas no `registry.md`.
4. Avaliar se as mudanças externas impactam a task atual ou tasks pendentes.
5. Reportar ao usuário qualquer conflito ou incompatibilidade antes de prosseguir.

```
VERIFICAÇÃO DE ESTADO PÓS-PULL
Estado registrado: [última implementação registrada]
Estado atual: [resumo das mudanças detectadas]
Divergências: [listar ou "nenhuma"]
Impacto na task atual: [sim/não — se sim, detalhar]
Decisão: [seguro para prosseguir / requer atenção do usuário]
```

## 8.4 Política de Arquivamento

Quando o histórico ultrapassar 30 entradas, o agente deve mover as entradas mais antigas (mantendo as 15 mais recentes) para o arquivo `registry-archive.md` na mesma pasta. O arquivo de arquivo é cumulativo e nunca editado após a inserção. Ao verificar histórico, o agente consulta ambos os arquivos se necessário.

## 8.5 Formato do Escopo Alterado

Registre de forma resumida — quantidade de arquivos e módulo afetado. Ex: "3 arquivos — módulo auth", "1 arquivo — config". O detalhamento completo de arquivos fica no Log de Andamento da task em `tasks.md` e no diff do commit.
