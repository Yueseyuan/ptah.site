#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ECC_DIR="$HOME/.ecc-src"
ECC_INSTALL_STATE="$HOME/.claude/ecc/install-state.json"

# Skip if ECC is already installed
if [ -f "$ECC_INSTALL_STATE" ]; then
  echo "[ECC] Already installed, skipping."
  exit 0
fi

echo "[ECC] Installing ECC from https://github.com/affaan-m/ECC.git ..."

# Clone if not already cloned
if [ ! -d "$ECC_DIR" ]; then
  git clone --depth=1 https://github.com/affaan-m/ECC.git "$ECC_DIR"
fi

cd "$ECC_DIR"
npm install --no-audit --no-fund --loglevel=error
node scripts/install-apply.js --profile minimal --target claude

echo "[ECC] Installation complete."
