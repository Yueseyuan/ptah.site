"""Tax Overage Recovery automation — surplus scraping, owner locate, email campaigns, and document generation."""

import json
import os
import urllib.parse
import urllib.request
from datetime import date
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, DocumentTemplate, ServiceCase, ServiceDocument, User
from app.services.document_service import get_client_template_vars, render_template

router = APIRouter(prefix="/api/overages", tags=["overages-automation"])
_AI_MODEL = "claude-sonnet-5"
_HAIKU_MODEL = "claude-haiku-4-5-20251001"


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _parse_intake(case: ServiceCase) -> dict:
    if not case.intake_data:
        return {}
    try:
        return json.loads(case.intake_data)
    except Exception:
        return {}


def _require_overages(case: Optional[ServiceCase], case_id: int) -> ServiceCase:
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.division_slug != "overages":
        raise HTTPException(status_code=400, detail="Case is not in the overages division")
    return case


def _jina_search(query: str) -> str:
    url = f"https://s.jina.ai/{urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"Accept": "text/plain", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read().decode("utf-8", errors="replace")[:4000]
    except Exception as exc:
        return f"[search error: {exc}]"


def _jina_fetch(url: str) -> str:
    fetch_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(fetch_url, headers={"Accept": "text/plain", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read().decode("utf-8", errors="replace")[:4000]
    except Exception as exc:
        return f"[fetch error: {exc}]"


def _run_agent_loop(key: str, system: str, user_msg: str, model: str = _AI_MODEL, max_rounds: int = 5) -> str:
    """Tool-use loop: search_web + fetch_page via Jina."""
    tools = [
        {
            "name": "search_web",
            "description": "Search the web using Jina AI. Returns plain text results.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "fetch_page",
            "description": "Fetch the full text content of a web page via Jina Reader.",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    ]

    client = anthropic.Anthropic(api_key=key)
    messages = [{"role": "user", "content": user_msg}]

    for _ in range(max_rounds):
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            tools=tools,
            messages=messages,
        )

        if resp.stop_reason == "end_turn":
            return "\n".join(b.text for b in resp.content if hasattr(b, "text"))

        if resp.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "search_web":
                content = _jina_search(block.input.get("query", ""))
            elif block.name == "fetch_page":
                content = _jina_fetch(block.input.get("url", ""))
            else:
                content = "Unknown tool."
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})

        messages.append({"role": "user", "content": results})

    return "\n".join(b.text for b in resp.content if hasattr(b, "text")) or "Agent loop completed."


# ---------------------------------------------------------------------------
# Scrape Surplus
# ---------------------------------------------------------------------------

@router.post("/{service_case_id}/scrape-surplus", status_code=201)
def scrape_surplus(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent searches county surplus / tax deed sale records to verify the overage amount and claim status."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    _require_overages(case, service_case_id)

    key = _api_key()
    if not key or len(key) < 50:
        raise HTTPException(status_code=503, detail="AI service not configured. Set ANTHROPIC_API_KEY.")

    intake = _parse_intake(case)
    county = intake.get("county", "Unknown County")
    parcel = intake.get("parcel_folio", "")
    tax_deed = intake.get("tax_deed_number", "")
    owner = intake.get("owner_name", "")

    system = (
        "You are a surplus fund research specialist for a contingency recovery firm. "
        "Search publicly available county clerk, tax collector, and court records to verify "
        "tax deed surplus / excess proceeds information. Return a structured report."
    )
    user_msg = (
        f"Verify and gather surplus fund information for the following tax deed case:\n\n"
        f"County: {county}\n"
        f"Former Owner: {owner}\n"
        f"Parcel / Folio: {parcel}\n"
        f"Tax Deed Number: {tax_deed}\n\n"
        "Tasks:\n"
        "1. Search the county clerk's surplus fund list or tax deed sale records\n"
        "2. Confirm the surplus / excess proceeds amount\n"
        "3. Check if a claim has already been filed\n"
        "4. Identify claim filing deadline (if published)\n"
        "5. Note any competing claimants or liens\n"
        "6. Find the exact claim submission address and process\n\n"
        "Be specific. Cite the URLs you find. Flag any discrepancies."
    )

    try:
        content = _run_agent_loop(key, system, user_msg)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI authentication failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(exc)[:200]}")

    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=case.client_id,
        division_slug="overages",
        title=f"Surplus Verification — {county} / {parcel or tax_deed}",
        document_type="Surplus Scrape Report",
        content=content,
        status="draft",
        ai_generated=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.id, "title": doc.title, "content": content}


# ---------------------------------------------------------------------------
# Locate Owner
# ---------------------------------------------------------------------------

