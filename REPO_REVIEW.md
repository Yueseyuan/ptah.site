# REPO_REVIEW.md — APEX AI

## Purpose

All external repositories must pass a 5-stage review before any code is imported.

## Review Pipeline

### Stage 1 — License Review
- Identify license type (MIT, Apache-2.0, GPL, proprietary, etc.)
- Flag copyleft licenses (GPL, AGPL) — require approval before use
- Flag unknown or missing licenses — do not use until clarified
- Confirm license compatibility with APEX AI (MIT license)

### Stage 2 — Security Review
- Scan for known CVEs in dependencies
- Check for hardcoded secrets or credentials
- Review network calls — flag unexpected outbound connections
- Check for supply chain risks (unusual install scripts, postinstall hooks)
- Review file system access patterns

### Stage 3 — Dependency Review
- List all direct and transitive dependencies
- Flag abandoned dependencies (no commits in 12+ months)
- Flag dependencies with known vulnerabilities
- Assess dependency tree depth and maintenance burden

### Stage 4 — Capability Extraction
- Document what the repository actually does
- Identify reusable components vs monolithic code
- Note integration points (APIs, protocols, data formats)
- Assess overlap with existing APEX capabilities

### Stage 5 — Integration Recommendation
- Determine classification (see below)
- Document integration approach if applicable
- Estimate integration effort
- Note risks and mitigations

## Classification Outcomes

| Classification | Meaning | Action |
|---|---|---|
| **Use Directly** | Meets all criteria, no changes needed | Import and use as dependency |
| **Modify First** | Good foundation but needs changes | Fork, audit, modify, then use |
| **Reference Only** | Useful patterns but not safe to import | Study code, implement independently |
| **Do Not Use** | License conflict, security risk, or abandoned | Document reason, find alternative |

## Review Record

Each review must be recorded as a `KnowledgeNode` with:
- Repository URL + commit SHA reviewed
- Date of review
- Stage-by-stage findings
- Final classification + justification
- Reviewer identity
