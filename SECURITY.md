# SECURITY.md — APEX AI

## Core Security Rules

### Secrets
- NEVER hardcode secrets, API keys, tokens, or passwords in source code
- ALL secrets via environment variables or `.env` file (gitignored)
- `.env.example` committed with placeholder values only
- Rotate any secret that appears in version control immediately

### Authentication
- Passwords hashed with bcrypt (cost factor ≥ 12)
- JWT tokens signed with HS256, expire in 30 minutes (configurable)
- Refresh tokens stored server-side (not in JWT payload)
- Failed login attempts rate-limited

### Authorization
- All API endpoints require authentication except `/health` and `/auth/login`
- Role-based access control enforced at route level
- High-risk actions require approval before execution (see APPROVAL_POLICY.md)

### Input Validation
- All inputs validated via Pydantic schemas at API boundary
- File uploads validated for type and size before processing
- No unsanitized data passed to model backends

### Audit Trail
- Every action logged to AuditLog (see ARCHITECTURE.md)
- Logs are append-only — no delete or update operations on audit records
- Log integrity verified on startup

### Model Backend Security
- API keys for cloud providers (OpenAI, Anthropic) stored in env vars only
- Local model backends communicate over localhost only
- No model responses stored without explicit user consent

### Data Protection
- `apex_data/` excluded from version control
- Backups encrypted before export
- No PII in log messages

## Checklist Before Every Commit

- [ ] No hardcoded secrets
- [ ] No API keys in code
- [ ] No PII in test fixtures
- [ ] All new endpoints require auth
- [ ] New user inputs validated with Pydantic
- [ ] Audit logging added for new action types
