#!/usr/bin/env python3
"""
Aegis Credit — Full System Diagnostic & Auto-Repair
=====================================================
Usage:
  python diagnose.py                   # check everything, fix nothing
  python diagnose.py --fix             # check + auto-fix what's possible
  python diagnose.py --fix --admin     # also create/reset admin user
  python diagnose.py --fix --admin --admin-email admin@example.com --admin-pass Secret123!

Run from: aegis-credit/backend/
"""

import os
import sys
import json
import re
import subprocess
import importlib
import argparse
from pathlib import Path
from datetime import datetime

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

FIXED    = []
BROKEN   = []
WARNINGS = []

def ok(msg):      print(f"  {GREEN}✅ {msg}{RESET}")
def warn(msg):    WARNINGS.append(msg); print(f"  {YELLOW}⚠️  {msg}{RESET}")
def fail(msg):    BROKEN.append(msg);   print(f"  {RED}❌ {msg}{RESET}")
def fixed(msg):   FIXED.append(msg);    print(f"  {GREEN}🔧 FIXED: {msg}{RESET}")
def info(msg):    print(f"  {BLUE}ℹ️  {msg}{RESET}")
def section(t):   print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}\n{BOLD}  {t}{RESET}\n{BOLD}{CYAN}{'═'*60}{RESET}")
def sub(t):       print(f"\n{BOLD}  {t}{RESET}")

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Aegis Credit diagnostic & repair")
parser.add_argument("--fix",           action="store_true", help="Auto-fix issues where possible")
parser.add_argument("--admin",         action="store_true", help="Create/reset admin user")
parser.add_argument("--admin-email",   default="admin@aegis.local", help="Admin email")
parser.add_argument("--admin-pass",    default="Admin123!",         help="Admin password")
parser.add_argument("--frontend",      action="store_true", help="Include frontend checks (slower)")
args = parser.parse_args()

FIX      = args.fix
DO_ADMIN = args.admin

print(f"\n{BOLD}{CYAN}Aegis Credit — System Diagnostic{RESET}")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  mode: {'FIX' if FIX else 'CHECK ONLY'}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. PYTHON PACKAGES
# ══════════════════════════════════════════════════════════════════════════════
section("1 · Python Packages")

REQUIRED_PACKAGES = [
    ("fastapi",          "fastapi"),
    ("uvicorn",          "uvicorn"),
    ("sqlalchemy",       "sqlalchemy"),
    ("psycopg2-binary",  "psycopg2"),
    ("pydantic",         "pydantic"),
    ("pydantic-settings","pydantic_settings"),
    ("anthropic",        "anthropic"),
    ("python-jose",      "jose"),
    ("passlib",          "passlib"),
    ("bcrypt",           "bcrypt"),
    ("aiofiles",         "aiofiles"),
    ("reportlab",        "reportlab"),
    ("alembic",          "alembic"),
    ("stripe",           "stripe"),
    ("pdfplumber",       "pdfplumber"),
    ("python-multipart", "multipart"),
    ("aiosmtplib",       "aiosmtplib"),
]

missing_pkgs = []
for pip_name, import_name in REQUIRED_PACKAGES:
    try:
        importlib.import_module(import_name)
        ok(f"{pip_name}")
    except ImportError:
        missing_pkgs.append(pip_name)
        fail(f"{pip_name}  ← NOT INSTALLED")

if missing_pkgs:
    if FIX:
        info(f"Installing {len(missing_pkgs)} missing package(s)…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir"] + missing_pkgs,
            capture_output=True, text=True
        )
        if result.returncode == 0:
            fixed(f"Installed: {', '.join(missing_pkgs)}")
        else:
            fail(f"pip install failed:\n{result.stderr[:500]}")
    else:
        warn(f"Run with --fix to install: pip install {' '.join(missing_pkgs)}")
else:
    ok("All packages installed")


# ══════════════════════════════════════════════════════════════════════════════
# 2. ENVIRONMENT VARIABLES
# ══════════════════════════════════════════════════════════════════════════════
section("2 · Environment Variables")