@router.post("/{service_case_id}/locate-owner", status_code=201)
def locate_owner(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent searches public records to locate the former property owner's current contact info."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    _require_overages(case, service_case_id)

    key = _api_key()
    if not key or len(key) < 50:
        raise HTTPException(status_code=503, detail="AI service not configured. Set ANTHROPIC_API_KEY.")

    intake = _parse_intake(case)
    owner = intake.get("owner_name", "Unknown Owner")
    county = intake.get("county", "Unknown County")
    parcel = intake.get("parcel_folio", "")
    prop_desc = intake.get("property_description", "")

    system = (
        "You are a skip-trace specialist for a surplus fund recovery firm. "
        "Search only publicly available, legal sources to locate current contact information "
        "for a former property owner who may be entitled to tax deed surplus funds. "
        "Never use private databases or non-public information."
    )
    user_msg = (
        f"Locate current contact information for this former property owner:\n\n"
        f"Name: {owner}\n"
        f"County: {county}\n"
        f"Property: {prop_desc or parcel}\n\n"
        "Search public sources:\n"
        "1. County property appraiser mailing address records\n"
        "2. Voter registration records (if publicly available in this state)\n"
        "3. Court case records for a current address\n"
        "4. Business registration records (if owner had a business)\n"
        "5. Social media / LinkedIn / public profiles\n"
        "6. White Pages / Spokeo-style public data\n\n"
        "Return:\n"
        "- Current mailing address (or best known address)\n"
        "- Phone number(s)\n"
        "- Email address(es)\n"
        "- Confidence level for each\n"
        "- Source URLs\n"
        "- Any aliases or related persons (spouse, estate heir, etc.)\n"
        "- Skip-trace difficulty assessment\n\n"
        "Flag if owner appears deceased — note any estate or probate indicators."
    )

    try:
        content = _run_agent_loop(key, system, user_msg)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI authentication failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(exc)[:200]}")

    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=case.client_id,
        division_slug="overages",
        title=f"Owner Locate Report — {owner}",
        document_type="Owner Locate Report",
        content=content,
        status="draft",
        ai_generated=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.id, "title": doc.title, "content": content}


# ---------------------------------------------------------------------------
# Email Campaign
# ---------------------------------------------------------------------------

@router.post("/{service_case_id}/email-campaign", status_code=201)
def email_campaign(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a personalized 3-email outreach sequence for the former property owner."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    _require_overages(case, service_case_id)

    key = _api_key()
    if not key or len(key) < 50:
        raise HTTPException(status_code=503, detail="AI service not configured. Set ANTHROPIC_API_KEY.")

    intake = _parse_intake(case)
    owner = intake.get("owner_name", "Former Owner")
    county = intake.get("county", "the county")
    surplus = intake.get("estimated_surplus", "")
    parcel = intake.get("parcel_folio", "")
    prop_desc = intake.get("property_description", "your former property")
    fee_pct = intake.get("fee_percentage", 40)

    surplus_str = f"${float(surplus):,.2f}" if surplus else "funds you may be owed"
    client_pct = 100 - int(fee_pct)

    client_obj = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    rep_name = case.assigned_to or "Recovery Specialist"

    prompt = (
        "You are a professional outreach specialist for Cruel & Associates, a legitimate "
        "surplus fund recovery firm. Write 3 personalized outreach emails — initial contact, "
        "7-day follow-up, and 14-day final notice — to a former property owner regarding "
        "unclaimed tax deed surplus funds.\n\n"
        f"CASE DETAILS:\n"
        f"Former Owner: {owner}\n"
        f"County: {county}\n"
        f"Property: {prop_desc or parcel}\n"
        f"Estimated Surplus: {surplus_str}\n"
        f"Our Fee: {fee_pct}% (you keep {client_pct}%)\n"
        f"Recovery Specialist: {rep_name}\n\n"
        "REQUIREMENTS:\n"
        "- Professional, empathetic, non-pressuring tone\n"
        "- Clearly explain what surplus funds are\n"
        "- Be transparent about the contingency fee structure\n"
        "- Include a clear call-to-action (call or email us)\n"
        "- Mention the claim deadline urgency without being alarmist\n"
        "- Include standard non-attorney disclaimer\n"
        "- No deceptive claims or false urgency\n\n"
        "FORMAT: Label each email clearly as EMAIL 1, EMAIL 2, EMAIL 3 with Subject line, "
        "body, and signature block."
    )

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.content[0].text if resp.content else "No response generated."
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI authentication failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(exc)[:200]}")

    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=case.client_id,
        division_slug="overages",
        title=f"Email Campaign — {owner} ({county})",
        document_type="Email Campaign",
        content=content,
        status="draft",
        ai_generated=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document_id": doc.id, "title": doc.title, "content": content}


# ---------------------------------------------------------------------------
# Document Generation (pre-fill from templates)
# ---------------------------------------------------------------------------

