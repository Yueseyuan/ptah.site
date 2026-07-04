# CHANGELOG.md — APEX AI

## [Unreleased] — Phase 12 Tauri Desktop App

### Added
- `frontend/src-tauri/` — Tauri v2 project scaffold wrapping the Next.js frontend
- `frontend/src-tauri/Cargo.toml` — Rust crate with tauri 2, tauri-plugin-shell/dialog/fs/updater/process
- `frontend/src-tauri/tauri.conf.json` — app config (1280×800 window, CSP, bundle targets, updater endpoint)
- `frontend/src-tauri/src/commands/backend.rs` — `start_backend` / `stop_backend` / `backend_status` Tauri commands (spawns FastAPI via bundled venv)
- `frontend/src-tauri/src/commands/database.rs` — `export_database` / `import_database` / `database_info` Tauri commands (safe copy with `.bak` pre-backup)
- `frontend/src-tauri/src/lib.rs` — Tauri app builder: auto-starts backend on launch, stops on window close
- `frontend/src-tauri/capabilities/default.json` — Tauri v2 capability file granting shell/dialog/fs/updater/process permissions
- `frontend/src-tauri/icons/` — placeholder PNG/ICO/ICNS icons (32×32, 128×128, 128×128@2x)
- `frontend/lib/tauri.ts` — `isTauri()` guard + `tauriBackend` / `tauriDatabase` typed wrappers
- Desktop panel in Settings page: backend start/stop control, live status indicator, DB export/import with file picker
- `@tauri-apps/api`, `@tauri-apps/plugin-dialog`, `@tauri-apps/plugin-fs`, `@tauri-apps/plugin-updater`, `@tauri-apps/plugin-process` npm packages

### Changed
- `frontend/next.config.ts` — `output: "export"` + `images.unoptimized` when `TAURI_ENV_TARGET_TRIPLE` is set (static export for desktop, SSR for web)

## [Unreleased] — Phase 11 Next.js Frontend

### Added
- `frontend/` — Next.js 16 + React 19 + TypeScript + Tailwind CSS scaffold (create-next-app)
- `frontend/lib/api.ts` — typed API client with auth injection + all module API methods
- `frontend/lib/auth.ts` — localStorage token management
- `frontend/components/ui/` — Button, Card, Badge, Input/Textarea components (dark design system)
- `frontend/components/sidebar.tsx` — collapsible navigation with active-link highlighting
- `frontend/app/(dashboard)/layout.tsx` — auth-gated dashboard shell with route protection
- `frontend/app/(dashboard)/dashboard/page.tsx` — live stats grid + model provider health
- `frontend/app/(dashboard)/agents/page.tsx` — agent CRUD + inline run panel
- `frontend/app/(dashboard)/memory/page.tsx` — memory entries with search + collection filter
- `frontend/app/(dashboard)/knowledge/page.tsx` — knowledge nodes with type filter chips
- `frontend/app/(dashboard)/workflows/page.tsx` — split-panel workflow builder + step manager
- `frontend/app/(dashboard)/repo-reviews/page.tsx` — split-panel review viewer + 5-stage pipeline
- `frontend/app/(dashboard)/settings/page.tsx` — provider health + model list + env config hints
- `frontend/app/login/page.tsx` + `frontend/app/register/page.tsx` — auth forms
- Production build: 13 routes, TypeScript clean

## [Unreleased] — Phase 10 Repo Review Pipeline

### Added
- `app/models/repo_review.py` — RepoReview, ReviewStage, ReviewFinding, ReviewReport + ReviewStatus/StageType/StageVerdict/RepoClassification enums
- `alembic/versions/…_create_repo_review_tables.py` — migration (4 tables, 7 indexes)
- `app/schemas/repo_review.py` — full schema set with 4-way classification
- `app/api/v1/endpoints/repo_review.py` — CRUD + 5-stage pipeline + per-stage findings + report generation (409 on dup)
- `tests/test_repo_review.py` — 11 tests

### Changed
- `app/api/v1/router.py` — includes repo-reviews router
- `app/models/__init__.py` — exports all Phase 10 models

## [Unreleased] — Phase 9 Workflow Engine + Orchestrator

