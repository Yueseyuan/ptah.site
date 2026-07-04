"""Multi-step AI research agent — web search + URL fetch loop powered by Claude."""

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

router = APIRouter(prefix="/api/research", tags=["research"])

_MODEL = "claude-sonnet-5"
_MAX_ROUNDS = 6
_JINA_SEARCH = "https://s.jina.ai/"
_JINA_READ = "https://r.jina.ai/"
_MAX_CHARS = 4000  # per tool result, to cap token usage


class ResearchRequest(BaseModel):
    query: str
    context: Optional[str] = None


TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the web. Use for court records, FCRA/FDCPA precedents, creditor histories, "
            "property records, business filings, county records, or any public legal/financial data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch the full readable text of a specific URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]

_SYSTEM = (
    "You are a precision research specialist for a legal services and credit investigation firm. "
    "Research the query thoroughly using multiple web searches and page fetches. "
    "Focus on: court filings, credit bureau data, FCRA/FDCPA law and precedents, creditor histories, "
    "property and tax records, business registrations, and any relevant public records. "
    "After gathering information synthesize a structured report exactly as:\n\n"
    "## SUMMARY\n(2-3 sentence overview)\n\n"
    "## KEY FINDINGS\n(bulleted, specific, cite sources inline)\n\n"
    "## SOURCES\n(numbered list of URLs used)\n\n"
    "## RECOMMENDED ACTIONS\n(concrete next steps for the case team)\n\n"
    "Be factual. Frame as operational research for a non-attorney firm — no legal advice."
)


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/plain",
            "X-Return-Format": "text",
            "User-Agent": "AegisResearch/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")[:_MAX_CHARS]
    except Exception as exc:
        return f"[Fetch error: {exc}]"


def _api_key() -> str:
    return settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")


def _run_agent(key: str, query: str, context: Optional[str]) -> tuple[str, list[str]]:
    """Execute the tool-use research loop. Returns (report_text, source_urls)."""
    client = anthropic.Anthropic(api_key=key)
    user_msg = f"Context: {context}\n\nResearch Query: {query}" if context else query
    messages: list = [{"role": "user", "content": user_msg}]
    sources: list[str] = []
    report = "Research completed but no report was generated."

    for _ in range(_MAX_ROUNDS):
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=2500,
            system=_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            for block in resp.content:
                if hasattr(block, "text") and block.text:
                    report = block.text
            break

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "search_web":
                q = urllib.parse.quote(block.input.get("query", ""))
                result = _fetch(f"{_JINA_SEARCH}{q}")
            elif block.name == "fetch_page":
                url = block.input.get("url", "")
                sources.append(url)
                result = _fetch(f"{_JINA_READ}{url}")
            else:
                result = "Unknown tool."
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    return report, list(dict.fromkeys(sources))  # deduplicated, order-preserved


def _check_key(key: str) -> None:
    if not key or len(key) < 50:
        raise HTTPException(status_code=503, detail="AI service not configured. Set ANTHROPIC_API_KEY.")


def _save_doc(db: Session, *, client_id: int, title: str, content: str,
              case_id: Optional[int] = None, service_case_id: Optional[int] = None,
              division_slug: str = "research") -> ServiceDocument:
    doc = ServiceDocument(
        client_id=client_id,
        case_id=case_id,
        service_case_id=service_case_id,
        division_slug=division_slug,
        title=title,
        document_type="Research Report",
        content=content,
        status="draft",
        ai_generated=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ── Credit investigation case research ─────────────────────────────────────────

@router.post("/case/{case_id}", status_code=201)
def research_credit_case(
    case_id: int,
    body: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    key = _api_key()
    _check_key(key)
    try:
        content, sources = _run_agent(key, body.query, body.context)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI auth failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Research agent error: {str(exc)[:200]}")

    doc = _save_doc(db, client_id=case.client_id, case_id=case_id,
                    title=f"Research: {body.query[:80]}", content=content)
    return {"document_id": doc.id, "title": doc.title, "content": content,
            "sources": sources, "ai_generated": True}


@router.get("/case/{case_id}")
def list_credit_case_research(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(AegisCase).filter(AegisCase.id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found")
    docs = (
        db.query(ServiceDocument)
        .filter(ServiceDocument.case_id == case_id,
                ServiceDocument.document_type == "Research Report")
        .order_by(ServiceDocument.created_at.desc())
        .all()
    )
    return [{"id": d.id, "title": d.title, "content": d.content,
             "created_at": d.created_at.isoformat() if d.created_at else None}
            for d in docs]


# ── Service case research ───────────────────────────────────────────────────────

@router.post("/service-case/{service_case_id}", status_code=201)
def research_service_case(
    service_case_id: int,
    body: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    key = _api_key()
    _check_key(key)
    try:
        content, sources = _run_agent(key, body.query, body.context)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"AI auth failed: {str(exc)[:150]}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Research agent error: {str(exc)[:200]}")

    doc = _save_doc(db, client_id=case.client_id, service_case_id=service_case_id,
                    division_slug=case.division_slug or "research",
                    title=f"Research: {body.query[:80]}", content=content)
    return {"document_id": doc.id, "title": doc.title, "content": content,
            "sources": sources, "ai_generated": True}


@router.get("/service-case/{service_case_id}")
def list_service_case_research(
    service_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(ServiceCase).filter(ServiceCase.id == service_case_id).first():
        raise HTTPException(status_code=404, detail="Case not found")
    docs = (
        db.query(ServiceDocument)
        .filter(ServiceDocument.service_case_id == service_case_id,
                ServiceDocument.document_type == "Research Report")
        .order_by(ServiceDocument.created_at.desc())
        .all()
    )
    return [{"id": d.id, "title": d.title, "content": d.content,
             "created_at": d.created_at.isoformat() if d.created_at else None}
            for d in docs]
