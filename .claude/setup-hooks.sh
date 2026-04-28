#!/usr/bin/env bash
# setup-hooks.sh — Configura git para usar os hooks de enforcement
# Execute uma vez após clonar o repositório ou extrair o .zip:
#   chmod +x .claude/setup-hooks.sh && .claude/setup-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/hooks"

# Verifica se está dentro de um repositório git
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "ERRO: Este script deve ser executado dentro de um repositório git."
  exit 1
fi

# Torna hooks executáveis
chmod +x "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/post-merge"

# Configura git para usar os hooks
git config core.hooksPath .claude/hooks

echo ""
echo "Hooks de enforcement configurados com sucesso."
echo "  Diretório: .claude/hooks/"
echo "  git config core.hooksPath = .claude/hooks"
echo ""
echo "  Para desativar temporariamente: git commit --no-verify"
echo "  Para desativar permanentemente: git config --unset core.hooksPath"
echo ""
