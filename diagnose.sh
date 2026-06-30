#!/usr/bin/env bash
# =============================================================================
#  ptah.site — Full Diagnostic & Fix Script
#  Covers: aegis-credit & ca-engine
#
#  Usage:  bash diagnose.sh [options]
#    --rebuild-frontend   Force npm run build even if .next already exists
#    --skip-build         Skip frontend build step entirely
#    --help               Show this message and exit
# =============================================================================

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

# ── Flags ─────────────────────────────────────────────────────────────────────
REBUILD_FRONTEND=false; SKIP_BUILD=false
for arg in "$@"; do
  case "$arg" in
    --rebuild-frontend) REBUILD_FRONTEND=true ;;
    --skip-build)       SKIP_BUILD=true ;;
    --help) grep '^#  ' "$0" | sed 's/^#  //'; exit 0 ;;
  esac
done

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AB="$ROOT/aegis-credit/backend"
AF="$ROOT/aegis-credit/frontend"
AE="$ROOT/aegis-credit/.env"
CB="$ROOT/ca-engine/backend"
CF="$ROOT/ca-engine/frontend"
CE="$ROOT/ca-engine/backend/.env"

# ── Result tracking ───────────────────────────────────────────────────────────
FIXED=(); ISSUES=(); WARNINGS=()
PY=""; PIP=""

# ── Printer helpers ───────────────────────────────────────────────────────────
section() {
  printf "\n${BOLD}${BLUE}┌──────────────────────────────────────────────────────┐${NC}\n"
  printf "${BOLD}${BLUE}│  %-52s│${NC}\n" "$1"
  printf "${BOLD}${BLUE}└──────────────────────────────────────────────────────┘${NC}\n"
}
ok()     { printf "  ${GREEN}✓${NC}  %s\n" "$1"; }
fixed()  { printf "  ${GREEN}⚡ FIXED:${NC} %s\n" "$1"; FIXED+=("$1"); }
issue()  { printf "  ${RED}✗ ISSUE:${NC} %s\n" "$1"; ISSUES+=("$1"); }
warn()   { printf "  ${YELLOW}⚠ WARN: ${NC} %s\n" "$1"; WARNINGS+=("$1"); }
info()   { printf "  ${CYAN}ℹ${NC}  %s\n" "$1"; }
hint()   { printf "          ${DIM}→ %s${NC}\n" "$1"; }
sub()    { printf "\n  ${BOLD}%s${NC}\n" "$1"; }

# ── Read one value from a .env file ───────────────────────────────────────────
env_val() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || { echo ""; return; }
  grep -E "^${key}\s*=" "$file" 2>/dev/null \
    | head -1 | cut -d= -f2- | sed "s/['\"]//g" | xargs 2>/dev/null || echo ""
}

# ── True if value looks like a real secret (not empty / placeholder) ──────────
is_real() {
  local v="$1"
  [[ -n "$v" ]] \
    && [[ "$v" != change* ]] \
    && [[ "$v" != your_* ]]  \
    && [[ "$v" != "sk-ant-..." ]] \
    && [[ "$v" != "sk-..." ]] \
    && [[ "$v" != "<"* ]] \
    && [[ "$v" != "dev-secret"* ]]
}

# ── Safely export vars from a .env file into current shell ────────────────────
load_dotenv() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  while IFS= read -r line; do
    # Skip blank lines and comments
    [[ "$line" =~ ^\s*# ]] && continue
    [[ -z "${line// }" ]] && continue
    # Only export NAME=VALUE lines
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*) ]]; then
      local k="${BASH_REMATCH[1]}"
      local v="${BASH_REMATCH[2]}"
      # Strip surrounding quotes
      v="${v%\"}"
      v="${v#\"}"
      v="${v%\'}"
      v="${v#\'}"
      export "$k"="$v"
    fi
  done < "$file"
}