### Added
- `app/models/workflow.py` — Workflow, WorkflowStep, WorkflowRun, WorkflowRunEvent + WorkflowStatus/RunStatus/StepType/StepStatus enums
- `app/models/orchestrator.py` — OrchestratorTask, TaskAssignment, TaskDependency, OrchestratorRun, OrchestratorDecision, OrchestratorPlan, TaskBranch, BranchRun, ResultMerge + status/merge enums
- `alembic/versions/…_create_workflow_orchestrator_tables.py` — migration (13 tables, 20+ indexes)
- `app/schemas/workflow.py` — full schema set for Workflow subsystem
- `app/schemas/orchestrator.py` — full schema set for Orchestrator subsystem
- `app/api/v1/endpoints/workflows.py` — CRUD + steps (order shift) + runs + run events
- `app/api/v1/endpoints/orchestrator.py` — tasks + assignments + dependencies + branches + branch runs + merges + runs + decisions + plans (with approve endpoint)
- `tests/test_workflow_orchestrator.py` — 15 tests

### Changed
- `app/api/v1/router.py` — includes workflows/orchestrator routers
- `app/models/__init__.py` — exports all Phase 9 models

## [Unreleased] — Phase 8 Memory + Context + Knowledge

### Added
- `app/models/memory.py` — MemoryCollection, MemoryTag, MemoryEntry, MemoryEntryTag, MemoryLink, MemoryVersion + ContentType/MemoryLinkType enums
- `app/models/context.py` — ContextPackage, ContextSource, ContextRebuildRun, ProjectState, DecisionRecord + status enums
- `app/models/knowledge.py` — KnowledgeNode, KnowledgeEdge, KnowledgeSnapshot + NodeType/EdgeType enums
- `alembic/versions/…_create_memory_context_knowledge_tables.py` — migration (18 tables, 20+ indexes)
- `app/schemas/memory.py` — full schema set for Memory subsystem
- `app/schemas/context.py` — full schema set for Context subsystem
- `app/schemas/knowledge.py` — full schema set for Knowledge subsystem
- `app/api/v1/endpoints/memory.py` — collections/tags/entries/versions/links + search + ilike filtering
- `app/api/v1/endpoints/context.py` — packages/sources/rebuild runs + project states + decision records (ADR)
- `app/api/v1/endpoints/knowledge.py` — nodes/edges/snapshots (auto-counts) + search
- `tests/test_memory_context_knowledge.py` — 24 tests

### Changed
- `app/api/v1/router.py` — includes memory/context/knowledge routers
- `app/models/__init__.py` — exports all Phase 8 models

## [Unreleased] — Phase 7 Skill + Prompt + Tool Registries

### Added
- `app/models/skill.py` — Skill, SkillVersion, SkillCategory, SkillRun, SkillRiskPolicy + SkillRunStatus enum
- `app/models/prompt.py` — PromptTemplate, PromptVersion, PromptRun, PromptEvaluation, PromptRiskPolicy + PromptType/PromptRunStatus enums
- `app/models/tool.py` — ToolDefinition, ToolVersion, ToolRun, ToolPermission, ToolRiskPolicy + ToolType/ToolRunStatus enums
- `alembic/versions/…_create_skill_prompt_tool_tables.py` — migration (15 tables)
- `app/schemas/skill.py` — full schema set for Skill registry (Category/Skill/Version/Run/RiskPolicy)
- `app/schemas/prompt.py` — full schema set for Prompt registry (Template/Version/Run/Evaluation/RiskPolicy)
- `app/schemas/tool.py` — full schema set for Tool registry (Tool/Version/Run/Permission/RiskPolicy)
- `app/api/v1/endpoints/skills.py` — categories CRUD + skills CRUD/versions/runs/risk-policies
- `app/api/v1/endpoints/prompts.py` — templates CRUD/versions/runs/evaluations/risk-policies
- `app/api/v1/endpoints/tools.py` — tools CRUD/versions/runs/permissions/risk-policies
- `tests/test_registries.py` — 23 tests covering all three registries

### Changed
- `app/api/v1/router.py` — includes skills/prompts/tools routers

## [Unreleased] — Phase 6 Agent Registry

### Added
- `app/models/agent.py` — 6 models + 2 enums (AgentCapabilityType × 9, AgentRunStatus × 5)
- `alembic/versions/…_create_agent_tables.py` — migration (6 tables, 9 indexes)
- `app/schemas/agent.py` — full schema set (Create/Update/Out for all models)
- `app/api/v1/endpoints/agents.py` — 14 endpoints across CRUD/versions/capabilities/runs/policies
- `tests/test_agents.py` — 21 tests

### Changed
- `app/models/__init__.py` — exports all agent models
- `app/api/v1/router.py` — includes agents router at `/agents`

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