# Load .env file if present (local dev)
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    info(f"Loading {env_file}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

ENV_CHECKS = [
    {
        "key": "DATABASE_URL",
        "required": True,
        "validator": lambda v: v.startswith("postgresql://") and "PASSWORD" not in v and len(v) > 30,
        "hint": "Must be a real PostgreSQL URL from Railway Postgres → Connect tab.\n"
                "     In Railway backend Variables, set:  DATABASE_URL = ${{ Postgres.DATABASE_URL }}",
        "safe_display": lambda v: re.sub(r'://([^:]+):[^@]+@', r'://\1:***@', v)[:80],
    },
    {
        "key": "ANTHROPIC_API_KEY",
        "required": True,
        "validator": lambda v: v.startswith("sk-ant-api03-") and len(v) >= 100,
        "hint": "Get from: https://console.anthropic.com → API Keys\n"
                "     Must start with sk-ant-api03- and be ~108 characters",
        "safe_display": lambda v: f"{v[:18]}...({len(v)} chars)",
    },
    {
        "key": "STRIPE_SECRET_KEY",
        "required": True,
        "validator": lambda v: (v.startswith("sk_live_") or v.startswith("sk_test_")) and len(v) > 50,
        "hint": "Get from: https://dashboard.stripe.com → Developers → API Keys\n"
                "     Must start with sk_live_ or sk_test_ and be ~107 characters",
        "safe_display": lambda v: f"{v[:12]}...({len(v)} chars)",
    },
    {
        "key": "STRIPE_PUBLISHABLE_KEY",
        "required": False,
        "validator": lambda v: v.startswith("pk_live_") or v.startswith("pk_test_"),
        "hint": "Get from: Stripe dashboard → Developers → API Keys (publishable key)",
        "safe_display": lambda v: f"{v[:14]}...({len(v)} chars)",
    },
    {
        "key": "STRIPE_WEBHOOK_SECRET",
        "required": False,
        "validator": lambda v: v.startswith("whsec_") and len(v) > 20,
        "hint": "Get from: Stripe dashboard → Developers → Webhooks → your endpoint → Signing secret",
        "safe_display": lambda v: f"{v[:10]}...({len(v)} chars)",
    },
    {
        "key": "STRIPE_PRICE_ID",
        "required": False,
        "validator": lambda v: v.startswith("price_") and len(v) > 10,
        "hint": "Get from: Stripe dashboard → Products → your subscription → Price ID",
        "safe_display": lambda v: v,
    },
    {
        "key": "JWT_SECRET_KEY",
        "required": True,
        "validator": lambda v: v not in ("", "change-me-in-production-use-env-var", "change-me", "secret") and len(v) >= 16,
        "hint": "Set any strong random string (32+ chars). Generate with:\n"
                "     python -c \"import secrets; print(secrets.token_hex(32))\"",
        "safe_display": lambda v: f"SET ({len(v)} chars)",
    },
]

env_ok = True
for chk in ENV_CHECKS:
    key      = chk["key"]
    val      = os.environ.get(key, "")
    required = chk["required"]
    label    = "required" if required else "optional"

    if not val:
        if required:
            env_ok = False
            fail(f"{key}  ← NOT SET ({label})")
            info(f"     ➜  {chk['hint']}")
        else:
            warn(f"{key}  ← not set ({label})")
            info(f"     ➜  {chk['hint']}")
        continue

    display = chk["safe_display"](val)
    if chk["validator"](val):
        ok(f"{key} = {display}")
    else:
        env_ok = False
        status = "INVALID" if required else "MAY BE WRONG"
        (fail if required else warn)(f"{key} = {display}  ← {status}")
        info(f"     ➜  {chk['hint']}")

if env_ok:
    ok("All required environment variables look correct")


# ══════════════════════════════════════════════════════════════════════════════
# 3. SOURCE FILES
# ══════════════════════════════════════════════════════════════════════════════
section("3 · Source Files")

BASE = Path(__file__).parent

CRITICAL_FILES = [
    "app/main.py",
    "app/config.py",
    "app/database.py",
    "app/models.py",
    "app/routers/__init__.py",
    "app/services/ai_service.py",
    "alembic.ini",
    "requirements.txt",
]

ROUTER_FILES = [
    "app/routers/auth.py",
    "app/routers/clients.py",
    "app/routers/cases.py",
    "app/routers/reports.py",
    "app/routers/billing.py",
    "app/routers/portal.py",
    "app/routers/disputes.py",
    "app/routers/tradelines.py",
    "app/routers/findings.py",
    "app/routers/analytics.py",
]

files_ok = True
for rel in CRITICAL_FILES:
    p = BASE / rel
    if p.exists() and p.stat().st_size > 0:
        ok(f"{rel}")
    else:
        files_ok = False
        fail(f"{rel}  ← MISSING OR EMPTY")

sub("Routers")
for rel in ROUTER_FILES:
    p = BASE / rel
    if p.exists():
        ok(f"{rel}")
    else:
        fail(f"{rel}  ← MISSING")
        files_ok = False

if files_ok:
    ok("All critical source files present")


# ══════════════════════════════════════════════════════════════════════════════
# 4. DATABASE
# ══════════════════════════════════════════════════════════════════════════════
section("4 · Database")

db_url = os.environ.get("DATABASE_URL", "")
db_ok  = False

if not db_url or not db_url.startswith("postgresql"):
    fail("DATABASE_URL not set or not PostgreSQL — skipping DB checks")
    BROKEN.append("DATABASE_URL must be set to a valid PostgreSQL URL")
else:
    try:
        sys.path.insert(0, str(BASE))
        from sqlalchemy import create_engine, text, inspect as sa_inspect

        engine = create_engine(
            db_url,
            connect_args={"connect_timeout": 10},
            pool_pre_ping=True,
        )

        sub("Connection test")
        with engine.connect() as conn:
            row = conn.execute(text("SELECT current_database(), version()")).fetchone()
        ok(f"Connected — db={row[0]}, pg={row[1][:50]}")

        sub("Table inventory")
        insp   = sa_inspect(engine)
        tables = set(insp.get_table_names())

        REQUIRED_TABLES = [
            "users", "organizations", "aegis_clients", "aegis_cases",
            "aegis_tradelines", "aegis_findings", "aegis_reports",
            "audit_logs", "billing_plans", "client_documents",
        ]
        missing_tables = [t for t in REQUIRED_TABLES if t not in tables]

        for t in REQUIRED_TABLES:
            (ok if t in tables else fail)(t)

        if missing_tables:
            info(f"Missing tables: {', '.join(missing_tables)}")
            if FIX:
                info("Running Alembic migrations…")
                try:
                    from alembic.config import Config
                    from alembic import command

                    base_dir = str(BASE)
                    alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
                    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))

                    existing = insp.get_table_names()
                    if "alembic_version" not in existing and "users" in existing:
                        command.stamp(alembic_cfg, "heads")
                    command.upgrade(alembic_cfg, "heads")
                    fixed("Alembic migrations applied")
                except Exception as exc:
                    warn(f"Alembic failed ({exc}), trying create_all fallback…")
                    try:
                        os.environ["PYTHONPATH"] = str(BASE)
                        import app.models
                        from app.database import Base
                        Base.metadata.create_all(bind=engine)
                        fixed("Tables created via create_all")
                    except Exception as e2:
                        fail(f"create_all also failed: {e2}")
        else:
            ok("All required tables exist")

        sub("Alembic version")
        try:
            with engine.connect() as conn:
                row2 = conn.execute(text("SELECT version FROM alembic_version")).fetchone()
            ok(f"Alembic head: {row2[0] if row2 else 'empty'}")
        except Exception:
            warn("No alembic_version table — migrations have never run")

        sub("User count")
        try:
            with engine.connect() as conn:
                cnt = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            ok(f"{cnt} user(s) in database")
            if cnt == 0:
                warn("No users — app will need an admin account")
        except Exception as exc:
            warn(f"Could not count users: {exc}")

        db_ok = True

    except Exception as exc:
        fail(f"Database connection failed: {exc}")
        info("Fix: ensure DATABASE_URL is correct in Railway → Variables")
        BROKEN.append(f"DB connection failed: {exc}")