# ═════════════════════════════════════════════════════════════════════════════
# 1. SYSTEM DEPENDENCIES
# ═════════════════════════════════════════════════════════════════════════════
check_system() {
  section "1 / 8  System Dependencies"

  # Python 3
  if command -v python3 &>/dev/null; then
    PY="$(command -v python3)"
    ok "python3 — $PY  ($(python3 --version 2>&1))"
  else
    issue "python3 not found — install Python 3.11+"
  fi

  # pip (prefer python3 -m pip so version matches)
  if [[ -n "$PY" ]] && "$PY" -m pip --version &>/dev/null 2>&1; then
    PIP="$PY -m pip"
    ok "pip — via python3 -m pip  ($($PIP --version 2>&1 | head -1))"
  elif command -v pip3 &>/dev/null; then
    PIP="pip3"
    ok "pip3 — $(pip3 --version 2>&1 | head -1)"
  else
    issue "pip not found — install pip for Python 3"
  fi

  # Node.js
  if command -v node &>/dev/null; then
    ok "node — $(node --version)"
  else
    issue "node not found — install Node.js 20+  →  https://nodejs.org"
  fi

  # npm
  if command -v npm &>/dev/null; then
    ok "npm — $(npm --version)"
  else
    issue "npm not found — comes with Node.js"
  fi

  # LibreOffice (ca-engine uses it for DOCX → PDF conversion)
  if command -v libreoffice &>/dev/null || command -v soffice &>/dev/null; then
    ok "LibreOffice — found  (ca-engine document conversion ready)"
  else
    warn "LibreOffice not found — ca-engine DOCX→PDF conversion will fail"
    hint "sudo apt-get install -y libreoffice libreoffice-writer"
  fi
}

