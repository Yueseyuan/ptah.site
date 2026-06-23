# TRUTH_CONSTITUTION.md — APEX AI

## Purpose

Defines how APEX AI handles truth, uncertainty, and data integrity across all operations.

## Core Rules

### 1. Source Attribution
- Every piece of information must have a traceable source
- Agent outputs must cite sources when making factual claims
- Research workflows capture citations at ingestion time (source ranking, citation capture)
- Contradictions between sources are flagged, not silently resolved

### 2. Uncertainty Disclosure
- Models must express uncertainty when confidence is low
- Outputs that cannot be verified are marked as unverified
- No fabricated citations or invented data

### 3. Contradiction Detection
- Research workflows include contradiction detection as a required step
- Contradictions are surfaced to the user for resolution
- The system does not auto-resolve contradictions without human input

### 4. Data Integrity
- Database records are never silently modified — all changes tracked via updated_at + version fields
- Audit logs are append-only
- KnowledgeSnapshots preserve historical state
- DecisionRecords capture why decisions were made, not just what was decided

### 5. Model Output Provenance
- Every PromptRun records: model used, backend, temperature, input hash, output hash
- AgentRunEvents record each step taken and its output
- WorkflowRunEvents record step results in sequence

### 6. Human Override Authority
- Humans may override any AI decision
- Overrides are logged with reason
- The system defers to human judgment on all factual disputes

## Prohibited Actions
- Presenting AI-generated content as verified fact without source
- Modifying audit records
- Silently dropping contradictions
- Generating citations that were not retrieved from real sources
