# TASKS.md — APEX AI

## Phase 1 — Foundation (Active)

### In Progress
- [x] Repo initialized
- [x] Directory structure created (`apex_data/` + backend + frontend)
- [x] All governance documentation written
- [ ] Backend scaffold (FastAPI app)
- [ ] Config system (pydantic-settings)
- [ ] Database setup (SQLAlchemy + aiosqlite)
- [ ] Alembic migrations initialized
- [ ] Health endpoint `/health`
- [ ] Testing setup (pytest + pytest-asyncio)
- [ ] `.env.example`
- [ ] `.gitignore`
- [ ] `requirements.txt`
- [ ] Phase 1 tests passing
- [ ] Phase 1 commit

### Blocked
- None

## Phase 2 — Auth (Pending)
- [ ] User model
- [ ] Alembic migration: users table
- [ ] Password hashing utility
- [ ] JWT token creation + validation
- [ ] POST /auth/login
- [ ] POST /auth/logout
- [ ] GET /auth/me
- [ ] Auth dependency (FastAPI)
- [ ] Tests: login, logout, invalid credentials, expired token

## Upcoming Phases
See ROADMAP.md for full phase list.
