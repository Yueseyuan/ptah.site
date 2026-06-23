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

## Phase 4 — Approval System (Complete)

- [x] ApprovalRequest model (levels 0-3, status, expires_at, payload, reason)
- [x] ApprovalDecision model (verdict, decided_by, note)
- [x] RiskPolicy model (resource_type, action_type → required_level)
- [x] ActionPolicy model (timeout_minutes per action_type)
- [x] Level 0 → AUTO_APPROVED immediately on create
- [x] POST /api/v1/approvals/request
- [x] POST /api/v1/approvals/{id}/approve (Level 3 admin-only)
- [x] POST /api/v1/approvals/{id}/reject
- [x] GET /api/v1/approvals (admin, filterable by status/level)
- [x] GET /api/v1/approvals/{id} (requester or admin)
- [x] POST /api/v1/approvals/policies/risk + GET
- [x] POST /api/v1/approvals/policies/action + GET
- [x] 18 approval tests; 44 total passing
- [x] Phase 4 commit

## Phase 5 — Model Backends (Complete)

- [x] ModelProvider Protocol + Message, ModelInfo, CompletionResult dataclasses
- [x] OllamaProvider (native /api/chat API)
- [x] OpenAICompatProvider base + LlamaCpp, LMStudio, LocalAI, VLLM, OpenAI subclasses
- [x] AnthropicProvider (cloud, /v1/messages)
- [x] Streaming support (stream() on all providers)
- [x] ProviderRegistry (loads from config, get/all/names)
- [x] GET /api/v1/models/providers — health + model count per provider
- [x] GET /api/v1/models/providers/{name} — detail + model list
- [x] GET /api/v1/models — flat list across healthy providers
- [x] 22 provider tests (mocked httpx); 66 total passing
- [x] Phase 5 commit

## Phase 6 — Agent Registry (Complete)

- [x] Agent, AgentVersion, AgentCapability, AgentRun, AgentRunEvent, AgentRiskPolicy models
- [x] AgentCapabilityType (9 types) + AgentRunStatus enums
- [x] Alembic migration (6 tables, 9 indexes)
- [x] Full CRUD: create/list/get/update/deactivate agent
- [x] Version management: create/list, is_current swap
- [x] Capability management: add (idempotent)/list/remove
- [x] Run management: create/list/get-with-events
- [x] Risk policies per agent (create/list)
- [x] Audit events logged on agent create/run
- [x] 21 agent tests; 87 total passing
- [x] Phase 6 commit

## Phase 7 — Skill + Prompt + Tool Registries (Complete)

- [x] Skill, SkillVersion, SkillCategory, SkillRun, SkillRiskPolicy models
- [x] PromptTemplate, PromptVersion, PromptRun, PromptEvaluation, PromptRiskPolicy models
- [x] ToolDefinition, ToolVersion, ToolRun, ToolPermission, ToolRiskPolicy models
- [x] Alembic migration (15 tables)
- [x] Full CRUD + versions + runs + risk-policies for all three registries
- [x] Prompt evaluations (score, notes, tags)
- [x] Tool permissions (user-scoped or is_public)
- [x] Skill categories (create/list)
- [x] 23 registry tests; 110 total passing
- [x] Phase 7 commit

## Phase 8 — Memory + Context + Knowledge (Pending)

- [ ] MemoryEntry, MemoryCollection, MemoryTag, MemoryLink, MemoryVersion
- [ ] ContextPackage, ContextSource, ContextRebuildRun, ProjectState, DecisionRecord
- [ ] KnowledgeNode, KnowledgeEdge, KnowledgeSnapshot
- [ ] Search + retrieval endpoints
- [ ] Tests

## Upcoming Phases

See ROADMAP.md for full phase list.
