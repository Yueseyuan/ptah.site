# PROJECT.md — APEX AI

## Identity

| Field | Value |
|---|---|
| Name | APEX AI |
| Type | Local-first AI operating system for PTAH Consultants |
| Backend | FastAPI + SQLite (dev) / PostgreSQL (server) |
| Frontend | Next.js + React |
| Desktop | Tauri (preferred) / Electron (optional) |
| Repo | apex (separate from ptah.site) |

## Purpose

APEX AI is a local-first AI operating system that powers PTAH Consultants' eight product modules. It provides a unified runtime for agents, skills, prompts, tools, workflows, and orchestration — with full audit trails, human approval gates, and model independence.

## Eight Product Modules

| Module | Description |
|---|---|
| Aegis Credit Intelligence | Credit analysis and risk assessment |
| Business Intelligence | Business data analysis and insights |
| Funding Intelligence | Funding opportunity identification |
| Recovery Intelligence | Recovery strategy and planning |
| Legal Intelligence | Legal document analysis and guidance |
| Document Intelligence | Document processing and extraction |
| Website Studio | Website design and generation |
| Automation Studio | Business process automation |

## Architecture Summary

```
apex/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── frontend/         # Next.js + React
├── apex_data/        # Local data store (13 directories)
└── docs/             # All governance documentation
```

## Current Phase

Phase 1 — Foundation
