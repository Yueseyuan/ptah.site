# ROADMAP.md — APEX AI

## Build Phases

### Phase 1 — Foundation ⬅ CURRENT
- [ ] Project scaffold (FastAPI backend + Next.js frontend)
- [ ] `apex_data/` directory structure
- [ ] SQLite database + SQLAlchemy + Alembic
- [ ] Config system (pydantic-settings)
- [ ] Health endpoint `/health`
- [ ] Testing setup (pytest + pytest-asyncio)

### Phase 2 — Auth
- [ ] User model + Alembic migration
- [ ] Password hashing (bcrypt)
- [ ] JWT token generation + validation
- [ ] Login / Logout endpoints
- [ ] Session handling
- [ ] Auth middleware + dependencies

### Phase 3 — Audit Logs
- [ ] AuditLog model
- [ ] 9 event types: login, uploads, agent runs, skill runs, prompt runs, tool runs, workflow runs, approvals, system changes
- [ ] Auto-logging middleware
- [ ] Audit query endpoints

### Phase 4 — Approval System
- [ ] ApprovalRequest, ApprovalDecision models
- [ ] RiskPolicy, ActionPolicy models
- [ ] Approve / Reject workflow endpoints
- [ ] Risk routing logic

### Phase 5 — Model Backends
- [ ] Provider abstraction interface
- [ ] Ollama backend
- [ ] llama.cpp backend
- [ ] LM Studio backend
- [ ] LocalAI backend
- [ ] vLLM backend
- [ ] OpenAI backend
- [ ] Anthropic backend
- [ ] Backend health checks + model listing

### Phase 6 — Agent Registry
- [ ] Agent, AgentVersion, AgentCapability models
- [ ] AgentRun, AgentRunEvent, AgentRiskPolicy models
- [ ] Capability types: Research, Code, Website, Automation, Document, Knowledge, Business, Review, Risk Review
- [ ] CRUD endpoints

### Phase 7 — Skill + Prompt + Tool Registries
- [ ] Skill, SkillVersion, SkillCategory, SkillRun, SkillRiskPolicy
- [ ] PromptTemplate, PromptVersion, PromptRun, PromptEvaluation, PromptRiskPolicy
- [ ] ToolDefinition, ToolVersion, ToolRun, ToolPermission, ToolRiskPolicy
- [ ] CRUD + run endpoints for all three

### Phase 8 — Memory + Context + Knowledge
- [ ] MemoryEntry, MemoryCollection, MemoryTag, MemoryLink, MemoryVersion
- [ ] ContextPackage, ContextSource, ContextRebuildRun, ProjectState, DecisionRecord
- [ ] KnowledgeNode, KnowledgeEdge, KnowledgeSnapshot
- [ ] Search + retrieval endpoints

### Phase 9 — Workflow Engine + Orchestrator
- [ ] Workflow, WorkflowStep, WorkflowRun, WorkflowRunEvent
- [ ] All workflow categories + subtypes
- [ ] OrchestratorTask, TaskAssignment, TaskDependency
- [ ] OrchestratorRun, OrchestratorDecision, OrchestratorPlan
- [ ] TaskBranch, BranchRun, BranchResult, ResultMerge
- [ ] Task planner, agent assignment logic, risk routing

### Phase 10 — Repo Review Pipeline
- [ ] 5-stage review (license, security, dependency, capability, integration)
- [ ] 4-way classification (Use Directly / Modify First / Reference Only / Do Not Use)
- [ ] Review report generation

### Phase 11 — Next.js Frontend + 8 Modules
- [ ] Dashboard shell
- [ ] Aegis Credit Intelligence UI
- [ ] Business Intelligence UI
- [ ] Funding Intelligence UI
- [ ] Recovery Intelligence UI
- [ ] Legal Intelligence UI
- [ ] Document Intelligence UI
- [ ] Website Studio UI
- [ ] Automation Studio UI

### Phase 12 — Tauri Desktop App
- [ ] Tauri wrapper around Next.js frontend
- [ ] Local backend process management
- [ ] SQLite backup/export tool
- [ ] Auto-update support

## Export Formats
- Markdown (all phases)
- PDF (Phase 11+)
- DOCX (future)
