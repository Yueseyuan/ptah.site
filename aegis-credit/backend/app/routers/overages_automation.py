"""Tax Overage Recovery automation — surplus scraping, owner locate, email campaigns, and document generation.

OmniRoute Fusion pattern: parallel agent panel → judge synthesis → authoritative report.
Graceful degradation: AI failures return structured stub rather than 503.
"""

import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Callable, Optional, TypeVar

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

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

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


def _run_agent_loop(
    key: str,
    system: str,
    user_msg: str,
    model: str = _AI_MODEL,
    max_rounds: int = 5,
) -> str:
    """Single tool-use loop: search_web + fetch_page via Jina."""
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
# OmniRoute Fusion helpers
# ---------------------------------------------------------------------------

def _fusion_parallel(tasks: list, key: str, max_workers: int = 4) -> list:
    """Fan out N agent tasks in parallel, collect all results (OmniRoute Fusion pattern).

    Each task: {"label": str, "system": str, "user_msg": str, "model"?: str}
    Returns list of result strings in completion order.
    """
    def run_task(t: dict) -> str:
        try:
            return _run_agent_loop(
                key, t["system"], t["user_msg"], model=t.get("model", _AI_MODEL)
            )
        except Exception as exc:
            return f"[{t.get('label', 'agent')} error: {exc}]"

    results = [""] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(run_task, t): i for i, t in enumerate(tasks)}
        for future in as_completed(future_to_idx):
            results[future_to_idx[future]] = future.result()

    return results


def _judge_synthesize(key: str, topic: str, panel_results: list) -> str:
    """Synthesize parallel panel results into one authoritative report (Fusion judge step)."""
    combined = "\n\n--- PANEL RESULT ---\n".join(
        f"[Source {i + 1}: {label}]\n{r}"
        for i, (label, r) in enumerate(panel_results)
    )
    prompt = (
        f"You are a senior analyst synthesizing parallel research results about: {topic}\n\n"
        f"The following {len(panel_results)} research reports were produced independently "
        f"from different search angles:\n\n{combined}\n\n"
        "Synthesis tasks:\n"
        "1. AGREEMENTS — facts confirmed by multiple sources (high confidence)\n"
        "2. CONTRADICTIONS — note which source is more credible and why\n"
        "3. GAPS — information no source covered; flag for manual follow-up\n"
        "4. AUTHORITATIVE REPORT — one clean, consolidated summary\n"
        "5. CONFIDENCE LEVEL — High / Medium / Low with brief rationale\n\n"
        "Format the final report clearly with section headers."
    )
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=_AI_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else "Synthesis unavailable."


def _with_degradation(primary: Callable[[], str], stub: str) -> str:
    """OmniRoute graceful degradation: run primary(); on AI failure return stub."""
    try:
        return primary()
    except (
        anthropic.AuthenticationError,
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
    ):
        return stub
    except Exception as exc:
        if "ANTHROPIC" in str(exc).upper() or "anthropic" in str(exc).lower():
            return stub
        raise


# ---------------------------------------------------------------------------
# Scrape Surplus  (Fusion: 4-agent panel → judge)
# ---------------------------------------------------------------------------

