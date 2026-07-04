import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

import app.models  # ensure all models are registered

from app.routers.clients import router as clients_router
from app.routers.cases import router as cases_router
from app.routers.reports import router as reports_router
from app.routers.tradelines import router as tradelines_router
from app.routers.comparison import router as comparison_router
from app.routers.findings import router as findings_router
from app.routers.evidence import router as evidence_router
from app.routers.court_records import router as court_records_router
from app.routers.timeline import router as timeline_router
from app.routers.strategy import router as strategy_router
from app.routers.report_generator import router as report_generator_router
from app.routers.disputes import router as disputes_router
from app.routers.outcomes import router as outcomes_router
from app.routers.learning import router as learning_router
from app.routers.metro2 import router as metro2_router
from app.routers.auth import router as auth_router
from app.routers.audit import router as audit_router
from app.routers.organizations import router as organizations_router
from app.routers.inquiries import router as inquiries_router
from app.routers.personal_info import router as personal_info_router
from app.routers.legal import router as legal_router
from app.routers.legal_updates import router as legal_updates_router
from app.routers.collection_review import router as collection_review_router
from app.routers.analytics import router as analytics_router
from app.routers.search import router as search_router
from app.routers.ai_consult import router as ai_consult_router
from app.routers.portal import router as portal_router
from app.routers.billing import router as billing_router
from app.routers.service_cases import router as service_cases_router
from app.routers.document_templates import router as document_templates_router
from app.routers.document_generation import router as document_generation_router
from app.routers.appointments import router as appointments_router
from app.routers.service_invoices import router as service_invoices_router
from app.routers.notary import router as notary_router
from app.routers.referrals import router as referrals_router
from app.routers.judgment_ai import router as judgment_ai_router
from app.routers.consulting_ai import router as consulting_ai_router
from app.routers.overages_ai import router as overages_ai_router
from app.routers.case_research import router as case_research_router
from app.routers.data_pulls import router as data_pulls_router
from app.routers.case_monitor import router as case_monitor_router


