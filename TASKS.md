# TASKS.md — APEX AI

## Phase 1 — Foundation (Complete)

- [x] Repo initialized
- [x] Directory structure created (`apex_data/` + backend + frontend)
- [x] All governance documentation written
- [x] Backend scaffold (FastAPI app)
- [x] Config system (pydantic-settings)
- [x] Database setup (SQLAlchemy + aiosqlite)
- [x] Alembic migrations initialized
- [x] Health endpoint `/health`
- [x] Testing setup (pytest + pytest-asyncio)
- [x] `.env.example`
- [x] `.gitignore`
- [x] `requirements.txt`
- [x] Phase 1 tests passing (2 tests)
- [x] Phase 1 commit

## Phase 2 — Auth (Complete)

- [x] User model (`app/models/user.py`)
- [x] Alembic migration: users table
- [x] Password hashing utility (bcrypt, `app/core/security.py`)
- [x] JWT token creation + validation (python-jose)
- [x] POST /api/v1/auth/register
- [x] POST /api/v1/auth/login
- [x] POST /api/v1/auth/logout
- [x] GET /api/v1/auth/me
- [x] Auth dependency `get_current_user` (`app/core/dependencies.py`)
- [x] Tests: register, login, logout, /me, invalid credentials, expired token (13 tests)
- [x] Phase 2 tests passing (15 total)
- [x] Phase 2 commit

## Phase 3 — Audit Logs (Pending)

- [ ] AuditLog model
- [ ] 9 event types: login, uploads, agent_run, skill_run, prompt_run, tool_run, workflow_run, approval, system_change
- [ ] Auto-logging middleware or service
- [ ] Query endpoint for audit trail
- [ ] Tests

## Upcoming Phases

See ROADMAP.md for full phase list.
