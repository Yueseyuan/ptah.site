# CHANGELOG.md — APEX AI

## [Unreleased] — Phase 5 Model Backends

### Added
- `app/providers/base.py` — ModelProvider Protocol, Message, ModelInfo, CompletionResult
- `app/providers/ollama.py` — OllamaProvider (native /api/chat, health, list, complete, stream)
- `app/providers/openai_compat.py` — OpenAICompatProvider + LlamaCpp/LMStudio/LocalAI/VLLM/OpenAI subclasses
- `app/providers/anthropic.py` — AnthropicProvider (cloud /v1/messages, static model list)
- `app/providers/registry.py` — ProviderRegistry; auto-builds from config at startup
- `app/api/v1/endpoints/models.py` — 3 endpoints: providers list, provider detail, flat model list
- `tests/test_models.py` — 22 tests covering all providers + endpoints (mocked httpx)

### Changed
- `app/api/v1/router.py` — includes models router at `/models`

## [Unreleased] — Phase 4 Approval System

### Added
- `app/models/approval.py` — ApprovalRequest, ApprovalDecision, RiskPolicy, ActionPolicy + ApprovalStatus enum
- `alembic/versions/…_create_approval_tables.py` — migration (4 tables, 4 indexes)
- `app/schemas/approval.py` — all Pydantic schemas for requests, decisions, policies
- `app/api/v1/endpoints/approval.py` — full CRUD: request/approve/reject/list/get + policy endpoints
- `tests/test_approval.py` — 18 tests covering all flows, level enforcement, expiry, policy CRUD

### Changed
- `app/models/__init__.py` — exports all approval models
- `app/api/v1/router.py` — includes approval router at `/approvals`

## [Unreleased] — Phase 3 Audit Logs

### Added
- `app/models/audit.py` — AuditLog model + AuditEventType enum (9 event types)
- `alembic/versions/…_create_audit_logs_table.py` — migration with 3 indexes
- `app/services/audit.py` — `log_event()` service (adds entry to session, caller commits)
- `app/schemas/audit.py` — AuditLogOut, AuditLogList Pydantic schemas
- `app/api/v1/endpoints/audit.py` — GET /api/v1/audit (admin-only, paginated, filterable)
- `tests/test_audit.py` — 11 tests covering service, endpoint, and login auto-logging

### Changed
- `app/models/__init__.py` — exports AuditEventType, AuditLog
- `app/core/dependencies.py` — adds `get_current_admin` dependency
- `app/api/v1/router.py` — includes audit router at `/audit`
- `app/api/v1/endpoints/auth.py` — logs LOGIN event + commit on successful login

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