def repair_schema():
    """Add any columns/tables that are missing due to partial Alembic migration history.

    This runs after run_migrations() as a safety net. It is idempotent — if all
    columns already exist it is a no-op. This fixes cases where the DB was created
    by create_all from an older model snapshot, then Alembic failed to add newer
    columns via ALTER TABLE.
    """
    from sqlalchemy import inspect as sa_inspect, text
    from app.database import engine

    try:
        insp = sa_inspect(engine)
        existing_tables = set(insp.get_table_names())

        def cols(table):
            if table not in existing_tables:
                return set()
            return {c["name"] for c in insp.get_columns(table)}

        def run_ddl(sql, label):
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
                print(f"[REPAIR] {label}")
            except Exception as exc:
                if "already exists" not in str(exc).lower():
                    print(f"[REPAIR-WARN] {label}: {exc}")

        # Migration 003: organizations table + users.organization_id
        if "organizations" not in existing_tables:
            run_ddl(
                "CREATE TABLE IF NOT EXISTS organizations "
                "(id SERIAL PRIMARY KEY, name VARCHAR NOT NULL, "
                "created_at TIMESTAMP DEFAULT NOW())",
                "Created organizations table",
            )
            existing_tables.add("organizations")

        if "users" in existing_tables and "organization_id" not in cols("users"):
            run_ddl(
                "ALTER TABLE users ADD COLUMN organization_id INTEGER "
                "REFERENCES organizations(id)",
                "Added users.organization_id",
            )

        # Migration 006: portal columns on aegis_clients / aegis_cases + client_documents
        if "aegis_clients" in existing_tables and "portal_user_id" not in cols("aegis_clients"):
            run_ddl(
                "ALTER TABLE aegis_clients ADD COLUMN portal_user_id INTEGER "
                "REFERENCES users(id)",
                "Added aegis_clients.portal_user_id",
            )

        if "aegis_cases" in existing_tables and "portal_status" not in cols("aegis_cases"):
            run_ddl(
                "ALTER TABLE aegis_cases ADD COLUMN portal_status VARCHAR "
                "DEFAULT 'pending'",
                "Added aegis_cases.portal_status",
            )

        if "client_documents" not in existing_tables:
            run_ddl(
                "CREATE TABLE IF NOT EXISTS client_documents ("
                "id SERIAL PRIMARY KEY, "
                "case_id INTEGER REFERENCES aegis_cases(id), "
                "client_id INTEGER REFERENCES aegis_clients(id), "
                "doc_type VARCHAR, bureau VARCHAR, original_filename VARCHAR, "
                "file_path VARCHAR, notes TEXT, "
                "uploaded_at TIMESTAMP DEFAULT NOW(), reviewed BOOLEAN DEFAULT FALSE)",
                "Created client_documents table",
            )

        for new_table, ddl in [
            ("service_cases", "CREATE TABLE IF NOT EXISTS service_cases (id SERIAL PRIMARY KEY, client_id INTEGER REFERENCES aegis_clients(id), division_slug VARCHAR, case_number VARCHAR UNIQUE, status VARCHAR DEFAULT 'intake', title VARCHAR, intake_data TEXT, notes TEXT, assigned_to VARCHAR, created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP)"),
            ("document_templates", "CREATE TABLE IF NOT EXISTS document_templates (id SERIAL PRIMARY KEY, division_slug VARCHAR, template_type VARCHAR DEFAULT 'generated', name VARCHAR, description TEXT, content TEXT, variables TEXT, category VARCHAR, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW())"),
            ("service_documents", "CREATE TABLE IF NOT EXISTS service_documents (id SERIAL PRIMARY KEY, service_case_id INTEGER REFERENCES service_cases(id), client_id INTEGER REFERENCES aegis_clients(id), template_id INTEGER REFERENCES document_templates(id), division_slug VARCHAR, title VARCHAR, document_type VARCHAR, content TEXT, file_path VARCHAR, status VARCHAR DEFAULT 'draft', esign_request_id VARCHAR, esign_provider VARCHAR, ai_generated BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())"),
            ("appointments", "CREATE TABLE IF NOT EXISTS appointments (id SERIAL PRIMARY KEY, client_id INTEGER REFERENCES aegis_clients(id), service_case_id INTEGER REFERENCES service_cases(id), division_slug VARCHAR, appointment_type VARCHAR, scheduled_at TIMESTAMP, duration_minutes INTEGER DEFAULT 60, location VARCHAR, travel_miles FLOAT, status VARCHAR DEFAULT 'scheduled', notes TEXT, created_at TIMESTAMP DEFAULT NOW())"),
            ("service_invoices", "CREATE TABLE IF NOT EXISTS service_invoices (id SERIAL PRIMARY KEY, client_id INTEGER REFERENCES aegis_clients(id), service_case_id INTEGER REFERENCES service_cases(id), invoice_number VARCHAR UNIQUE, division_slug VARCHAR, line_items TEXT, subtotal FLOAT DEFAULT 0, tax_rate FLOAT DEFAULT 0, tax_amount FLOAT DEFAULT 0, total FLOAT DEFAULT 0, status VARCHAR DEFAULT 'draft', due_date TIMESTAMP, paid_at TIMESTAMP, payment_method VARCHAR, notes TEXT, created_at TIMESTAMP DEFAULT NOW())"),
            ("attorney_referrals", "CREATE TABLE IF NOT EXISTS attorney_referrals (id SERIAL PRIMARY KEY, client_id INTEGER REFERENCES aegis_clients(id), service_case_id INTEGER REFERENCES service_cases(id), attorney_name VARCHAR, attorney_firm VARCHAR, attorney_email VARCHAR, attorney_phone VARCHAR, practice_area VARCHAR, reason TEXT, status VARCHAR DEFAULT 'pending', referral_letter_path VARCHAR, notes TEXT, referred_at TIMESTAMP DEFAULT NOW())"),
            ("notary_logs", "CREATE TABLE IF NOT EXISTS notary_logs (id SERIAL PRIMARY KEY, client_id INTEGER REFERENCES aegis_clients(id), service_case_id INTEGER REFERENCES service_cases(id), journal_number VARCHAR UNIQUE, document_type VARCHAR, signer_name VARCHAR, signer_id_type VARCHAR, signer_id_number VARCHAR, signer_id_expiry VARCHAR, num_signers INTEGER DEFAULT 1, num_witnesses INTEGER DEFAULT 0, notarized_at TIMESTAMP, location VARCHAR, travel_miles FLOAT, fee_charged FLOAT, notes TEXT, created_at TIMESTAMP DEFAULT NOW())"),
        ]:
            if new_table not in existing_tables:
                run_ddl(ddl, f"Created {new_table} table")
                existing_tables.add(new_table)

        # Migration 007: stripe billing columns on users
        if "users" in existing_tables:
            ucols = cols("users")
            for col_name, col_def in [
                ("stripe_customer_id", "VARCHAR"),
                ("stripe_subscription_id", "VARCHAR"),
                ("subscription_status", "VARCHAR"),
                ("subscription_period_end", "TIMESTAMP"),
            ]:
                if col_name not in ucols:
                    run_ddl(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_def}",
                        f"Added users.{col_name}",
                    )

        # Migration 008: case_id on service_documents for cross-linking research reports
        if "service_documents" in existing_tables and "case_id" not in cols("service_documents"):
            run_ddl(
                "ALTER TABLE service_documents ADD COLUMN case_id INTEGER "
                "REFERENCES aegis_cases(id)",
                "Added service_documents.case_id",
            )

        print("[REPAIR] Schema repair complete")
    except Exception as e:
        print(f"[WARNING] Schema repair failed: {e}")


