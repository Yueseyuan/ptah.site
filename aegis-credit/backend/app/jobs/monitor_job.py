"""Nightly case monitoring digest (OpenJarvis scheduled-agent pattern).

Runs at 6 AM server time via APScheduler. Queries all active cases,
flags inactivity/overdue work, and asks Claude to generate a prioritized
daily action digest stored as a ServiceDocument (division_slug='monitor').
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import anthropic

from app.config import settings
from app.database import SessionLocal
from app.models import AegisCase, ServiceCase, ServiceDocument


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_morning_digest() -> Optional[int]:
    """Generate the daily digest and return the new ServiceDocument id, or None on failure."""
    db = SessionLocal()
    try:
        return _run(db)
    except Exception as exc:
        print(f"[MONITOR] Digest generation failed: {exc}")
        return None
    finally:
        db.close()


def _run(db) -> Optional[int]:
    now = _utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # ── Gather stats ────────────────────────────────────────────────────────────

    total_credit = db.query(AegisCase).count()
    active_credit = db.query(AegisCase).filter(AegisCase.status == "active").count()
    intake_credit = db.query(AegisCase).filter(AegisCase.status == "intake").count()

    # Cases with no update in 7+ days (updated_at may be NULL on never-edited rows)
    stale_credit = (
        db.query(AegisCase)
        .filter(
            AegisCase.status == "active",
            (AegisCase.updated_at < seven_days_ago) | (AegisCase.updated_at.is_(None)),
            AegisCase.created_at < seven_days_ago,
        )
        .all()
    )

    # New credit cases opened in last 7 days
    new_credit = (
        db.query(AegisCase)
        .filter(AegisCase.created_at >= seven_days_ago)
        .count()
    )

    # Service cases summary
    total_service = db.query(ServiceCase).count()
    active_service = db.query(ServiceCase).filter(ServiceCase.status == "active").count()

    stale_service = (
        db.query(ServiceCase)
        .filter(
            ServiceCase.status == "active",
            (ServiceCase.updated_at < seven_days_ago) | (ServiceCase.updated_at.is_(None)),
            ServiceCase.created_at < seven_days_ago,
        )
        .all()
    )

    new_service = (
        db.query(ServiceCase)
        .filter(ServiceCase.created_at >= seven_days_ago)
        .count()
    )

    # Cases with no activity in 30+ days (at risk of abandonment)
    at_risk = (
        db.query(AegisCase)
        .filter(
            AegisCase.status == "active",
            AegisCase.created_at < thirty_days_ago,
            (AegisCase.updated_at < thirty_days_ago) | (AegisCase.updated_at.is_(None)),
        )
        .all()
    )

    # ── Build context for Claude ─────────────────────────────────────────────────

    stale_credit_lines = "\n".join(
        f"  • Case {c.case_number} (client_id={c.client_id}, goal: {(c.goal or '')[:60]})"
        for c in stale_credit[:10]
    ) or "  None"

    stale_service_lines = "\n".join(
        f"  • {c.case_number} [{c.division_slug}] (client_id={c.client_id})"
        for c in stale_service[:10]
    ) or "  None"

    at_risk_lines = "\n".join(
        f"  • Case {c.case_number} — last updated: {c.updated_at or c.created_at}"
        for c in at_risk[:5]
    ) or "  None"

    prompt = (
        f"Today is {now.strftime('%A, %B %d, %Y')}.\n\n"
        "You are the operations intelligence for Cruel & Associates, a legal services and "
        "credit investigation firm. Generate a concise morning digest for the team.\n\n"
        "SNAPSHOT:\n"
        f"• Credit Cases: {total_credit} total | {active_credit} active | {intake_credit} intake | {new_credit} opened this week\n"
        f"• Service Cases: {total_service} total | {active_service} active | {new_service} opened this week\n\n"
        f"STALE CREDIT CASES (no activity 7+ days):\n{stale_credit_lines}\n\n"
        f"STALE SERVICE CASES (no activity 7+ days):\n{stale_service_lines}\n\n"
        f"AT-RISK CASES (30+ days inactive):\n{at_risk_lines}\n\n"
        "Write a structured morning digest with:\n"
        "## TODAY'S PRIORITY ACTIONS\n"
        "## CASES NEEDING ATTENTION\n"
        "## WEEK IN REVIEW\n"
        "## RECOMMENDED FOCUS\n\n"
        "Be specific and direct. Keep it under 400 words. This is for operational staff, not clients."
    )

    key = _api_key()
    if not key or len(key) < 50:
        # Save a data-only digest without AI narrative
        content = (
            f"## Morning Digest — {now.strftime('%B %d, %Y')}\n\n"
            f"**Credit Cases:** {active_credit} active / {intake_credit} intake / {new_credit} new this week\n"
            f"**Service Cases:** {active_service} active / {new_service} new this week\n\n"
            f"**Stale Credit Cases ({len(stale_credit)}):**\n{stale_credit_lines}\n\n"
            f"**Stale Service Cases ({len(stale_service)}):**\n{stale_service_lines}\n\n"
            f"**At-Risk Cases ({len(at_risk)}):**\n{at_risk_lines}\n\n"
            "_AI narrative unavailable — ANTHROPIC_API_KEY not configured._"
        )
    else:
        try:
            client = anthropic.Anthropic(api_key=key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            content = resp.content[0].text if resp.content else "Digest generation failed."
        except Exception as exc:
            content = (
                f"## Morning Digest — {now.strftime('%B %d, %Y')}\n\n"
                f"AI narrative failed: {str(exc)[:150]}\n\n"
                f"**Stats:** {active_credit} active credit cases, {active_service} active service cases.\n"
                f"**Stale credit:** {len(stale_credit)} cases. **Stale service:** {len(stale_service)} cases."
            )

    doc = ServiceDocument(
        division_slug="monitor",
        title=f"Morning Digest — {now.strftime('%B %d, %Y')}",
        document_type="Daily Digest",
        content=content,
        status="draft",
        ai_generated=(key and len(key) >= 50),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    print(f"[MONITOR] Digest saved — document_id={doc.id}")
    return doc.id