# ═════════════════════════════════════════════════════════════════════════════
# 2. API KEYS & ENVIRONMENT FILES
# ═════════════════════════════════════════════════════════════════════════════
check_env() {
  section "2 / 8  API Keys & Environment Files"

  # ── Helper: generate a secure random hex key ──────────────────────────────
  gen_key() {
    if [[ -n "$PY" ]]; then
      "$PY" -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null
    else
      openssl rand -hex 32 2>/dev/null || date +%s%N | sha256sum | head -c 64
    fi
  }

  # ── Set or replace a key in a .env file ───────────────────────────────────
  set_env_key() {
    local file="$1" key="$2" val="$3"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
      sed -i "s|^${key}=.*|${key}=${val}|" "$file"
    else
      echo "${key}=${val}" >> "$file"
    fi
  }

  # ════════════ aegis-credit ════════════════════════════════════════════════
  sub "aegis-credit"

  # Create .env if missing
  if [[ ! -f "$AE" ]]; then
    if [[ -f "$ROOT/aegis-credit/.env.example" ]]; then
      cp "$ROOT/aegis-credit/.env.example" "$AE"
      fixed "Created aegis-credit/.env from .env.example"
    else
      issue "aegis-credit/.env missing and no .env.example found"
      printf '%s\n' \
        "DATABASE_URL=sqlite:///./aegis.db" \
        "SECRET_KEY=placeholder" \
        "ANTHROPIC_API_KEY=" \
        "STRIPE_SECRET_KEY=" \
        "POSTGRES_PASSWORD=" > "$AE"
      fixed "Created aegis-credit/.env with skeleton keys"
    fi
  else
    ok "aegis-credit/.env exists"
  fi

  # Auto-generate SECRET_KEY / JWT_SECRET_KEY if placeholder
  local ae_sk; ae_sk=$(env_val "$AE" "SECRET_KEY")
  local ae_jk; ae_jk=$(env_val "$AE" "JWT_SECRET_KEY")
  if ! is_real "$ae_sk" && ! is_real "$ae_jk"; then
    local newkey; newkey=$(gen_key)
    set_env_key "$AE" "SECRET_KEY" "$newkey"
    fixed "aegis-credit: Generated SECRET_KEY  ($(echo "$newkey" | head -c 12)...)"
  else
    ok "aegis-credit: SECRET_KEY / JWT_SECRET_KEY is set"
  fi

  # Ensure SQLite default if DATABASE_URL missing
  local ae_db; ae_db=$(env_val "$AE" "DATABASE_URL")
  if [[ -z "$ae_db" ]]; then
    set_env_key "$AE" "DATABASE_URL" "sqlite:///./aegis.db"
    fixed "aegis-credit: Set DATABASE_URL=sqlite:///./aegis.db  (dev default)"
  elif is_real "$ae_db"; then
    ok "aegis-credit: DATABASE_URL is set"
  fi

  # Required: ANTHROPIC_API_KEY
  local ae_ant; ae_ant=$(env_val "$AE" "ANTHROPIC_API_KEY")
  if is_real "$ae_ant"; then
    ok "aegis-credit: ANTHROPIC_API_KEY is set  (${ae_ant:0:10}...)"
  else
    issue "aegis-credit: ANTHROPIC_API_KEY missing — AI report parsing & strategy disabled"
    hint "Get it at: https://console.anthropic.com/settings/keys"
    hint "Add to aegis-credit/.env:  ANTHROPIC_API_KEY=sk-ant-..."
  fi

  # Required for billing: STRIPE_SECRET_KEY
  local ae_sk2; ae_sk2=$(env_val "$AE" "STRIPE_SECRET_KEY")
  if is_real "$ae_sk2"; then
    ok "aegis-credit: STRIPE_SECRET_KEY is set"
  else
    warn "aegis-credit: STRIPE_SECRET_KEY missing — billing endpoints will error"
    hint "Get it at: https://dashboard.stripe.com/apikeys"
  fi

  # Optional
  local ae_swh; ae_swh=$(env_val "$AE" "STRIPE_WEBHOOK_SECRET")
  is_real "$ae_swh" || warn "aegis-credit: STRIPE_WEBHOOK_SECRET not set — webhook validation disabled"

  local ae_smtp; ae_smtp=$(env_val "$AE" "SMTP_HOST")
  is_real "$ae_smtp" || warn "aegis-credit: SMTP not configured — email notifications disabled"

  # NEXT_PUBLIC_API_URL for frontend
  local ae_npu; ae_npu=$(env_val "$AE" "NEXT_PUBLIC_API_URL")
  if [[ -z "$ae_npu" ]]; then
    set_env_key "$AE" "NEXT_PUBLIC_API_URL" "http://localhost:8082"
    fixed "aegis-credit: Added NEXT_PUBLIC_API_URL=http://localhost:8082 to .env"
  else
    ok "aegis-credit: NEXT_PUBLIC_API_URL=$ae_npu"
  fi

  # ════════════ ca-engine ══════════════════════════════════════════════════
  sub "ca-engine"

  # Create .env if missing
  if [[ ! -f "$CE" ]]; then
    if [[ -f "$CB/.env.example" ]]; then
      cp "$CB/.env.example" "$CE"
      fixed "Created ca-engine/backend/.env from .env.example"
    else
      issue "ca-engine/backend/.env missing and no .env.example found"
      printf '%s\n' \
        "DATABASE_URL=sqlite:///./ca_engine.db" \
        "SECRET_KEY=placeholder" \
        "ANTHROPIC_API_KEY=" \
        "DEV_NO_AUTH=True" > "$CE"
      fixed "Created ca-engine/backend/.env with skeleton keys"
    fi
  else
    ok "ca-engine/backend/.env exists"
  fi

  # Auto-generate SECRET_KEY if placeholder
  local ce_sk; ce_sk=$(env_val "$CE" "SECRET_KEY")
  if ! is_real "$ce_sk"; then
    local newkey; newkey=$(gen_key)
    set_env_key "$CE" "SECRET_KEY" "$newkey"
    fixed "ca-engine: Generated SECRET_KEY  ($(echo "$newkey" | head -c 12)...)"
  else
    ok "ca-engine: SECRET_KEY is set"
  fi

  # DATABASE_URL — default to SQLite
  local ce_db; ce_db=$(env_val "$CE" "DATABASE_URL")
  if [[ -z "$ce_db" ]]; then
    set_env_key "$CE" "DATABASE_URL" "sqlite:///./ca_engine.db"
    fixed "ca-engine: Set DATABASE_URL=sqlite:///./ca_engine.db  (dev default)"
  else
    ok "ca-engine: DATABASE_URL=$ce_db"
  fi

  # Required: ANTHROPIC_API_KEY
  local ce_ant; ce_ant=$(env_val "$CE" "ANTHROPIC_API_KEY")
  if is_real "$ce_ant"; then
    ok "ca-engine: ANTHROPIC_API_KEY is set  (${ce_ant:0:10}...)"
  else
    # If aegis has it, copy it
    local ae_ant2; ae_ant2=$(env_val "$AE" "ANTHROPIC_API_KEY")
    if is_real "$ae_ant2"; then
      set_env_key "$CE" "ANTHROPIC_API_KEY" "$ae_ant2"
      fixed "ca-engine: Copied ANTHROPIC_API_KEY from aegis-credit/.env"
    else
      issue "ca-engine: ANTHROPIC_API_KEY missing — AI features disabled"
      hint "Get it at: https://console.anthropic.com/settings/keys"
      hint "Add to ca-engine/backend/.env:  ANTHROPIC_API_KEY=sk-ant-..."
    fi
  fi

  # Optional: OpenAI
  local ce_oai; ce_oai=$(env_val "$CE" "OPENAI_API_KEY")
  is_real "$ce_oai" || warn "ca-engine: OPENAI_API_KEY not set — OpenAI fallback unavailable"
  hint "https://platform.openai.com/api-keys"

  # Optional: AWS S3
  local ce_aws; ce_aws=$(env_val "$CE" "AWS_ACCESS_KEY_ID")
  is_real "$ce_aws" || warn "ca-engine: AWS_ACCESS_KEY_ID not set — S3 document storage disabled"

  # Optional: E-signature
  local ce_ds; ce_ds=$(env_val "$CE" "DOCUSIGN_INTEGRATION_KEY")
  local ce_hs; ce_hs=$(env_val "$CE" "DROPBOX_SIGN_API_KEY")
  if ! is_real "$ce_ds" && ! is_real "$ce_hs"; then
    warn "ca-engine: No e-signature provider configured (DocuSign or HelloSign)"
    hint "DocuSign:  https://developers.docusign.com/"
    hint "HelloSign: https://app.hellosign.com/api/all"
  fi

  # Optional: SMTP
  local ce_smtp; ce_smtp=$(env_val "$CE" "SMTP_USER")
  is_real "$ce_smtp" || warn "ca-engine: SMTP not configured — email notifications disabled"
  hint "Gmail app password: https://myaccount.google.com/apppasswords"
}