def run_migrations():
    """Run alembic upgrade heads on startup.

    If the database was previously created with SQLAlchemy create_all (no
    alembic_version table) but tables already exist, we stamp the DB at heads
    first so Alembic doesn't try to re-create existing tables.
    """
    try:
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import inspect as sa_inspect
        from app.database import engine

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))

        # Detect create_all-initialised DB: tables exist but no alembic_version row.
        insp = sa_inspect(engine)
        existing = insp.get_table_names()
        if "alembic_version" not in existing and "users" in existing:
            print("[MIGRATION] Detected create_all DB — stamping heads before upgrade")
            command.stamp(alembic_cfg, "heads")

        command.upgrade(alembic_cfg, "heads")
        print("[MIGRATION] Alembic upgrade heads completed successfully")
    except Exception as e:
        print(f"[WARNING] Alembic migration failed ({e}), falling back to create_all")
        try:
            from app.database import engine, Base
            Base.metadata.create_all(bind=engine)
        except Exception as e2:
            print(f"[WARNING] create_all also failed ({e2}) — app will start without schema")


def run_seeds():
    """Seed reference data (legal knowledge engine)."""
    try:
        from app.database import SessionLocal
        from app.services.legal_seed import seed_federal_laws, seed_agency_guidance, seed_case_law, seed_state_laws
        db = SessionLocal()
        try:
            seed_federal_laws(db)
            seed_agency_guidance(db)
            seed_case_law(db)
            seed_state_laws(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[WARNING] Seed functions failed ({e})")


def _ensure_admin():
    """Create a default admin user on first boot if none exists."""
    try:
        from app.database import SessionLocal
        from app.models import User
        from app.services.auth_service import hash_password
        db = SessionLocal()
        try:
            if db.query(User).filter(User.role == "admin").count() == 0:
                admin = User(
                    username="admin",
                    email="admin@cruelandassociates.site",
                    full_name="Administrator",
                    hashed_password=hash_password("Cruel2026!"),
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                db.commit()
                print("[STARTUP] Default admin created — username: admin  password: Cruel2026!")
            else:
                print("[STARTUP] Admin user already exists — skipping default creation")
        finally:
            db.close()
    except Exception as e:
        print(f"[STARTUP] Could not ensure admin user: {e}")


# Skip migrations during test runs (tests call create_all directly)
if not os.environ.get("TESTING"):
    # Run all startup tasks in a background thread so uvicorn starts immediately
    # and the Railway healthcheck at /api/health responds before DB ops finish.
    # This prevents health-check timeouts from rolling back deployments.
    import threading
    def _startup():
        # Create persistent storage directories before anything else writes files
        for _dir in [settings.UPLOAD_DIR, settings.REPORTS_DIR, settings.EVIDENCE_DIR]:
            if _dir:
                os.makedirs(_dir, exist_ok=True)
        run_migrations()
        repair_schema()
        _ensure_admin()
        run_seeds()
    threading.Thread(target=_startup, daemon=True).start()

# APScheduler — daily morning digest at 6 AM UTC
if not os.environ.get("TESTING"):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.jobs.monitor_job import generate_morning_digest
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(generate_morning_digest, "cron", hour=6, minute=0, id="morning_digest", replace_existing=True)
        _scheduler.start()
        print("[SCHEDULER] Morning digest job scheduled at 06:00 UTC daily")
    except Exception as _sched_err:
        print(f"[SCHEDULER] Failed to start: {_sched_err}")

# Startup diagnostics — visible in Railway deploy logs
_ak_raw = os.environ.get('ANTHROPIC_API_KEY', '')
_sk_raw = os.environ.get('STRIPE_SECRET_KEY', '')
print(f"[ENV-RAW] ANTHROPIC_API_KEY: {len(_ak_raw)} chars (alt ANTHROPIC_KEY: {len(os.environ.get('ANTHROPIC_KEY',''))} chars)")
print(f"[ENV-RAW] STRIPE_SECRET_KEY: {len(_sk_raw)} chars (alt STRIPE_SK: {len(os.environ.get('STRIPE_SK',''))} chars)")
_raw_db = os.environ.get('DATABASE_URL', 'NOT SET')
print(f"[ENV-RAW] DATABASE_URL in os.environ: {_raw_db[:40]}")
# Show host+user without password for diagnosis
try:
    import re as _re
    _db_safe = _re.sub(r'://([^:]+):[^@]+@', r'://\1:***@', settings.DATABASE_URL)
    print(f"[CONFIG] DATABASE_URL (masked): {_db_safe[:80]}")
except Exception:
    print(f"[CONFIG] DATABASE_URL: {settings.DATABASE_URL[:35]}...")
print(f"[CONFIG] ANTHROPIC_API_KEY: {'SET (' + str(len(settings.ANTHROPIC_API_KEY)) + ' chars)' if settings.ANTHROPIC_API_KEY else 'MISSING — reports will fail'}")
print(f"[CONFIG] STRIPE_SECRET_KEY: {'SET' if settings.STRIPE_SECRET_KEY else 'MISSING — billing will fail'}")
print(f"[CONFIG] JWT_SECRET_KEY: {'SET (custom)' if settings.JWT_SECRET_KEY not in ('change-me-in-production-use-env-var', '') else 'MISSING — using insecure default'}")

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients_router)
app.include_router(cases_router)
app.include_router(reports_router)
app.include_router(tradelines_router)
app.include_router(comparison_router)
app.include_router(findings_router)
app.include_router(evidence_router)
app.include_router(court_records_router)
app.include_router(timeline_router)
app.include_router(strategy_router)
app.include_router(report_generator_router)
app.include_router(disputes_router)
app.include_router(outcomes_router)
app.include_router(learning_router)
app.include_router(metro2_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(organizations_router)
app.include_router(inquiries_router)
app.include_router(personal_info_router)
app.include_router(legal_router)
app.include_router(legal_updates_router)
app.include_router(collection_review_router)
app.include_router(analytics_router)
app.include_router(search_router)
app.include_router(ai_consult_router)
app.include_router(portal_router)
app.include_router(billing_router)
app.include_router(service_cases_router)
app.include_router(document_templates_router)
app.include_router(document_generation_router)
app.include_router(appointments_router)
app.include_router(service_invoices_router)
app.include_router(notary_router)
app.include_router(referrals_router)
app.include_router(judgment_ai_router)
app.include_router(consulting_ai_router)
app.include_router(overages_ai_router)
app.include_router(case_research_router)
app.include_router(data_pulls_router)
app.include_router(case_monitor_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "v": 4}


@app.get("/api/diagnose")
def diagnose(response: Response):
    """Full system diagnostic — checks env, packages, DB, tables, and config."""
    import re
    import importlib
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    out = {"_version": "v1", "_mode": "check-only"}
    issues = []
    warnings = []

    # ── env vars ──────────────────────────────────────────────────────────────
    def mask(v): return re.sub(r'://([^:]+):[^@]+@', r'://\1:***@', v) if v else ""

    env = {}
    ak = os.environ.get("ANTHROPIC_API_KEY", "")
    ak_alt = os.environ.get("ANTHROPIC_KEY", "")
    ak_eff = ak if len(ak) >= 100 else ak_alt
    env["ANTHROPIC_API_KEY"] = (
        f"OK — {len(ak_eff)} chars (from {'ANTHROPIC_KEY' if ak_eff == ak_alt and ak_eff else 'ANTHROPIC_API_KEY'})"
        if ak_eff.startswith("sk-ant-api03-") and len(ak_eff) >= 100
        else f"INVALID/TRUNCATED — primary={len(ak)} chars, alt ANTHROPIC_KEY={len(ak_alt)} chars"
    )
    if "INVALID" in env["ANTHROPIC_API_KEY"]:
        issues.append("ANTHROPIC_API_KEY: set ANTHROPIC_KEY in Railway Variables with your full sk-ant-api03-... key")

    sk = os.environ.get("STRIPE_SECRET_KEY", "")
    sk_alt = os.environ.get("STRIPE_SK", "")
    sk_eff = sk if len(sk) > 50 else sk_alt
    env["STRIPE_SECRET_KEY"] = (
        f"OK — {len(sk_eff)} chars (from {'STRIPE_SK' if sk_eff == sk_alt and sk_eff else 'STRIPE_SECRET_KEY'})"
        if (sk_eff.startswith("sk_live_") or sk_eff.startswith("sk_test_")) and len(sk_eff) > 50
        else f"INVALID/TRUNCATED — primary={len(sk)} chars, alt STRIPE_SK={len(sk_alt)} chars"
    )
    if "INVALID" in env["STRIPE_SECRET_KEY"]:
        issues.append("STRIPE_SECRET_KEY: set STRIPE_SK in Railway Variables with your full sk_live_... key")

    db_url = os.environ.get("DATABASE_URL", "")
    env["DATABASE_URL"] = mask(db_url)[:80] if db_url else "NOT SET"
    if not db_url:
        issues.append("DATABASE_URL: set to ${{ Postgres.DATABASE_URL }} in Railway Variables")
    elif "PASSWORD" in db_url:
        issues.append("DATABASE_URL: contains literal 'PASSWORD' — set to ${{ Postgres.DATABASE_URL }}")

    jwt = os.environ.get("JWT_SECRET_KEY", "")
    env["JWT_SECRET_KEY"] = (
        f"OK — {len(jwt)} chars" if jwt and jwt not in ("change-me-in-production-use-env-var", "")
        else "USING INSECURE DEFAULT — set a random 32+ char string"
    )
    if "INSECURE" in env["JWT_SECRET_KEY"]:
        warnings.append("JWT_SECRET_KEY is using default — change for production")

    out["env"] = env

    # ── packages ──────────────────────────────────────────────────────────────
    pkgs = {}
    for pip_name, import_name in [
        ("alembic", "alembic"), ("stripe", "stripe"), ("anthropic", "anthropic"),
        ("psycopg2-binary", "psycopg2"), ("pdfplumber", "pdfplumber"),
        ("reportlab", "reportlab"), ("passlib", "passlib"), ("python-jose", "jose"),
    ]:
        try:
            mod = importlib.import_module(import_name)
            pkgs[pip_name] = getattr(mod, "__version__", "installed")
        except ImportError:
            pkgs[pip_name] = "MISSING"
            issues.append(f"Package '{pip_name}' not installed — Dockerfile pip layer may be cached")
    out["packages"] = pkgs

    # ── database ──────────────────────────────────────────────────────────────
    db = {}
    if db_url and db_url.startswith("postgresql"):
        try:
            from sqlalchemy import create_engine, text, inspect as sa_inspect
            engine = create_engine(db_url, connect_args={"connect_timeout": 8}, pool_pre_ping=True)
            with engine.connect() as conn:
                row = conn.execute(text("SELECT current_database(), version()")).fetchone()
            db["connection"] = f"OK — db={row[0]}"

            insp = sa_inspect(engine)
            existing = set(insp.get_table_names())
            required = ["users", "aegis_clients", "aegis_cases", "tradelines",
                        "findings", "generated_reports", "audit_logs", "client_documents"]
            db["tables_present"]  = sorted(existing)
            db["tables_missing"]  = [t for t in required if t not in existing]
            db["alembic_version"] = "present" if "alembic_version" in existing else "missing"

            if db["tables_missing"]:
                issues.append(f"Missing DB tables: {', '.join(db['tables_missing'])} — run migrations")

            try:
                with engine.connect() as conn:
                    db["user_count"] = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                    if db["user_count"] == 0:
                        warnings.append("No users in DB — you need to register or create an admin")
            except Exception:
                pass

        except Exception as exc:
            db["connection"] = f"FAILED: {str(exc)[:200]}"
            issues.append(f"DB connection failed: {str(exc)[:120]} — check DATABASE_URL in Railway Variables")
    else:
        db["connection"] = "SKIPPED — DATABASE_URL not set or not PostgreSQL"
    out["database"] = db

    # ── summary ───────────────────────────────────────────────────────────────
    out["issues"]   = issues
    out["warnings"] = warnings
    out["status"]   = "ALL GOOD" if not issues else f"{len(issues)} ISSUE(S) NEED ATTENTION"

    return out


@app.get("/api/db-check")
def db_check():
    """Diagnostic — tests DB connectivity and table existence."""
    from sqlalchemy import inspect as sa_inspect, text
    from app.database import engine
    result = {"database_url": settings.DATABASE_URL[:40] + "..."}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["connection"] = "OK"
    except Exception as e:
        result["connection"] = f"FAILED: {e}"
        return result
    try:
        insp = sa_inspect(engine)
        tables = sorted(insp.get_table_names())
        result["tables"] = tables
        result["alembic_version"] = "alembic_version" in tables
        result["users_table"] = "users" in tables
        result["aegis_clients_table"] = "aegis_clients" in tables
    except Exception as e:
        result["inspect_error"] = str(e)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()
            result["user_count"] = row[0]
    except Exception as e:
        result["user_count_error"] = str(e)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version FROM alembic_version")).fetchone()
            result["alembic_heads"] = row[0] if row else "empty"
    except Exception as e:
        result["alembic_heads"] = f"no table: {e}"
    return result

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "anthropic_key": "SET" if settings.ANTHROPIC_API_KEY else "MISSING",
        "stripe_key": "SET" if settings.STRIPE_SECRET_KEY else "MISSING",
        "database": settings.DATABASE_URL[:30] + "...",
    }


@app.get("/api/env-check")
def env_check(response: Response):
    """Diagnostic — no-cache, shows every DB source and live connection test."""
    import re
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"

    def mask(url: str) -> str:
        return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url) if url else "NOT SET"

    result = {"_version": "v4"}

    # Anthropic key: compare raw env vs what pydantic-settings loaded
    ak_env      = os.environ.get("ANTHROPIC_API_KEY", "")
    ak_settings = settings.ANTHROPIC_API_KEY or ""
    result["ANTHROPIC_KEY_env"]      = f"{len(ak_env)} chars — {ak_env[:14]}..." if ak_env else "NOT SET"
    result["ANTHROPIC_KEY_settings"] = f"{len(ak_settings)} chars" if ak_settings else "EMPTY (pydantic-settings missed it)"

    # DATABASE_URL_OVERRIDE — priority 0 in database.py, bypasses Railway auto-injection
    dbo = os.environ.get("DATABASE_URL_OVERRIDE", "")
    result["DATABASE_URL_OVERRIDE"] = (
        f"SET — {mask(dbo)[:80]}" if dbo and dbo.startswith("postgresql")
        else ("SET but not postgresql (ignored)" if dbo else "NOT SET — add this in Railway Variables to fix DB")
    )

    # All DB-related env vars
    for k in ["DATABASE_URL", "PGHOST", "PGPORT", "PGUSER", "PGDATABASE"]:
        val = os.environ.get(k, "")
        result[f"env_{k}"] = mask(val)[:80] if k == "DATABASE_URL" else (val[:60] if val else "NOT SET")
    for k in ["PGPASSWORD", "POSTGRES_PASSWORD"]:
        result[f"env_{k}"] = "SET (***)" if os.environ.get(k) else "NOT SET"

    # What database.py is actually using (after all patching)
    from app.database import _url as db_resolved_url
    result["db_resolved_url"]   = mask(db_resolved_url)[:80]
    result["settings_DB_URL"]   = mask(settings.DATABASE_URL)[:80]

    # Live connection test
    try:
        from sqlalchemy import text
        from app.database import engine
        with engine.connect() as conn:
            row = conn.execute(text("SELECT current_database(), version()")).fetchone()
        result["db_connection"] = f"OK — db={row[0]}, pg={row[1][:40]}"
    except Exception as exc:
        result["db_connection"] = f"FAILED: {str(exc)[:150]}"

    # Other keys
    for k in ["STRIPE_SECRET_KEY", "JWT_SECRET_KEY"]:
        val = os.environ.get(k, "")
        result[k] = f"SET ({len(val)} chars)" if val else "NOT SET"

    for k in ["RAILWAY_ENVIRONMENT", "RAILWAY_SERVICE_NAME", "PORT"]:
        result[k] = os.environ.get(k, "NOT SET")

    return result


@app.get("/api/test-ai")
def test_ai(response: Response):
    """Live Anthropic API test — makes a 1-token call to verify key works end-to-end."""
    response.headers["Cache-Control"] = "no-store"
    from app.services.ai_service import _api_key, _client
    key = _api_key()
    key_info = f"{len(key)} chars, starts with {key[:14]}..." if key else "EMPTY"
    if not key or len(key) < 50:
        return {"status": "ERROR", "reason": "No valid API key found", "key_info": key_info}
    try:
        import anthropic
        client = _client()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say: OK"}],
        )
        return {
            "status": "OK",
            "key_info": key_info,
            "anthropic_response": msg.content[0].text if msg.content else "(empty)",
        }
    except anthropic.AuthenticationError as e:
        return {"status": "AUTH_FAILED", "key_info": key_info, "error": str(e)[:300]}
    except anthropic.RateLimitError as e:
        return {"status": "RATE_LIMITED", "key_info": key_info, "error": str(e)[:300]}
    except Exception as e:
        return {"status": "ERROR", "key_info": key_info, "error": str(e)[:300]}
