# CHANGELOG.md — APEX AI

## [Unreleased] — Phase 2 Auth

### Added
- `app/models/user.py` — User model (id, email, hashed_password, is_active, is_admin, timestamps)
- `alembic/versions/1d40572fe74a_create_users_table.py` — migration for users table
- `app/core/security.py` — bcrypt password hashing + python-jose JWT create/decode
- `app/schemas/auth.py` — UserCreate, UserLogin, Token, UserOut Pydantic schemas
- `app/core/dependencies.py` — `get_current_user` FastAPI dependency (OAuth2 bearer)
- `app/api/v1/endpoints/auth.py` — POST /register, POST /login, POST /logout, GET /me
- `tests/test_auth.py` — 13 auth tests covering all flows and error paths

### Changed
- `app/models/__init__.py` — exports User
- `app/api/v1/router.py` — includes auth router at `/auth`
- `requirements.txt` — replaced `passlib[bcrypt]` with `bcrypt>=4.0.0`; added `pydantic[email]`

## [0.1.0] — Phase 1 Foundation

### Added
- Repository initialized
- `apex_data/` directory structure (13 subdirectories)
- `backend/` scaffold structure
- `frontend/` scaffold structure
- PROJECT.md — project identity and purpose
- ARCHITECTURE.md — system layers and schema domains
- ROADMAP.md — 12-phase build plan
- SECURITY.md — security rules and commit checklist
- LOCAL_FIRST.md — local-first data principles
- TRUTH_CONSTITUTION.md — truth and data integrity rules
- APPROVAL_POLICY.md — 4-level approval system
- REPO_REVIEW.md — 5-stage repo review pipeline
- AGENTS.md — agent types and data model
- TASKS.md — phase task tracking
- CHANGELOG.md — this file
- `app/config.py` — pydantic-settings Settings
- `app/database.py` — async SQLAlchemy + aiosqlite
- `app/main.py` — FastAPI app with lifespan + CORS
- `app/models/base.py` — TimestampMixin
- `app/api/v1/endpoints/health.py` — GET /health
- `alembic/` — async Alembic setup
- `tests/conftest.py` — in-memory SQLite fixtures
- `tests/test_health.py` — 2 health tests
