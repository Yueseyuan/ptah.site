# LOCAL_FIRST.md — APEX AI

## Principle

All data is stored locally by default. Cloud sync is opt-in, never opt-out.

## Rules

### Data Storage
- Primary database: local SQLite (dev) or local PostgreSQL (server)
- `apex_data/` is never synced without explicit user action
- Model weights stored in `apex_data/models/` — never uploaded
- All agent runs, skill runs, and workflow outputs stay local

### Model Execution
- Local model backends (Ollama, llama.cpp, LM Studio, LocalAI, vLLM) are the default
- Cloud backends (OpenAI, Anthropic) are opt-in per-request
- No data sent to cloud models without user confirmation when cloud backend is selected

### Networking
- Backend binds to `localhost` by default
- Server deployment requires explicit configuration to expose to network
- No telemetry, analytics, or usage reporting without consent

### Exports
- All exports go to `apex_data/exports/` locally first
- User initiates any transfer outside the local system

### Backups
- Backups stored in `apex_data/backups/`
- Backup format: encrypted SQLite dump + file archive
- Cloud backup is a separate, opt-in feature

## Cloud Sync (Future, Opt-In)
When enabled:
- User provides their own storage credentials
- Sync is encrypted end-to-end
- User can disable and purge cloud data at any time
