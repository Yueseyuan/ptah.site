# AGENTS.md — APEX AI

## Agent Capability Types

| Type | Description |
|---|---|
| Research | Source ranking, citation capture, source comparison, contradiction detection, research summaries |
| Code | Project scaffolding, code generation, refactoring, test generation, code review, documentation generation |
| Website | Landing pages, dashboards, client portals, multi-page websites, forms, brand sections |
| Automation | Triggers, schedules, conditions, actions, alerts, report generation |
| Document | Markdown exports, PDF exports, reports, specifications, project exports |
| Knowledge | Knowledge graph building, node linking, snapshot creation |
| Business | Business analysis, strategy, competitive intelligence |
| Review | Quality review, compliance review, output evaluation |
| Risk Review | Risk assessment, policy evaluation, threat modeling |

## Agent Data Model

```
Agent
  id, name, description, capability_type, is_active
  created_at, updated_at

AgentVersion
  id, agent_id, version, config, system_prompt, model_backend
  created_at

AgentCapability
  id, agent_id, capability_type, parameters

AgentRun
  id, agent_id, version_id, status, input_hash
  started_at, completed_at, duration_ms
  approval_request_id (if approval required)

AgentRunEvent
  id, run_id, event_type, payload, timestamp

AgentRiskPolicy
  id, agent_id, risk_level (0-3), requires_approval
  max_tokens, allowed_backends, allowed_tools
```

## Agent Assignment Logic (Orchestrator)

1. Orchestrator receives task with required capability type
2. Queries active agents matching capability
3. Evaluates AgentRiskPolicy — routes to approval if needed
4. Assigns agent version based on: capability match → risk level → availability
5. Logs assignment to TaskAssignment
6. Executes via AgentRun, streams events to AgentRunEvent

## Risk Routing

| Risk Level | Action |
|---|---|
| 0 | Auto-execute |
| 1 | Log + notify, execute |
| 2 | Require Level 1 approval |
| 3 | Require Level 2 approval |
