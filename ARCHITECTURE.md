# ARCHITECTURE.md — APEX AI

## Design Principles

1. **Local-first** — all data stored locally by default; cloud sync is optional
2. **Model independent** — pluggable backends (Ollama, llama.cpp, LM Studio, LocalAI, vLLM, OpenAI, Anthropic)
3. **Audit everything** — every agent run, skill run, prompt run, tool run, workflow run, approval, login, and system change is logged
4. **Human approval gates** — high-risk actions require explicit human approval before execution
5. **No hardcoded secrets** — all secrets via environment variables or config files outside version control

## System Layers

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Next.js)                  │
│  Dashboard · 8 Modules · Approval UI · Admin        │
├─────────────────────────────────────────────────────┤
│                  API Layer (FastAPI)                  │
│  /api/v1/* — REST endpoints for all domains         │
├──────────────┬──────────────┬────────────────────────┤
│  Auth        │  Orchestrator│  Workflow Engine        │
│  JWT · bcrypt│  Planner     │  Steps · Runs · Events  │
├──────────────┴──────────────┴────────────────────────┤
│              Registry Layer                           │
│  Agents · Skills · Prompts · Tools                   │
├─────────────────────────────────────────────────────┤
│              Intelligence Layer                       │
│  Memory · Context · Knowledge Graph                  │
├─────────────────────────────────────────────────────┤
│              Model Backend Abstraction                │
│  Ollama · llama.cpp · LM Studio · LocalAI · vLLM    │
│  OpenAI · Anthropic                                  │
├─────────────────────────────────────────────────────┤
│              Data Layer                               │
│  SQLite (dev) · PostgreSQL (server)                  │
│  SQLAlchemy + Alembic migrations                     │
└─────────────────────────────────────────────────────┘
```

## Database Schema Domains

| Domain | Models |
|---|---|
| Auth | User |
| Audit | AuditLog |
| Approval | ApprovalRequest, ApprovalDecision, RiskPolicy, ActionPolicy |
| Orchestrator | OrchestratorTask, TaskAssignment, TaskDependency, OrchestratorRun, OrchestratorDecision, OrchestratorPlan, TaskBranch, BranchRun, BranchResult, ResultMerge |
| Agents | Agent, AgentVersion, AgentCapability, AgentRun, AgentRunEvent, AgentRiskPolicy |
| Skills | Skill, SkillVersion, SkillCategory, SkillRun, SkillRiskPolicy |
| Prompts | PromptTemplate, PromptVersion, PromptRun, PromptEvaluation, PromptRiskPolicy |
| Tools | ToolDefinition, ToolVersion, ToolRun, ToolPermission, ToolRiskPolicy |
| Memory | MemoryEntry, MemoryCollection, MemoryTag, MemoryLink, MemoryVersion |
| Context | ContextPackage, ContextSource, ContextRebuildRun, ProjectState, DecisionRecord |
| Knowledge | KnowledgeNode, KnowledgeEdge, KnowledgeSnapshot |
| Workflows | Workflow, WorkflowStep, WorkflowRun, WorkflowRunEvent |

## Model Backend Abstraction

All model calls route through a provider-agnostic interface:

```python
class ModelBackend:
    async def complete(prompt, model, options) -> str
    async def list_models() -> list[str]
    async def health() -> bool
```

Implementations: OllamaBackend, LlamaCppBackend, LMStudioBackend, LocalAIBackend, vLLMBackend, OpenAIBackend, AnthropicBackend

## Deployment Paths

| Path | DB | Auth | Notes |
|---|---|---|---|
| Local desktop | SQLite | Local JWT | Tauri wrapper |
| Server | PostgreSQL | JWT + HTTPS | Docker + reverse proxy |
