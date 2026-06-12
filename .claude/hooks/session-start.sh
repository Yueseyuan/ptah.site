#!/bin/bash
set -euo pipefail

echo '{"async": true, "asyncTimeout": 300000}'

# Only run in remote Claude Code web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# ── ECC ──────────────────────────────────────────────────────────────────────
ECC_DIR="$HOME/.ecc-src"
ECC_INSTALL_STATE="$HOME/.claude/ecc/install-state.json"

if [ -f "$ECC_INSTALL_STATE" ]; then
  echo "[ECC] Already installed, skipping."
else
  echo "[ECC] Installing ECC from https://github.com/affaan-m/ECC.git ..."
  if [ ! -d "$ECC_DIR" ]; then
    git clone --depth=1 https://github.com/affaan-m/ECC.git "$ECC_DIR"
  fi
  cd "$ECC_DIR"
  npm install --no-audit --no-fund --loglevel=error
  node scripts/install-apply.js --profile minimal --target claude
  echo "[ECC] Installation complete."
fi

# ── Magic MCP ─────────────────────────────────────────────────────────────────
if claude mcp list 2>/dev/null | grep -q "^magic:"; then
  echo "[Magic] MCP already registered, skipping."
else
  echo "[Magic] Registering 21st.dev Magic MCP server ..."
  claude mcp add magic --scope user \
    --env API_KEY="${MAGIC_API_KEY:-}" \
    -- npx -y @21st-dev/magic@latest
  echo "[Magic] Registration complete."
fi
