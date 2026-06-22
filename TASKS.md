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

## Phase 3 — Audit Logs (Complete)

- [x] AuditLog model (`app/models/audit.py`) with `AuditEventType` enum
- [x] 9 event types: login, upload, agent_run, skill_run, prompt_run, tool_run, workflow_run, approval, system_change
- [x] Alembic migration for audit_logs table
- [x] `log_event()` service (`app/services/audit.py`)
- [x] GET /api/v1/audit — admin-only, paginated, filterable by event_type/user_id
- [x] `get_current_admin` dependency (`app/core/dependencies.py`)
- [x] Auto-log LOGIN event on successful auth
- [x] 11 audit tests (service + endpoint + integration)
- [x] Phase 3 tests passing (26 total)
- [x] Phase 3 commit

## Phase 4 — Approval System (Pending)

- [ ] ApprovalRequest model (level 0-3, status, requester, approver)
- [ ] ApprovalDecision model
- [ ] RiskPolicy model (per resource type)
- [ ] ActionPolicy model
- [ ] POST /approvals/request
- [ ] POST /approvals/{id}/approve
- [ ] POST /approvals/{id}/reject
- [ ] GET /approvals (list with filters)
- [ ] Auto-expire timed-out requests
- [ ] Tests

## Upcoming Phases

See ROADMAP.md for full phase list.