@router.post("/{service_case_id}/scrape-surplus", status_code=201)
def scrape_surplus(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fusion agent panel searches county surplus / tax deed records from four angles,
    then a judge synthesizes contradictions and gaps into one authoritative report."""
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

    base_system = (
        "You are a surplus fund research specialist for a contingency recovery firm. "
        "Search publicly available county clerk, tax collector, and court records. "
        "Be specific. Cite every URL you find. Flag any discrepancies or missing data."
    )

    # Fusion panel: four distinct search angles
    tasks = [
        {
            "label": "county-clerk",
            "system": base_system,
            "user_msg": (
                f"Search the {county} County Clerk's surplus fund list or registry. "
                f"Owner: {owner}. Parcel: {parcel}. Tax Deed: {tax_deed}. "
                "Confirm surplus amount, claim filing status, and deadline. "
                "Find the official surplus claim form URL and submission address."
            ),
        },
        {
            "label": "tax-collector",
            "system": base_system,
            "user_msg": (
                f"Search the {county} County Tax Collector and Property Appraiser websites. "
                f"Parcel/Folio: {parcel}. Tax Deed: {tax_deed}. "
                "Find the tax deed sale date, opening bid, final sale price, and calculated surplus. "
                "Check for any outstanding liens, mortgages, or IRS levies that could reduce net surplus."
            ),
        },
        {
            "label": "court-records",
            "system": base_system,
            "user_msg": (
                f"Search court records and CourtListener for {county} tax deed case {tax_deed}. "
                f"Former owner: {owner}. Parcel: {parcel}. "
                "Identify any competing claimants, lienholders, or attorneys who have filed for the surplus. "
                "Check if a disbursement order has been issued."
            ),
        },
        {
            "label": "general-web",
            "system": base_system,
            "user_msg": (
                f"Do a broad web search for surplus funds in {county} County for parcel {parcel} "
                f"or tax deed {tax_deed}, former owner {owner}. "
                "Look for news articles, legal notices, or third-party surplus databases "
                "(e.g., surplusfundshub.com, overage.io). "
                "Cross-check any surplus amounts found against public records."
            ),
        },
    ]

    stub = (
        "## Surplus Verification — Manual Review Required\n\n"
        "AI-assisted search is temporarily unavailable.\n\n"
        f"**Case:** {county} / {parcel or tax_deed}\n"
        f"**Former Owner:** {owner}\n\n"
        "**Next Steps (manual):**\n"
        f"1. Visit {county} County Clerk website and search surplus fund list\n"
        "2. Search property appraiser for parcel details and tax deed sale history\n"
        "3. Check court records for competing claimants\n"
        "4. Confirm claim deadline directly with the clerk's office\n\n"
        "_This document was generated by the graceful-degradation fallback. "
        "Re-run once AI service is restored._"
    )

    def _fusion_surplus() -> str:
        panel = _fusion_parallel(tasks, key)
        labeled = list(zip([t["label"] for t in tasks], panel))
        topic = f"Tax deed surplus verification — {county}, Parcel {parcel or tax_deed}, Owner: {owner}"
        return _judge_synthesize(key, topic, labeled)

    content = _with_degradation(_fusion_surplus, stub)

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
# Locate Owner  (Fusion: 4-agent panel → judge)
# ---------------------------------------------------------------------------

@router.post("/{service_case_id}/locate-owner", status_code=201)
def locate_owner(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fusion agent panel skip-traces the former owner via four parallel search angles,
    then a judge synthesizes the best contact info with confidence levels."""
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

    base_system = (
        "You are a skip-trace specialist for a surplus fund recovery firm. "
        "Search only publicly available, legal sources to locate current contact information. "
        "Return: mailing address, phone(s), email(s), confidence per item, source URLs. "
        "Flag if owner appears deceased, incarcerated, or part of an estate/probate."
    )

    tasks = [
        {
            "label": "property-appraiser",
            "system": base_system,
            "user_msg": (
                f"Search the {county} County Property Appraiser's public records for the mailing "
                f"address of former owner: {owner}. Parcel: {parcel}. Property: {prop_desc}. "
                "Also check for any homestead exemption or subsequent property purchases by this person."
            ),
        },
        {
            "label": "voter-court-records",
            "system": base_system,
            "user_msg": (
                f"Search voter registration records and court filings in {county} County for "
                f"{owner}. Look for a current residential address, phone, or email. "
                "Also search Florida (or relevant state) court records for any civil or criminal cases "
                "that include an address for this person."
            ),
        },
        {
            "label": "business-linkedin",
            "system": base_system,
            "user_msg": (
                f"Search business registration records, LinkedIn, and professional directories "
                f"for {owner} in or around {county} County. "
                "Look for a business they own or work at that could provide a contact address or email. "
                "Check for a spouse or business partner who may be reachable."
            ),
        },
        {
            "label": "public-people-search",
            "system": base_system,
            "user_msg": (
                f"Search public people-search sites (WhitePages, Spokeo public results, BeenVerified "
                f"preview, FastPeopleSearch) for {owner} near {county} County. "
                "Cross-reference any address found with the known property address. "
                "Check for aliases, maiden name, or known relatives who may have current contact info."
            ),
        },
    ]

    stub = (
        "## Owner Locate Report — Manual Review Required\n\n"
        "AI-assisted skip-trace is temporarily unavailable.\n\n"
        f"**Subject:** {owner}\n"
        f"**County:** {county}\n"
        f"**Parcel:** {parcel}\n\n"
        "**Manual Skip-Trace Steps:**\n"
        f"1. {county} County Property Appraiser — mailing address on file\n"
        "2. State voter registration records\n"
        "3. WhitePages / FastPeopleSearch public lookup\n"
        "4. County court docket search for defendant/plaintiff address\n"
        "5. LinkedIn / social media search\n"
        "6. Check for estate/probate if owner may be deceased\n\n"
        "_Re-run once AI service is restored._"
    )

    def _fusion_locate() -> str:
        panel = _fusion_parallel(tasks, key)
        labeled = list(zip([t["label"] for t in tasks], panel))
        topic = f"Skip-trace: locate former owner {owner}, {county} County, Parcel {parcel}"
        return _judge_synthesize(key, topic, labeled)

    content = _with_degradation(_fusion_locate, stub)

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

    stub = (
        "## Email Campaign — Draft Pending\n\n"
        "AI email generation is temporarily unavailable. "
        "Please use the template below as a starting point and customize manually.\n\n"
        "---\n\n"
        "**EMAIL 1 — Initial Contact**\n"
        f"Subject: Important Notice Regarding Unclaimed Funds — {county} County\n\n"
        f"Dear {owner},\n\n"
        "We are reaching out regarding unclaimed surplus funds from a tax deed sale "
        f"on your former property in {county} County. You may be entitled to recover "
        f"{surplus_str}.\n\n"
        "Please contact us to learn more. There is no upfront cost — we work on contingency.\n\n"
        f"Sincerely,\n{rep_name}\nCruel & Associates\ninfo@cruelandassociates.com\n\n"
        "_Re-run once AI service is restored for fully personalized emails._"
    )

    def _generate_campaign() -> str:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text if resp.content else "No response generated."

    content = _with_degradation(_generate_campaign, stub)

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

DOC_TYPE_MAP = {
    "assignment_of_rights":    "Assignment of Rights",
    "assignment_of_judgment":  "Assignment of Judgment",
    "fee_agreement":           "Fee Agreement (60/40 Contingency)",
    "power_of_attorney":       "Limited Power of Attorney (Surplus Claim)",
    "purchase_agreement":      "Purchase Agreement (Surplus Rights)",
    "purchase_sale_agreement": "Purchase and Sale Agreement",
    "quitclaim_deed":          "Quitclaim Deed",
    "pre_estate_agreement":    "Pre-Estate Agreement",
    "notary_affidavit":        "Notary Affidavit (Surplus Claim)",
    # Legacy templates
    "contingency_agreement":   "Asset Recovery Contingency Agreement",
    "authorization":           "Authorization to Recover Funds",
    "non_lawyer_disclosure":   "Non-Lawyer Disclosure (Tax Overage Recovery)",
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
        "full_name":            intake.get("owner_name", base_vars.get("full_name", "")),
        "address":              intake.get("owner_address", base_vars.get("address", "")),
        "phone":                intake.get("owner_phone", base_vars.get("phone", "")),
        "email":                intake.get("owner_email", base_vars.get("email", "")),
        "company_name":         "Cruel & Associates",
        "company_address":      "456 Service Lane, Columbia, SC 29201",
        "company_phone":        "(803) 555-0200",
        "company_email":        "info@cruelandassociates.com",
        "assigned_to":          case.assigned_to or "Recovery Specialist",
        "case_number":          case.case_number or "",
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