# Maps frontend doc_type keys → template names in DB
DOC_TYPE_MAP = {
    "assignment_of_rights":     "Assignment of Rights",
    "assignment_of_judgment":   "Assignment of Judgment",
    "fee_agreement":            "Fee Agreement (60/40 Contingency)",
    "power_of_attorney":        "Limited Power of Attorney (Surplus Claim)",
    "purchase_agreement":       "Purchase Agreement (Surplus Rights)",
    "purchase_sale_agreement":  "Purchase and Sale Agreement",
    "quitclaim_deed":           "Quitclaim Deed",
    "pre_estate_agreement":     "Pre-Estate Agreement",
    "notary_affidavit":         "Notary Affidavit (Surplus Claim)",
    # Also support generating existing legacy templates by their name
    "contingency_agreement":    "Asset Recovery Contingency Agreement",
    "authorization":            "Authorization to Recover Funds",
    "non_lawyer_disclosure":    "Non-Lawyer Disclosure (Tax Overage Recovery)",
}


class GenerateDocRequest(BaseModel):
    doc_type: str


@router.post("/{service_case_id}/generate-doc", status_code=201)
def generate_doc(
    service_case_id: int,
    body: GenerateDocRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pre-fill a legal document from a template using intake data and client info."""
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    _require_overages(case, service_case_id)

    template_name = DOC_TYPE_MAP.get(body.doc_type)
    if not template_name:
        raise HTTPException(status_code=400, detail=f"Unknown doc_type: '{body.doc_type}'")

    tmpl = (
        db.query(DocumentTemplate)
        .filter(
            DocumentTemplate.name == template_name,
            DocumentTemplate.division_slug == "overages",
        )
        .first()
    )
    if not tmpl:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found. Run POST /api/templates/seed first.",
        )

    # Build variables from client + case
    client_obj = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    intake = _parse_intake(case)

    base_vars: dict = {}
    if client_obj:
        base_vars = get_client_template_vars(client_obj, case)

    today_str = date.today().strftime("%B %d, %Y")
    surplus_raw = intake.get("estimated_surplus", "")
    try:
        surplus_fmt = f"${float(surplus_raw):,.2f}" if surplus_raw else ""
    except (ValueError, TypeError):
        surplus_fmt = str(surplus_raw)

    fee_pct = intake.get("fee_percentage", 40)
    try:
        fee_pct_int = int(float(fee_pct))
    except (ValueError, TypeError):
        fee_pct_int = 40
    client_pct = 100 - fee_pct_int

    # Override / augment with intake fields (overages-specific)
    overage_vars = {
        "date":                 today_str,
        "signature_date":       today_str,
        "county":               intake.get("county", ""),
        "parcel_folio":         intake.get("parcel_folio", ""),
        "tax_deed_number":      intake.get("tax_deed_number", ""),
        "property_description": intake.get("property_description", ""),
        "estimated_surplus":    surplus_fmt or intake.get("estimated_surplus", ""),
        "opening_bid":          intake.get("opening_bid", ""),
        "sale_price":           intake.get("sale_price", ""),
        "fee_percentage":       f"{fee_pct_int}%",
        "client_percentage":    f"{client_pct}%",
        "fee":                  f"{fee_pct_int}%",
        # Allow intake to supply owner contact if different from registered client
        "full_name":            intake.get("owner_name", base_vars.get("full_name", "")),
        "address":              intake.get("owner_address", base_vars.get("address", "")),
        "phone":                intake.get("owner_phone", base_vars.get("phone", "")),
        "email":                intake.get("owner_email", base_vars.get("email", "")),
        # Company constants
        "company_name":         "Cruel & Associates",
        "company_address":      "456 Service Lane, Columbia, SC 29201",
        "company_phone":        "(803) 555-0200",
        "company_email":        "info@cruelandassociates.com",
        "assigned_to":          case.assigned_to or "Recovery Specialist",
        "case_number":          case.case_number or "",
        # Notary / affidavit fields
        "notary_name":          intake.get("notary_name", "[Notary Name]"),
        "notary_commission":    intake.get("notary_commission", "[Commission No.]"),
        "notary_expiry":        intake.get("notary_expiry", "[Expiry Date]"),
        "state":                intake.get("state", base_vars.get("state", "Florida")),
        "notes":                case.notes or "",
    }

    all_vars = {**base_vars, **overage_vars}
    rendered = render_template(tmpl.content, all_vars)

    doc = ServiceDocument(
        service_case_id=case.id,
        client_id=case.client_id,
        division_slug="overages",
        title=f"{template_name} — {all_vars.get('full_name', 'Owner')}",
        document_type=template_name,
        content=rendered,
        status="draft",
        ai_generated=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {
        "document_id": doc.id,
        "title": doc.title,
        "content": rendered,
        "template_name": template_name,
    }
