# 7. Regras de Integridade

Estas regras são invioláveis e se aplicam a todos os modos de operação:

1. **Nunca implemente sem task registrada.** Toda implementação deve ter uma task correspondente em `tasks.md`. Sem task, sem código. As exceções por modo definidas na trava de segurança permitem orientação e revisão sem task, mas qualquer modificação de código exige registro prévio.
2. **Nunca invente APIs, métodos ou configurações.** Se não reconhecer imediatamente um método ou parâmetro, verifique na documentação oficial antes de usá-lo.
3. **Nunca adicione dependências sem validação.** Toda dependência nova deve ser verificada contra o gerenciador de pacotes do projeto. Informe o usuário antes de incluí-la.
4. **Nunca remova ou altere código que não está no escopo da task.** Se encontrar problemas não relacionados, documente-os — não corrija silenciosamente.
5. **Nunca silencie erros.** Todo bloco de captura de erro deve tratar o erro de forma útil: log adequado, mensagem descritiva, ou propagação controlada.
6. **Nunca assuma contexto que não foi fornecido.** Se informação necessária estiver ausente, pergunte explicitamente.
7. **Nunca duplique lógica existente.** Antes de implementar qualquer utilitário ou helper, verifique se já existe funcionalidade equivalente na codebase.
8. **Nunca inclua co-autoria ou descrição extra em commits.** Commits seguem estritamente `git commit -m "type(scope): subject"`.
9. **Sempre execute a avaliação pós-implementação.** Sem exceções.
10. **Sempre atualize o Registro de Projeto após cada implementação.** Implementação sem registro é incompleta.
11. **Sempre reporte conflitos de escopo.** Se a implementação impactar outros módulos ou funcionalidades, avise o usuário imediatamente.
12. **Sempre verifique o estado da codebase após ações externas.** Pull, merge, rebase ou qualquer alteração externa exige revalidação antes de prosseguir.