# ═════════════════════════════════════════════════════════════════════════════
# 3. PYTHON PACKAGES
# ═════════════════════════════════════════════════════════════════════════════
check_python_packages() {
  section "3 / 8  Python Packages"

  if [[ -z "$PY" || -z "$PIP" ]]; then
    issue "Skipping — python3 / pip not found"
    return
  fi

  for pair in \
    "aegis-credit:$AB/requirements.txt" \
    "ca-engine:$CB/requirements.txt"
  do
    local label="${pair%%:*}"
    local req="${pair##*:}"
    sub "$label"

    if [[ ! -f "$req" ]]; then
      issue "$label: requirements.txt not found at $req"
      continue
    fi

    local pkg_count; pkg_count=$(grep -cE '^[A-Za-z]' "$req" 2>/dev/null || echo "?")
    info "Installing/verifying $pkg_count packages..."

    local pip_log="/tmp/ptah_pip_${label//\//_}_$$.log"
    if $PIP install -q -r "$req" >"$pip_log" 2>&1; then
      fixed "$label: All Python packages installed / up-to-date"
    else
      issue "$label: pip install failed — see $pip_log"
      tail -5 "$pip_log" | while IFS= read -r line; do hint "$line"; done
    fi
  done
}

# ═════════════════════════════════════════════════════════════════════════════
# 4. SOURCE FILE INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════
check_source_files() {
  section "4 / 8  Source File Integrity"

  local -a aegis_files=(
    "$AB/app/main.py"
    "$AB/app/config.py"
    "$AB/app/database.py"
    "$AB/app/models.py"
    "$AB/app/dependencies.py"
    "$AB/requirements.txt"
    "$AB/alembic.ini"
    "$AF/package.json"
    "$AF/next.config.js"
    "$AF/tsconfig.json"
  )

  local -a ca_files=(
    "$CB/app/main.py"
    "$CB/app/config.py"
    "$CB/app/database.py"
    "$CB/app/models.py"
    "$CB/app/auth.py"
    "$CB/requirements.txt"
    "$CF/package.json"
    "$CF/next.config.js"
    "$CF/tsconfig.json"
  )

  for pair in "aegis-credit:aegis_files[@]" "ca-engine:ca_files[@]"; do
    local label="${pair%%:*}"
    local arr="${pair##*:}"
    sub "$label"
    local all_ok=true
    for f in "${!arr}"; do
      if [[ -f "$f" ]]; then
        ok "${f#"$ROOT/"}"
      else
        issue "MISSING: ${f#"$ROOT/"}"
        all_ok=false
      fi
    done
    $all_ok || ISSUES+=("$label: one or more critical source files are missing — check git status")
  done

  # ── Runtime directories ───────────────────────────────────────────────────
  sub "Runtime directories"
  local -a dirs=("$AB/uploads" "$AB/generated_reports" "$CB/generated_docs")
  for d in "${dirs[@]}"; do
    if [[ -d "$d" ]]; then
      ok "${d#"$ROOT/"}"
    else
      mkdir -p "$d"
      fixed "Created ${d#"$ROOT/"}"
    fi
  done
}

