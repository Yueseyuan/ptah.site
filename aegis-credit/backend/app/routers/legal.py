"""Legal Knowledge Engine router."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import FederalLaw, AgencyGuidance, StateLaw, CaseLaw

router = APIRouter(prefix="/api/legal", tags=["legal"])


# ─── Output helpers ───────────────────────────────────────────────────────────

def _out_federal(law: FederalLaw) -> dict:
    return {
        "id": law.id,
        "short_name": law.short_name,
        "title": law.title,
        "citation": law.citation,
        "section": law.section,
        "summary": law.summary,
        "effective_date": law.effective_date,
        "category": law.category,
        "source_url": law.source_url,
        "effective_as_of": getattr(law, "effective_as_of", None),
        "superseded_by_id": getattr(law, "superseded_by_id", None),
        "version_notes": getattr(law, "version_notes", None),
        "created_at": law.created_at.isoformat() if law.created_at else None,
    }


def _out_guidance(g: AgencyGuidance) -> dict:
    return {
        "id": g.id,
        "agency": g.agency,
        "document_name": g.document_name,
        "publication_date": g.publication_date,
        "topic": g.topic,
        "summary": g.summary,
        "source_url": g.source_url,
        "effective_as_of": getattr(g, "effective_as_of", None),
        "superseded": getattr(g, "superseded", False),
        "version_notes": getattr(g, "version_notes", None),
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


def _out_state(s: StateLaw) -> dict:
    return {
        "id": s.id,
        "state": s.state,
        "statute": s.statute,
        "citation": s.citation,
        "topic": s.topic,
        "effective_date": s.effective_date,
        "summary": s.summary,
        "source_url": s.source_url,
        "effective_as_of": getattr(s, "effective_as_of", None),
        "superseded": getattr(s, "superseded", False),
        "version_notes": getattr(s, "version_notes", None),
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _out_case(c: CaseLaw) -> dict:
    return {
        "id": c.id,
        "case_name": c.case_name,
        "citation": c.citation,
        "court": c.court,
        "jurisdiction": c.jurisdiction,
        "year": c.year,
        "topic": c.topic,
        "holding_summary": c.holding_summary,
        "legal_principle": c.legal_principle,
        "relevance_tags": c.relevance_tags,
        "source_url": c.source_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─── Federal Laws ─────────────────────────────────────────────────────────────

class FederalLawCreate(BaseModel):
    short_name: str
    title: str
    citation: str
    section: Optional[str] = None
    summary: Optional[str] = None
    effective_date: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    effective_as_of: Optional[str] = None
    version_notes: Optional[str] = None


@router.get("/federal")
def list_federal_laws(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    as_of: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(FederalLaw)
    if category:
        q = q.filter(FederalLaw.category == category)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                FederalLaw.title.ilike(term),
                FederalLaw.summary.ilike(term),
                FederalLaw.citation.ilike(term),
                FederalLaw.section.ilike(term),
                FederalLaw.short_name.ilike(term),
            )
        )
    if as_of:
        q = q.filter(
            or_(FederalLaw.effective_as_of == None, FederalLaw.effective_as_of <= as_of)
        ).filter(FederalLaw.superseded_by_id == None)
    return [_out_federal(law) for law in q.all()]


@router.post("/federal", status_code=201)
def create_federal_law(data: FederalLawCreate, db: Session = Depends(get_db)):
    law = FederalLaw(**data.model_dump())
    db.add(law)
    db.commit()
    db.refresh(law)
    return _out_federal(law)


@router.get("/federal/{law_id}")
def get_federal_law(law_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    law = db.query(FederalLaw).filter(FederalLaw.id == law_id).first()
    if not law:
        raise HTTPException(404, "Law not found")
    return _out_federal(law)


# ─── Agency Guidance ──────────────────────────────────────────────────────────

@router.get("/guidance")
def list_agency_guidance(
    agency: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    as_of: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(AgencyGuidance)
    if agency:
        q = q.filter(AgencyGuidance.agency == agency)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                AgencyGuidance.document_name.ilike(term),
                AgencyGuidance.summary.ilike(term),
                AgencyGuidance.topic.ilike(term),
                AgencyGuidance.agency.ilike(term),
            )
        )
    if as_of:
        q = q.filter(
            or_(AgencyGuidance.effective_as_of == None, AgencyGuidance.effective_as_of <= as_of)
        ).filter(AgencyGuidance.superseded == False)
    return [_out_guidance(g) for g in q.all()]


# ─── State Laws ───────────────────────────────────────────────────────────────

class StateLawCreate(BaseModel):
    state: str
    statute: str
    citation: str
    topic: str
    effective_date: Optional[str] = None
    summary: Optional[str] = None
    source_url: Optional[str] = None
    effective_as_of: Optional[str] = None
    version_notes: Optional[str] = None


@router.get("/state")
def list_state_laws(
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StateLaw)
    if state:
        q = q.filter(StateLaw.state == state)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                StateLaw.statute.ilike(term),
                StateLaw.summary.ilike(term),
                StateLaw.citation.ilike(term),
                StateLaw.topic.ilike(term),
                StateLaw.state.ilike(term),
            )
        )
    return [_out_state(s) for s in q.all()]


@router.post("/state", status_code=201)
def create_state_law(data: StateLawCreate, db: Session = Depends(get_db)):
    law = StateLaw(**data.model_dump())
    db.add(law)
    db.commit()
    db.refresh(law)
    return _out_state(law)


# ─── Case Law ─────────────────────────────────────────────────────────────────

class CaseLawCreate(BaseModel):
    case_name: str
    citation: str
    court: str
    jurisdiction: str
    year: int
    topic: str
    holding_summary: Optional[str] = None
    legal_principle: Optional[str] = None
    relevance_tags: Optional[str] = None
    source_url: Optional[str] = None


@router.get("/cases")
def list_case_law(
    topic: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(CaseLaw)
    if topic:
        q = q.filter(CaseLaw.topic.ilike(f"%{topic}%"))
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                CaseLaw.case_name.ilike(term),
                CaseLaw.holding_summary.ilike(term),
                CaseLaw.citation.ilike(term),
                CaseLaw.topic.ilike(term),
                CaseLaw.legal_principle.ilike(term),
            )
        )
    return [_out_case(c) for c in q.all()]


@router.post("/cases", status_code=201)
def create_case_law(data: CaseLawCreate, db: Session = Depends(get_db)):
    case = CaseLaw(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _out_case(case)


# ─── Global Search ────────────────────────────────────────────────────────────

@router.get("/search")
def search_legal(q: str = Query(...), db: Session = Depends(get_db)):
    term = f"%{q}%"

    federal = db.query(FederalLaw).filter(
        or_(
            FederalLaw.title.ilike(term),
            FederalLaw.summary.ilike(term),
            FederalLaw.citation.ilike(term),
            FederalLaw.section.ilike(term),
            FederalLaw.short_name.ilike(term),
        )
    ).all()

    guidance = db.query(AgencyGuidance).filter(
        or_(
            AgencyGuidance.document_name.ilike(term),
            AgencyGuidance.summary.ilike(term),
            AgencyGuidance.topic.ilike(term),
            AgencyGuidance.agency.ilike(term),
        )
    ).all()

    state = db.query(StateLaw).filter(
        or_(
            StateLaw.statute.ilike(term),
            StateLaw.summary.ilike(term),
            StateLaw.citation.ilike(term),
            StateLaw.topic.ilike(term),
            StateLaw.state.ilike(term),
        )
    ).all()

    cases = db.query(CaseLaw).filter(
        or_(
            CaseLaw.case_name.ilike(term),
            CaseLaw.holding_summary.ilike(term),
            CaseLaw.citation.ilike(term),
            CaseLaw.topic.ilike(term),
            CaseLaw.legal_principle.ilike(term),
        )
    ).all()

    return {
        "query": q,
        "federal_laws": [_out_federal(law) for law in federal],
        "agency_guidance": [_out_guidance(g) for g in guidance],
        "state_laws": [_out_state(s) for s in state],
        "case_law": [_out_case(c) for c in cases],
        "total": len(federal) + len(guidance) + len(state) + len(cases),
    }
