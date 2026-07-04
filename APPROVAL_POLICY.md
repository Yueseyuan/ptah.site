# APPROVAL_POLICY.md — APEX AI

## Purpose

Defines which actions require human approval before execution.

## Approval Levels

### Level 0 — Auto-Approved (no human required)
- Reading data (any domain)
- Running low-risk prompts
- Health checks
- Search and retrieval operations
- Generating drafts (not publishing)

### Level 1 — Soft Approval (confirm before proceeding)
- Running agents for the first time
- Executing workflows with external integrations
- Sending any outbound communication
- Writing to `apex_data/` outside normal paths
- Calling cloud model backends (OpenAI, Anthropic) when cost exceeds threshold

### Level 2 — Hard Approval (explicit human sign-off required)
- Deploying code to production
- Publishing website content
- Initiating financial operations
- Modifying RiskPolicy or ActionPolicy
- Bulk data operations (delete, export, migration)
- Adding new model backends
- Granting new user permissions

### Level 3 — Admin Only
- Creating or deleting users
- Modifying system configuration
- Accessing backup/restore functions
- Viewing full audit logs

## Approval Workflow

1. Action triggers `ApprovalRequest` with risk level, action type, payload summary
2. `RiskPolicy` evaluated — if risk exceeds threshold, approval required
3. `ActionPolicy` determines who can approve (user self-approve vs admin)
4. Approver receives notification
5. Approver submits `ApprovalDecision` (approve / reject + reason)
6. If approved: action executes, `AuditLog` records execution
7. If rejected: action blocked, `AuditLog` records rejection

## Timeout Policy
- Level 1 approvals: auto-expire after 24 hours (action cancelled)
- Level 2 approvals: auto-expire after 72 hours (action cancelled)
- Level 3 approvals: no auto-expiry

## Escalation
If an approver is unavailable, Level 2+ requests escalate to admin after timeout.
