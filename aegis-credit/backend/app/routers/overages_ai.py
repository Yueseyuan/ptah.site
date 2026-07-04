"""AI-powered lead scoring and case analysis for the Tax Overage Recovery division."""

import json
import os

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ServiceCase, ServiceDocument, User

router = APIRouter(prefix="/api/overages", tags=["overages-ai"])
_AI_MODEL = "claude-haiku-4-5-20251001"


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _parse_intake(case: ServiceCase) -> dict:
    if not case.intake_data:
        return {}
    try:
        return json.loads(case.intake_data)
    except Exception:
        return {}


@router.post("/{service_case_id}/score-lead", status_code=201)
def score_lead(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an AI lead score (1–100) and priority analysis for a tax overage case."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.division_slug != "overages":
        raise HTTPException(status_code=400, detail="Case is not in the overages division")

    key = _api_key()
    if not key or len(key) < 50:
        raise HTTPException(status_code=503, detail="AI service is not configured. Set ANTHROPIC_API_KEY.")

    intake = _parse_intake(case)

    prompt = (
        "You are a tax deed excess proceeds specialist helping a contingency recovery firm "
        "score lead quality for a potential surplus funds claim.\n\n"
        "CASE DATA:\n"
        f"County: {intake.get('county', 'Unknown')}\n"
        f"Owner Name: {intake.get('owner_name', 'Unknown')}\n"
        f"Parcel / Folio: {intake.get('parcel_folio', 'Unknown')}\n"
        f"Tax Deed Number: {intake.get('tax_deed_number', 'Unknown')}\n"
        f"Property Description: {intake.get('property_description', 'Not provided')}\n"
        f"Opening Bid: ${intake.get('opening_bid', '0')}\n"
        f"Sale Price: ${intake.get('sale_price', '0')}\n"
        f"Estimated Surplus: ${intake.get('estimated_surplus', '0')}\n"
        f"Claim Status: {intake.get('claim_status', 'Unclaimed')}\n"
        f"Case Complexity: {intake.get('case_complexity', 'Unknown')}\n\n"
        "Provide a structured lead score report:\n"
        "1. LEAD SCORE (1–100 with brief rationale)\n"
        "2. PRIORITY (High / Medium / Low)\n"
        "3. SURPLUS VIABILITY (Is the surplus amount worth pursuing?)\n"
        "4. OWNER LOCATE DIFFICULTY (Easy / Moderate / Hard / Very Hard)\n"
        "5. CLAIM COMPLEXITY (Simple / Moderate / Complex)\n"
        "6. RECOMMENDED NEXT STEP (one specific action)\n"
        "7. RED FLAGS (if any — competing claimants, legal holds, bankruptcy, etc.)\n"
        "8. ESTIMATED NET FEE (at 35% of surplus, minus estimated costs)\n\n"
        "Keep each section to 2–3 sentences. Be direct and actionable.\n"
        "Do NOT include legal advice. This is operational analysis for a non-attorney recovery firm."
    )

    try:
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=_AI_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text if response.content else "No response generated."
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI authentication failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(exc)[:200]}")

    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=case.client_id,
        division_slug="overages",
        title=f"Lead Score Analysis — {intake.get('owner_name', 'Owner')} ({intake.get('county', 'County')})",
        document_type="Lead Score Report",
        content=content,
        status="draft",
        ai_generated=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "title": doc.title,
        "content": content,
        "ai_generated": True,
    }