# ── Admin user creation ───────────────────────────────────────────────────────
if DO_ADMIN and db_ok:
    sub("Admin user")
    try:
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

        with engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :e"),
                {"e": args.admin_email}
            ).fetchone()

            hashed = pwd_ctx.hash(args.admin_pass)
            if existing:
                conn.execute(
                    text("UPDATE users SET hashed_password = :p, role = 'admin' WHERE email = :e"),
                    {"p": hashed, "e": args.admin_email}
                )
                fixed(f"Admin password reset for {args.admin_email}")
            else:
                conn.execute(
                    text(
                        "INSERT INTO users (email, hashed_password, role, is_active, created_at) "
                        "VALUES (:e, :p, 'admin', true, NOW())"
                    ),
                    {"e": args.admin_email, "p": hashed}
                )
                fixed(f"Admin user created: {args.admin_email} / {args.admin_pass}")
    except Exception as exc:
        fail(f"Admin user setup failed: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. FRONTEND CONFIG
# ══════════════════════════════════════════════════════════════════════════════
section("5 · Frontend Config")

FRONTEND = BASE.parent / "frontend"
if not FRONTEND.exists():
    warn("Frontend directory not found at ../frontend — skipping")
else:
    sub("next.config.js")
    next_cfg = FRONTEND / "next.config.js"
    if next_cfg.exists():
        content = next_cfg.read_text()
        if "ptahsite-production.up.railway.app" in content or "railway.app" in content:
            ok("next.config.js — API rewrite points to Railway backend")
        elif "/api/:path*" in content:
            warn("next.config.js has a rewrite but destination may not point to Railway")
            info("Expected: destination: 'https://ptahsite-production.up.railway.app/api/:path*'")
        else:
            fail("next.config.js — missing /api/* rewrite rule")
            if FIX:
                new_content = content.replace(
                    "module.exports = nextConfig;",
                    """  async rewrites() {
    return [{
      source: '/api/:path*',
      destination: 'https://ptahsite-production.up.railway.app/api/:path*',
    }];
  },
};

module.exports = nextConfig;"""
                )
                if new_content != content:
                    next_cfg.write_text(new_content)
                    fixed("Added API rewrite to next.config.js")
    else:
        fail("next.config.js not found")

    sub(".env.local")
    env_local = FRONTEND / ".env.local"
    if env_local.exists():
        env_content = env_local.read_text()
        pub_api = ""
        for line in env_content.splitlines():
            if line.startswith("NEXT_PUBLIC_API_URL"):
                pub_api = line.split("=", 1)[-1].strip()
        if pub_api:
            ok(f"NEXT_PUBLIC_API_URL = {pub_api}")
        else:
            warn("NEXT_PUBLIC_API_URL is not set in .env.local")
            if FIX:
                new_env = env_content.rstrip() + "\nNEXT_PUBLIC_API_URL=https://ptahsite-production.up.railway.app\n"
                env_local.write_text(new_env)
                fixed("Set NEXT_PUBLIC_API_URL in frontend/.env.local")
    else:
        warn(".env.local not found")
        if FIX:
            env_local.write_text("NEXT_PUBLIC_API_URL=https://ptahsite-production.up.railway.app\n")
            fixed("Created frontend/.env.local")

    sub("tsconfig.json")
    tsconfig = FRONTEND / "tsconfig.json"
    if tsconfig.exists():
        try:
            cfg = json.loads(tsconfig.read_text())
            ok(f"tsconfig.json valid JSON  (target: {cfg.get('compilerOptions',{}).get('target','?')})")
        except json.JSONDecodeError as exc:
            fail(f"tsconfig.json invalid JSON: {exc}")
            BROKEN.append("tsconfig.json is not valid JSON")
    else:
        fail("tsconfig.json not found")

    sub("node_modules")
    nm = FRONTEND / "node_modules"
    if nm.exists() and any(nm.iterdir()):
        ok("node_modules present")
    else:
        warn("node_modules missing or empty")
        if FIX:
            info("Running npm install…")
            result = subprocess.run(["npm", "install"], cwd=str(FRONTEND), capture_output=True, text=True)
            if result.returncode == 0:
                fixed("npm install completed")
            else:
                fail(f"npm install failed:\n{result.stderr[:300]}")

    if args.frontend:
        sub("Frontend build")
        next_build = FRONTEND / ".next" / "BUILD_ID"
        if next_build.exists():
            ok(f".next build exists (BUILD_ID: {next_build.read_text().strip()})")
        else:
            warn(".next build not found")
            if FIX:
                info("Running npm run build… (this may take 60–90 seconds)")
                result = subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND), capture_output=True, text=True, timeout=180)
                if result.returncode == 0:
                    fixed("Frontend build succeeded")
                else:
                    fail(f"Frontend build failed:\n{result.stderr[:500]}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
section("6 · Summary Report")

if FIXED:
    print(f"\n{GREEN}{BOLD}  ✅ Fixed ({len(FIXED)}):{RESET}")
    for m in FIXED:
        print(f"     • {m}")

if WARNINGS:
    print(f"\n{YELLOW}{BOLD}  ⚠️  Warnings ({len(WARNINGS)}):{RESET}")
    for m in WARNINGS:
        print(f"     • {m}")

if BROKEN:
    print(f"\n{RED}{BOLD}  ❌ Broken — needs manual action ({len(BROKEN)}):{RESET}")
    for m in BROKEN:
        print(f"     • {m}")
    print(f"""
{BOLD}  Quick fixes:{RESET}
  1. Railway → backend service → Variables → set:
       DATABASE_URL      = ${{{{ Postgres.DATABASE_URL }}}}
       ANTHROPIC_API_KEY = <108-char key from console.anthropic.com>
       STRIPE_SECRET_KEY = <107-char key from dashboard.stripe.com>
       JWT_SECRET_KEY    = <any 32+ char random string>

  2. Re-run:  python diagnose.py --fix --admin
""")
else:
    print(f"\n{GREEN}{BOLD}  🎉 All checks passed!{RESET}")
    if not FIX:
        print(f"  Run with --fix to auto-repair any warnings.")

total_issues = len(BROKEN) + len(WARNINGS)
emoji = "🟢" if not BROKEN else "🔴"
print(f"\n  {emoji}  {len(FIXED)} fixed · {len(WARNINGS)} warnings · {len(BROKEN)} broken\n")
