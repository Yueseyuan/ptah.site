"""Structured data pulls from public legal/financial databases (Agent-Reach pattern).

Sources:
  courts   — CourtListener REST API (federal + state court dockets)
  cfpb     — CFPB Consumer Complaint Database API
  property — County property appraiser via Jina Reader + Claude extraction
  business — State SOS business registry via Jina Reader + Claude extraction
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisCase, ServiceCase, ServiceDocument, User

router = APIRouter(prefix="/api/data-pulls", tags=["data-pulls"])

_JINA_READ = "https://r.jina.ai/"
_COURTLISTENER = "https://www.courtlistener.com/api/rest/v4/dockets/"
_CFPB_API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"

# ── County property appraiser search URLs (FL-focused) ─────────────────────────
_COUNTY_URLS = {
    "broward":    "https://www.bcpa.net/RecInfo.asp?URL_Owner={name}&searchType=OWNER",
    "miami-dade": "https://www.miamidade.gov/apps/PA/propertysearch/#/?ST=LS&QT=LS&Q={name}",
    "palm-beach": "https://pbcpao.gov/property-search/?name={name}",
    "orange":     "https://www.ocpafl.org/Searches/ParcelSearch.aspx?sid=&ptype=1&name={name}",
    "hillsborough": "https://www.hcpafl.org/LinkClick.aspx?fileticket=search&name={name}",
}

# ── State SOS business registry URLs ───────────────────────────────────────────
_SOS_URLS = {
    "FL": "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?inquiryType=EntityName&inquiryDirectionType=ForwardList&searchNameOrder=&masterDataType=Master&searchTerm={name}&listNameOrder=",
    "TX": "https://mycpa.cpa.state.tx.us/coa/Index.do#",
    "CA": "https://bizfileonline.sos.ca.gov/search/business",
    "NY": "https://apps.dos.ny.gov/publicInquiry/",
    "GA": "https://ecorp.sos.ga.gov/BusinessSearch/BusinessInformation?businessId=&businessType=&businessStatus=A&filingType=All&nameType=CN&searchTerm={name}",
}


class PullRequest(BaseModel):
    source: str          # "courts" | "cfpb" | "property" | "business"
    query: str           # main search term
    params: dict = {}    # source-specific: county, state, etc.
    case_id: Optional[int] = None
    service_case_id: Optional[int] = None


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _http_get(url: str, accept: str = "application/json", timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AegisData/1.0",
            "Accept": accept,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return f"[HTTP error: {exc}]"


def _jina(url: str) -> str:
    raw = _http_get(f"{_JINA_READ}{url}", accept="text/plain")
    return raw[:5000]


def _claude_extract(key: str, raw: str, instruction: str) -> str:
    """Use Claude to extract structured info from raw text."""
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"{instruction}\n\nRAW DATA:\n{raw[:4000]}"
        }],
    )
    return resp.content[0].text if resp.content else "No data extracted."


# ── Court record pull ───────────────────────────────────────────────────────────

def _pull_courts(query: str, params: dict, key: str) -> tuple[str, str]:
    """Query CourtListener API for court dockets matching a party name."""
    q = urllib.parse.quote(query)
    url = f"{_COURTLISTENER}?q={q}&type=d&format=json&page_size=10"
    raw = _http_get(url)
    try:
        data = json.loads(raw)
    except Exception:
        return "Court record search unavailable.", "courts"

    count = data.get("count", 0)
    results = data.get("results", [])

    lines = [f"**CourtListener search: '{query}'** — {count} cases found\n"]
    for r in results[:10]:
        name = r.get("case_name") or "Unknown"
        docket = r.get("docket_number") or ""
        court = r.get("court") or ""
        filed = r.get("date_filed") or "?"
        link = f"https://www.courtlistener.com{r.get('absolute_url', '')}"
        lines.append(f"• **{name}** | {docket} | {court} | Filed: {filed}\n  {link}")

    if not results:
        lines.append("No matching court dockets found in CourtListener.")

    return "\n".join(lines), "courts"


# ── CFPB complaint pull ─────────────────────────────────────────────────────────

def _pull_cfpb(query: str, params: dict, key: str) -> tuple[str, str]:
    """Query CFPB complaint database for a company name."""
    q = urllib.parse.quote(query)
    url = f"{_CFPB_API}?size=25&search_term={q}&field=all&sort=created_date_desc"
    raw = _http_get(url)
    try:
        data = json.loads(raw)
    except Exception:
        return "CFPB search unavailable.", "cfpb"

    hits = data.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else total
    records = hits.get("hits", [])

    lines = [f"**CFPB Complaints: '{query}'** — {total_count} total complaints\n"]

    # Aggregate by product and issue
    products: dict = {}
    issues: dict = {}
    for rec in records:
        src = rec.get("_source", {})
        p = src.get("product", "Other")
        iss = src.get("issue", "Other")
        products[p] = products.get(p, 0) + 1
        issues[iss] = issues.get(iss, 0) + 1

    if products:
        lines.append("**Top Products:**")
        for p, n in sorted(products.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  • {p}: {n}")

    if issues:
        lines.append("\n**Top Issues:**")
        for iss, n in sorted(issues.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  • {iss}: {n}")

    lines.append(f"\n*Source: CFPB Consumer Complaint Database — consumerfinance.gov*")
    return "\n".join(lines), "cfpb"


# ── Property record pull ────────────────────────────────────────────────────────

def _pull_property(query: str, params: dict, key: str) -> tuple[str, str]:
    """Fetch county property appraiser records via Jina Reader."""
    county = params.get("county", "broward").lower()
    tmpl = _COUNTY_URLS.get(county, _COUNTY_URLS["broward"])
    url = tmpl.format(name=urllib.parse.quote(query.replace(" ", "+")))
    raw = _jina(url)

    instruction = (
        "Extract all property records from this county appraiser page. "
        "For each property list: owner name, parcel/folio number, property address, "
        "assessed value, market value, and any tax information. "
        "Format as a clean bulleted list. If no records found, say so clearly."
    )
    extracted = _claude_extract(key, raw, instruction)
    result = f"**{county.title()} County Property Records: '{query}'**\n\n{extracted}"
    return result, "property"


# ── Business registry pull ──────────────────────────────────────────────────────

def _pull_business(query: str, params: dict, key: str) -> tuple[str, str]:
    """Fetch state SOS business registry records via Jina Reader."""
    state = params.get("state", "FL").upper()
    tmpl = _SOS_URLS.get(state, _SOS_URLS["FL"])
    url = tmpl.format(name=urllib.parse.quote(query))
    raw = _jina(url)

    instruction = (
        "Extract business entity information from this state Secretary of State page. "
        "For each entity list: company name, document number, status (active/inactive), "
        "principal address, registered agent, date filed/formed, and officer/director names. "
        "Format as a clean bulleted list. If no records found, say so clearly."
    )
    extracted = _claude_extract(key, raw, instruction)
    result = f"**{state} Business Registry: '{query}'**\n\n{extracted}"
    return result, "business"


# ── Source router ───────────────────────────────────────────────────────────────

_HANDLERS = {
    "courts":   _pull_courts,
    "cfpb":     _pull_cfpb,
    "property": _pull_property,
    "business": _pull_business,
}


@router.post("", status_code=201)
def run_data_pull(
    body: PullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    handler = _HANDLERS.get(body.source)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown source '{body.source}'. Use: courts, cfpb, property, business")

    key = _api_key()
    if not key or len(key) < 50:
        # courts and cfpb don't need Claude; property/business do
        if body.source in ("property", "business"):
            raise HTTPException(status_code=503, detail="AI service not configured.")

    # Resolve client_id
    client_id: Optional[int] = None
    case_id: Optional[int] = None
    service_case_id: Optional[int] = None

    if body.case_id:
        case = db.query(AegisCase).filter(AegisCase.id == body.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        client_id = case.client_id
        case_id = body.case_id

    if body.service_case_id:
        scase = db.query(ServiceCase).filter(ServiceCase.id == body.service_case_id).first()
        if not scase:
            raise HTTPException(status_code=404, detail="Service case not found")
        client_id = scase.client_id
        service_case_id = body.service_case_id

    try:
        content, source_slug = handler(body.query, body.params, key)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI auth failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Data pull error: {str(exc)[:200]}")

    source_labels = {"courts": "Court Records", "cfpb": "CFPB Complaints",
                     "property": "Property Records", "business": "Business Records"}
    doc_type = source_labels.get(source_slug, "Data Pull")

    doc = ServiceDocument(
        client_id=client_id,
        case_id=case_id,
        service_case_id=service_case_id,
        division_slug="research",
        title=f"{doc_type}: {body.query[:70]}",
        document_type=doc_type,
        content=content,
        status="draft",
        ai_generated=(body.source in ("property", "business")),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"document_id": doc.id, "title": doc.title, "content": content, "source": body.source}


@router.get("/case/{case_id}")
def list_case_pulls(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(AegisCase).filter(AegisCase.id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found")
    docs = (
        db.query(ServiceDocument)
        .filter(
            ServiceDocument.case_id == case_id,
            ServiceDocument.document_type.in_(
                ["Court Records", "CFPB Complaints", "Property Records", "Business Records"]
            ),
        )
        .order_by(ServiceDocument.created_at.desc())
        .all()
    )
    return [{"id": d.id, "title": d.title, "content": d.content,
             "created_at": d.created_at.isoformat() if d.created_at else None}
            for d in docs]
