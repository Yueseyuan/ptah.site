"""AI business advisory generator for Business Consulting division."""
import json
import os
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, ServiceCase, ServiceDocument, User

router = APIRouter(prefix="/api/consulting", tags=["consulting-ai"])

_AI_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are a senior business consultant and document preparer for Cruel & Associates. "
    "Generate practical, prioritized business advisory plans in plain language. "
    "Return only the advisory content — no preamble, no unnecessary commentary."
)


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _build_prompt(case: ServiceCase, client: AegisClient) -> str:
    intake: dict = {}
    if case.intake_data:
        try:
            raw = case.intake_data
            intake = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, dict) else {})
        except Exception:
            pass

    client_name = f"{client.first_name or ''} {client.last_name or ''}".strip()

    parts = [
        "Generate a structured business advisory plan for the following client.\n",
        f"CLIENT: {client_name}",
        f"CASE: {case.case_number or 'N/A'}",
    ]

    if intake.get("business_type"):
        parts.append(f"BUSINESS TYPE: {intake['business_type']}")
    if intake.get("stage"):
        stage_labels = {"startup": "Startup (not yet launched)", "existing": "Existing (already operating)"}
        parts.append(f"STAGE: {stage_labels.get(intake['stage'], intake['stage'])}")
    if intake.get("primary_need"):
        parts.append(f"PRIMARY NEED: {intake['primary_need']}")
    if intake.get("revenue_range"):
        rev_labels = {
            "pre_revenue": "Pre-revenue",
            "under_50k": "Under $50K/year",
            "50k_250k": "$50K–$250K/year",
            "250k_1m": "$250K–$1M/year",
            "over_1m": "Over $1M/year",
        }
        parts.append(f"REVENUE RANGE: {rev_labels.get(intake['revenue_range'], intake['revenue_range'])}")
    if case.notes:
        parts.append(f"ADDITIONAL NOTES: {case.notes}")

    parts.append(
        "\nProvide a structured advisory covering:\n"
        "1. Immediate priorities (next 30 days) based on the primary need\n"
        "2. Entity / compliance checklist (EIN, operating agreement, licenses, registered agent)\n"
        "3. Business credit building roadmap (Dun & Bradstreet, trade accounts, business credit card)\n"
        "4. Operational recommendations (SOPs, banking, bookkeeping, payroll)\n"
        "5. Growth milestones to target in the next 6–12 months\n"
        "\nKeep the total advisory under 700 words. Be specific to the stage and revenue range."
    )

    return "\n".join(parts)


@router.post("/{service_case_id}/advise", status_code=201)
def generate_business_advisory(
    service_case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Generate an AI-powered business advisory plan for a consulting service case."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Service case not found")
    if case.division_slug != "consulting":
        raise HTTPException(status_code=422, detail="Service case is not in the consulting division")

    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    prompt = _build_prompt(case, client)

    ai_generated = False
    api_key = _api_key()
    if api_key:
        try:
            anthropic_client = anthropic.Anthropic(api_key=api_key)
            response = anthropic_client.messages.create(
                model=_AI_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            advisory_content = response.content[0].text
            ai_generated = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"AI generation failed: {exc}")
    else:
        client_name = f"{client.first_name or ''} {client.last_name or ''}".strip()
        advisory_content = (
            f"BUSINESS ADVISORY PLAN — {client_name}\n\n"
            "AI generation unavailable (ANTHROPIC_API_KEY not configured).\n\n"
            "Please review the intake data and prepare a manual advisory."
        )

    doc = ServiceDocument(
        service_case_id=service_case_id,
        client_id=case.client_id,
        template_id=None,
        division_slug="consulting",
        title=f"Business Advisory — {case.case_number}",
        document_type="business_advisory",
        content=advisory_content,
        status="draft",
        ai_generated=ai_generated,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "title": doc.title,
        "content": advisory_content,
        "ai_generated": ai_generated,
    }
