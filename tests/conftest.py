"""Configuração compartilhada da suíte de testes.

Define variáveis de ambiente exigidas antes do import de ``core.config`` (que
valida ``JWT_SECRET_KEY`` no startup). ``setdefault`` preserva valores fornecidos
externamente (ex.: CI), aplicando o valor de teste apenas quando ausente.
"""

import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-jwt-secret-key-for-tests-only-32-chars-minimum",
)