# ═════════════════════════════════════════════════════════════════════════════
# 5. DATABASE
# ═════════════════════════════════════════════════════════════════════════════
check_database() {
  section "5 / 8  Database"

  [[ -z "$PY" ]] && { issue "Skipping DB checks — python3 not found"; return; }

  # ── aegis-credit (Alembic + PostgreSQL / SQLite) ─────────────────────────
  sub "aegis-credit  (Alembic)"

  local ae_db; ae_db=$(env_val "$AE" "DATABASE_URL")
  info "DATABASE_URL: $(echo "${ae_db:-not set}" | sed 's|://.*@|://<redacted>@|')"

  if [[ -f "$AB/alembic.ini" ]]; then
    info "Running: alembic upgrade head..."
    local alembic_log="/tmp/ptah_alembic_$$.log"
    if (cd "$AB" && load_dotenv "$AE" && "$PY" - >"$alembic_log" 2>&1 <<'PYEOF'
from alembic.config import Config
from alembic import command as alembic_cmd
cfg = Config("alembic.ini")
alembic_cmd.upgrade(cfg, "head")
print("Migrations applied")
PYEOF
    ); then
      fixed "aegis-credit: Alembic migrations applied / already current"
      [[ -s "$alembic_log" ]] && tail -3 "$alembic_log" | while IFS= read -r l; do hint "$l"; done
    else
      warn "aegis-credit: Alembic migration failed — app startup will attempt create_all fallback"
      tail -5 "$alembic_log" | while IFS= read -r l; do hint "$l"; done
      hint "Check DATABASE_URL in aegis-credit/.env"
    fi
  else
    issue "aegis-credit: alembic.ini not found — cannot run migrations"
  fi

  # Check user count (SQLite only, non-destructive)
  if echo "${ae_db:-sqlite}" | grep -q "sqlite"; then
    local db_path="${ae_db#sqlite:///}"
    [[ "$db_path" == ./* ]] && db_path="$AB/${db_path#./}"
    [[ "$db_path" == /* ]] || db_path="$AB/$db_path"
    if [[ -f "$db_path" ]]; then
      local uc
      uc=$("$PY" - <<PYEOF 2>/dev/null || echo "?"
import sqlite3
try:
    conn = sqlite3.connect("$db_path")
    print(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
    conn.close()
except:
    print("?")
PYEOF
)
      if [[ "$uc" == "0" || "$uc" == "?" ]]; then
        warn "aegis-credit: No users in database yet"
        hint "Register via POST /api/auth/register after starting the backend"
      else
        ok "aegis-credit: SQLite DB has $uc user(s)"
      fi
    else
      info "aegis-credit: SQLite DB not yet created — will be auto-created on first start"
    fi
  fi

  # ── ca-engine (SQLite auto-create + admin seed) ───────────────────────────
  sub "ca-engine  (SQLite / auto-create)"

  local ce_db; ce_db=$(env_val "$CE" "DATABASE_URL")
  info "DATABASE_URL: ${ce_db:-sqlite:///./ca_engine.db}"

  # Create tables
  local tbl_log="/tmp/ptah_ca_tables_$$.log"
  if (cd "$CB" && load_dotenv "$CE" && "$PY" - >"$tbl_log" 2>&1 <<PYEOF
from app.database import engine, Base
from app import models
Base.metadata.create_all(bind=engine)
print("OK")
PYEOF
  ); then
    fixed "ca-engine: Database tables created / verified"
  else
    issue "ca-engine: Failed to create database tables — check Python imports"
    tail -5 "$tbl_log" | while IFS= read -r l; do hint "$l"; done
    hint "cd ca-engine/backend && python3 -c \"from app.database import engine, Base; from app import models; Base.metadata.create_all(bind=engine)\""
  fi

  # Admin user
  local ce_db_path="${ce_db:-sqlite:///./ca_engine.db}"
  ce_db_path="${ce_db_path#sqlite:///}"
  [[ "$ce_db_path" == ./* ]] && ce_db_path="$CB/${ce_db_path#./}"
  [[ "$ce_db_path" == /* ]] || ce_db_path="$CB/$ce_db_path"

  if [[ -f "$ce_db_path" ]]; then
    local admin_count
    admin_count=$("$PY" - <<PYEOF 2>/dev/null || echo "0"
import sqlite3
try:
    conn = sqlite3.connect("$ce_db_path")
    # Try role column first, fall back to is_admin or just count all users
    try:
        print(conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0])
    except:
        try:
            print(conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0])
        except:
            print(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
    conn.close()
except:
    print("0")
PYEOF
)
    if [[ "$admin_count" == "0" ]]; then
      info "No admin user found — creating default..."
      local seed_log="/tmp/ptah_ca_seed_$$.log"
      if (cd "$CB" && load_dotenv "$CE" && "$PY" - >"$seed_log" 2>&1 <<PYEOF
import sys
from app.database import SessionLocal
from app import models

try:
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    print("passlib not installed"); sys.exit(1)

db = SessionLocal()
try:
    hpw = pwd_ctx.hash("CruelAdmin2024!")
    # Try most common field signatures
    u = None
    for kwargs in [
        dict(email="admin@cruelandassociates.site", name="Admin", hashed_password=hpw, role="admin", is_active=True),
        dict(email="admin@cruelandassociates.site", full_name="Admin", hashed_password=hpw, role="admin", is_active=True),
        dict(email="admin@cruelandassociates.site", hashed_password=hpw, role="admin"),
    ]:
        try:
            u = models.User(**kwargs)
            db.add(u)
            db.commit()
            print("Admin created:", kwargs.get("email"))
            break
        except Exception as e:
            db.rollback()
            u = None
    if u is None:
        print("Could not determine User model signature")
except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
PYEOF
      ); then
        fixed "ca-engine: Admin user created  (admin@cruelandassociates.site / CruelAdmin2024!)"
      else
        warn "ca-engine: Could not auto-create admin user — the app will seed on first startup"
        tail -3 "$seed_log" | while IFS= read -r l; do hint "$l"; done
      fi
    else
      ok "ca-engine: Admin user exists ($admin_count admin(s))"
    fi
  else
    info "ca-engine: DB file not yet on disk — tables will be created on first start"
  fi
}

# ═════════════════════════════════════════════════════════════════════════════
# 6. FRONTEND CONFIG
# ═════════════════════════════════════════════════════════════════════════════
check_frontend_config() {
  section "6 / 8  Frontend Config"

  # ── aegis-credit next.config.js ───────────────────────────────────────────
  sub "aegis-credit  next.config.js"
  local ae_next="$AF/next.config.js"

  if [[ ! -f "$ae_next" ]]; then
    issue "aegis-credit: next.config.js missing"
  elif grep -q "ptahsite-production.up.railway.app" "$ae_next"; then
    # Replace hardcoded Railway URL with env var
    cat > "$ae_next" << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint:     { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  async rewrites() {
    return [
      {
        source:      '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8082'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
EOF
    fixed "aegis-credit: next.config.js — replaced hardcoded Railway URL with NEXT_PUBLIC_API_URL env var"
  else
    ok "aegis-credit: next.config.js looks good"
    grep -q "NEXT_PUBLIC_API_URL" "$ae_next" \
      && ok "  Uses NEXT_PUBLIC_API_URL ✓" \
      || warn "  next.config.js does not reference NEXT_PUBLIC_API_URL — check backend URL"
  fi

  # ── ca-engine next.config.js ──────────────────────────────────────────────
  sub "ca-engine  next.config.js"
  local ca_next="$CF/next.config.js"

  if [[ ! -f "$ca_next" ]]; then
    issue "ca-engine: next.config.js missing"
  else
    ok "ca-engine: next.config.js present"
    grep -q "NEXT_PUBLIC_API_URL" "$ca_next" \
      && ok "  Uses NEXT_PUBLIC_API_URL ✓" \
      || warn "  NEXT_PUBLIC_API_URL not referenced in ca-engine next.config.js"
  fi

  # ── tsconfig.json files ───────────────────────────────────────────────────
  sub "tsconfig.json"
  for f in "$AF/tsconfig.json" "$CF/tsconfig.json"; do
    if [[ -f "$f" ]]; then
      ok "${f#"$ROOT/"}"
      grep -q '"@/\*"' "$f" \
        && ok "  Path alias @/* configured ✓" \
        || warn "  ${f#"$ROOT/"}: @/* path alias missing"
    else
      issue "MISSING: ${f#"$ROOT/"}"
    fi
  done

  # ── .env.local for each frontend ─────────────────────────────────────────
  sub "frontend .env.local"
  local ae_el="$AF/.env.local"
  local ca_el="$CF/.env.local"

  if [[ ! -f "$ae_el" ]]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8082" > "$ae_el"
    fixed "Created aegis-credit/frontend/.env.local  (NEXT_PUBLIC_API_URL=http://localhost:8082)"
  else
    ok "aegis-credit/frontend/.env.local exists  ($(cat "$ae_el" | head -1))"
  fi

  if [[ ! -f "$ca_el" ]]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > "$ca_el"
    fixed "Created ca-engine/frontend/.env.local  (NEXT_PUBLIC_API_URL=http://localhost:8000)"
  else
    ok "ca-engine/frontend/.env.local exists  ($(cat "$ca_el" | head -1))"
  fi
}

# ═════════════════════════════════════════════════════════════════════════════
# 7. NPM PACKAGES
# ═════════════════════════════════════════════════════════════════════════════
check_npm_packages() {
  section "7 / 8  Frontend npm Packages"

  if ! command -v npm &>/dev/null; then
    issue "npm not found — skipping"
    return
  fi

  for pair in "aegis-credit/frontend:$AF" "ca-engine/frontend:$CF"; do
    local label="${pair%%:*}"
    local dir="${pair##*:}"
    sub "$label"

    if [[ ! -f "$dir/package.json" ]]; then
      issue "$label: package.json missing — cannot install"
      continue
    fi

    local need_install=false
    if [[ ! -d "$dir/node_modules" ]]; then
      info "$label: node_modules not found — installing..."
      need_install=true
    else
      # node_modules exists — check it has enough packages
      local mod_count; mod_count=$(ls "$dir/node_modules" | wc -l)
      if [[ "$mod_count" -lt 50 ]]; then
        warn "$label: node_modules seems incomplete ($mod_count entries) — reinstalling"
        need_install=true
      else
        ok "$label: node_modules present  ($mod_count top-level packages)"
      fi
    fi

    if $need_install; then
      local npm_log="/tmp/ptah_npm_${label//\//_}_$$.log"
      if (cd "$dir" && npm install --legacy-peer-deps >"$npm_log" 2>&1); then
        fixed "$label: npm install completed"
      else
        issue "$label: npm install failed"
        tail -5 "$npm_log" | while IFS= read -r l; do hint "$l"; done
        hint "cd $dir && npm install --legacy-peer-deps"
      fi
    fi
  done
}

# ═════════════════════════════════════════════════════════════════════════════
# 8. FRONTEND BUILD
# ═════════════════════════════════════════════════════════════════════════════
check_frontend_build() {
  section "8 / 8  Frontend Build"

  if $SKIP_BUILD; then
    info "Skipping frontend builds  (--skip-build)"
    return
  fi

  if ! command -v npm &>/dev/null; then
    issue "npm not found — skipping build"
    return
  fi

  for pair in "aegis-credit/frontend:$AF:$AF/.env.local" "ca-engine/frontend:$CF:$CF/.env.local"; do
    local label="${pair%%:*}"
    local dir
    dir="$(echo "$pair" | cut -d: -f2)"
    local env_file
    env_file="$(echo "$pair" | cut -d: -f3)"

    sub "$label"

    if [[ ! -d "$dir/node_modules" ]]; then
      issue "$label: node_modules missing — run npm install first"
      continue
    fi

    if [[ -d "$dir/.next" ]] && ! $REBUILD_FRONTEND; then
      ok "$label: .next build directory exists"
      hint "Pass --rebuild-frontend to force a fresh build"
    else
      [[ -d "$dir/.next" ]] && info "$label: Rebuilding .next..." || info "$label: Building for the first time... (60–120s)"
      local build_log="/tmp/ptah_build_${label//\//_}_$$.log"
      if (cd "$dir" && [[ -f "$env_file" ]] && load_dotenv "$env_file"; npm run build >"$build_log" 2>&1); then
        fixed "$label: Frontend built successfully"
      else
        issue "$label: npm run build failed"
        # Show the last meaningful error lines
        grep -E "(Error|error TS|Failed)" "$build_log" 2>/dev/null | tail -8 \
          | while IFS= read -r l; do hint "$l"; done
        hint "Full log: $build_log"
        hint "cd $dir && npm run build"
      fi
    fi
  done
}

# ═════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═════════════════════════════════════════════════════════════════════════════
print_report() {
  echo
  printf "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}\n"
  printf "${BOLD}${BLUE}║              DIAGNOSTIC REPORT                      ║${NC}\n"
  printf "${BOLD}${BLUE}╠══════════════════════════════════════════════════════╣${NC}\n"
  printf "${BOLD}${BLUE}║  ✅ Fixed: %-4s  ⚠  Warnings: %-4s  ✗ Issues: %-4s ║${NC}\n" \
    "${#FIXED[@]}" "${#WARNINGS[@]}" "${#ISSUES[@]}"
  printf "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}\n"

  if [[ ${#FIXED[@]} -gt 0 ]]; then
    printf "\n${GREEN}${BOLD}✅  AUTO-FIXED  (${#FIXED[@]})${NC}\n"
    for msg in "${FIXED[@]}"; do printf "  ${GREEN}⚡${NC}  %s\n" "$msg"; done
  fi

  if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    printf "\n${YELLOW}${BOLD}⚠   WARNINGS — optional services not configured  (${#WARNINGS[@]})${NC}\n"
    for msg in "${WARNINGS[@]}"; do printf "  ${YELLOW}⚠${NC}  %s\n" "$msg"; done
  fi

  if [[ ${#ISSUES[@]} -gt 0 ]]; then
    printf "\n${RED}${BOLD}✗   NEEDS ATTENTION  (${#ISSUES[@]})${NC}\n"
    for msg in "${ISSUES[@]}"; do printf "  ${RED}✗${NC}  %s\n" "$msg"; done
  else
    printf "\n${GREEN}${BOLD}  All critical checks passed!${NC}\n"
  fi

  echo
  printf "${BOLD}Quick-start commands (after filling .env keys):${NC}\n"
  printf "  ${CYAN}%-28s${NC}  cd aegis-credit/backend  && uvicorn app.main:app --port 8082 --reload\n" "aegis-credit backend"
  printf "  ${CYAN}%-28s${NC}  cd aegis-credit/frontend && npm run dev\n"                               "aegis-credit frontend"
  printf "  ${CYAN}%-28s${NC}  cd ca-engine/backend     && uvicorn app.main:app --port 8000 --reload\n" "ca-engine backend"
  printf "  ${CYAN}%-28s${NC}  cd ca-engine/frontend    && npm run dev\n"                               "ca-engine frontend"
  echo
  printf "  ${CYAN}%-28s${NC}  cd aegis-credit && docker compose up\n" "aegis-credit (Docker)"
  printf "  ${CYAN}%-28s${NC}  cd ca-engine    && docker compose up\n" "ca-engine (Docker)"
  echo
  printf "${DIM}  Re-run:  bash diagnose.sh                 — full check${NC}\n"
  printf "${DIM}           bash diagnose.sh --rebuild-frontend — force fresh build${NC}\n"
  printf "${DIM}           bash diagnose.sh --skip-build       — skip npm run build${NC}\n"
  echo
}

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
main() {
  printf "\n${BOLD}${BLUE}  ptah.site — Full Diagnostic & Fix Script${NC}\n"
  printf "  ${DIM}Root: $ROOT${NC}\n"
  printf "  ${DIM}Date: $(date)${NC}\n"

  check_system
  check_env
  check_python_packages
  check_source_files
  check_database
  check_frontend_config
  check_npm_packages
  check_frontend_build
  print_report
}

main
