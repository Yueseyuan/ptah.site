"""AI recovery plan generator for Judgment & Asset Recovery division."""
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

router = APIRouter(prefix="/api/judgment", tags=["judgment-ai"])

_AI_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are a judgment recovery specialist and legal document preparer for Cruel & Associates. "
    "Generate concise, actionable recovery plans in plain language. "
    "Return only the plan content — no preamble, no markdown headers unless they add structure."
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
        "Generate a prioritized judgment recovery plan for the following case.\n",
        f"CREDITOR/CLIENT: {client_name}",
        f"CASE NUMBER: {case.case_number or 'N/A'}",
    ]

    if intake.get("judgment_amount"):
        parts.append(f"JUDGMENT AMOUNT: ${intake['judgment_amount']}")
    if intake.get("judgment_date"):
        parts.append(f"JUDGMENT DATE: {intake['judgment_date']}")
    if intake.get("court"):
        parts.append(f"COURT: {intake['court']}")
    if intake.get("debtor_name"):
        parts.append(f"DEBTOR: {intake['debtor_name']}")
    if intake.get("known_assets"):
        parts.append(f"KNOWN ASSETS: {intake['known_assets']}")
    if case.notes:
        parts.append(f"ADDITIONAL NOTES: {case.notes}")

    parts.append(
        "\nProvide:\n"
        "1. Assessment of collectability (high/medium/low) with rationale\n"
        "2. Top 3–5 enforcement actions ranked by likelihood of success "
        "(wage garnishment, bank levy, property lien, till tap, keeper levy, etc.)\n"
        "3. Asset exemption risks to be aware of\n"
        "4. Statute of limitations and renewal timeline\n"
        "5. Recommended next step within the next 30 days\n"
        "\nKeep the total plan under 600 words."
    )

    return "\n".join(parts)


@router.post("/{service_case_id}/recovery-plan", status_code=201)
def generate_recovery_plan(
    service_case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Generate an AI-powered judgment recovery plan for a service case."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Service case not found")
    if case.division_slug != "judgment":
        raise HTTPException(status_code=422, detail="Service case is not in the judgment division")

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
            plan_content = response.content[0].text
            ai_generated = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"AI generation failed: {exc}")
    else:
        client_name = f"{client.first_name or ''} {client.last_name or ''}".strip()
        plan_content = (
            f"JUDGMENT RECOVERY PLAN — {client_name}\n\n"
            "AI generation unavailable (ANTHROPIC_API_KEY not configured).\n\n"
            "Please review the intake data and prepare a manual recovery plan."
        )

    doc = ServiceDocument(
        service_case_id=service_case_id,
        client_id=case.client_id,
        template_id=None,
        division_slug="judgment",
        title=f"Recovery Plan — {case.case_number}",
        document_type="recovery_plan",
        content=plan_content,
        status="draft",
        ai_generated=ai_generated,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "title": doc.title,
        "content": plan_content,
        "ai_generated": ai_generated,
    }
