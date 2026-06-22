# PROJECT.md — PTAH Consultants Website

## Project Identity

| Field | Value |
|---|---|
| Name | ptah.site |
| Domain | ptah-het.com |
| Type | Static consulting firm website |
| Stack | HTML5 + Tailwind CSS (CDN) + Vanilla JS |
| Repo | yueseyuan/ptah.site |
| Branch | claude/ecc-repo-setup-jri49x → main |

## Purpose

Public-facing website for PTAH Consultants. Communicates the firm's value proposition, service offerings, insights, and client intake — converting visitors into qualified leads.

## Current State (Phase 0)

- Single-page `index.html` with header, hero, insights grid, contact section, footer
- Tailwind CDN (no build step)
- Color palette: gunmetal `#2a3439`, lightgrey `#d3d3d3`, green accent `#00FF66`
- Typography: Inter (Google Fonts)
- Placeholder JS for language toggle and CTA routing
- No backend, no forms, no analytics

## Tooling Installed

| Tool | Location | Purpose |
|---|---|---|
| ECC v2.0.0 | `~/.claude/` (via session hook) | Agent harness + rules + skills |
| ui-ux-pro-max v2.5.0 | `.claude/skills/ui-ux-pro-max/` | Design intelligence for HTML/Tailwind |
| 21st.dev Magic MCP | User MCP config | Component generation |
| SessionStart hook | `.claude/hooks/session-start.sh` | Auto-installs ECC + Magic on web sessions |

## Target Outcome

A polished, fast, accessible consulting firm website that:
1. Passes Core Web Vitals (LCP < 2.5s, CLS < 0.1, INP < 200ms)
2. Meets WCAG 2.2 AA accessibility
3. Converts visitors through clear hierarchy and a single primary CTA per page
4. Represents the PTAH brand with intentional visual design (not template defaults)
