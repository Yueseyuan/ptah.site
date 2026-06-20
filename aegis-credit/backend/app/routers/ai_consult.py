from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import anthropic

from app.database import get_db
from app.models import AegisCase, Finding
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/ai-consult", tags=["ai_consult"])

AI_MODEL = "claude-sonnet-4-6"

CONSULT_DISCLAIMER = (
    "This analysis is for investigator review only. It does not constitute legal advice "
    "and does not guarantee any outcome. Consult a licensed attorney before taking legal action."
)


def _client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


class ConsultRequest(BaseModel):
    finding_id: Optional[int] = None
    user_theory: str
    law_reference: Optional[str] = None
    context: Optional[str] = None


@router.post("/case/{case_id}")
def consult_ai(
    case_id: int,
    body: ConsultRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    finding_context = ""
    if body.finding_id is not None:
        finding = db.query(Finding).filter(Finding.id == body.finding_id).first()
        if finding:
            finding_context = (
                f"\n\nFINDING DETAILS:\n"
                f"  Title: {finding.title}\n"
                f"  Type: {finding.finding_type}\n"
                f"  Severity: {finding.severity}\n"
                f"  FCRA Section: {finding.fcra_section or 'N/A'}\n"
                f"  Description: {finding.description or 'N/A'}"
            )

    law_ref_line = f"\nLaw/Rule Reference cited by investigator: {body.law_reference}" if body.law_reference else ""
    extra_context = f"\nAdditional context: {body.context}" if body.context else ""

    prompt = f"""You are a credit law expert assisting a licensed credit investigator (NOT a consumer).
This analysis is strictly for internal investigator use and will be reviewed by a licensed attorney before any action.

CASE INFORMATION:
  Case Number: {case.case_number}
  Case Status: {case.status}
  Case Goal: {case.goal or 'Not specified'}
{finding_context}

INVESTIGATOR'S LEGAL THEORY:
{body.user_theory}
{law_ref_line}
{extra_context}

Evaluate the investigator's legal theory and provide a structured analysis covering ALL of the following sections:

**1. ACCURACY**
Is the theory legally accurate? Cite specific statutes, regulations, or case law that support or contradict it.

**2. APPLICABILITY**
Does this theory apply to the specific finding and facts described above? Explain why or why not.

**3. STRENGTH**
Rate the overall strength: Strong / Moderate / Weak / Inapplicable. Justify your rating.

**4. SUPPORTING LAW**
List additional statutes, regulations, or case law (with citations) that strengthen this theory.

**5. COUNTERARGUMENTS**
What arguments will the opposing party (bureau/furnisher/collector) likely raise? How strong are those counterarguments?

**6. EVIDENCE NEEDED**
What specific documentation, records, or proof should the investigator gather to support this theory?

**7. RECOMMENDED ACTION**
What is the recommended next step: dispute letter to bureau/furnisher, CFPB complaint, FTC complaint, state AG complaint, demand letter, or civil litigation? Explain why.

Be specific and cite statutes (e.g., FCRA § 611, FDCPA § 809(b), FCRA § 623) and relevant case law where applicable.
Do NOT provide legal advice to consumers. This analysis is for a licensed credit investigator's internal use only."""

    try:
        client = _client()
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = message.content[0].text
    except Exception as exc:
        raise HTTPException(500, f"AI consultation failed: {exc}")

    return {
        "analysis": analysis,
        "finding_id": body.finding_id,
        "user_theory": body.user_theory,
        "law_reference": body.law_reference,
        "disclaimer": CONSULT_DISCLAIMER,
    }
