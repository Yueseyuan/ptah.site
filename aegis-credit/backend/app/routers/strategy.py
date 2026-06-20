import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import StrategyItem, Finding, AegisCase
from app.services.ai_service import generate_strategy

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class StrategyCreate(BaseModel):
    case_id: int
    priority: int = 2
    strategy_type: str
    title: str
    description: Optional[str] = None
    action_items: Optional[list] = None
    estimated_timeline: Optional[str] = None


class StrategyUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None


def _out(s: StrategyItem) -> dict:
    return {
        "id": s.id,
        "case_id": s.case_id,
        "priority": s.priority,
        "strategy_type": s.strategy_type,
        "title": s.title,
        "description": s.description,
        "action_items": json.loads(s.action_items) if s.action_items else [],
        "estimated_timeline": s.estimated_timeline,
        "status": s.status,
        "ai_generated": s.ai_generated,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/case/{case_id}")
def list_strategy(case_id: int, db: Session = Depends(get_db)):
    return [_out(s) for s in db.query(StrategyItem).filter(StrategyItem.case_id == case_id).order_by(StrategyItem.priority).all()]


@router.post("/case/{case_id}/generate")
def generate_case_strategy(case_id: int, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    if not findings:
        raise HTTPException(400, "No findings available. Generate findings first.")

    findings_data = [{
        "finding_type": f.finding_type,
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "fcra_section": f.fcra_section,
    } for f in findings]

    try:
        strategy_data = generate_strategy(findings_data, case.goal or "")
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    db.query(StrategyItem).filter(StrategyItem.case_id == case_id, StrategyItem.ai_generated == True).delete()

    new_items = []
    for sd in strategy_data:
        item = StrategyItem(
            case_id=case_id,
            priority=sd.get("priority", 2),
            strategy_type=sd.get("strategy_type", "dispute"),
            title=sd.get("title", "Strategy"),
            description=sd.get("description", ""),
            action_items=json.dumps(sd.get("action_items", [])),
            estimated_timeline=sd.get("estimated_timeline", ""),
            ai_generated=True,
        )
        db.add(item)
        new_items.append(item)
    db.commit()
    for i in new_items:
        db.refresh(i)
    return {"items_generated": len(new_items), "items": [_out(i) for i in new_items]}


@router.post("/", status_code=201)
def create_strategy(data: StrategyCreate, db: Session = Depends(get_db)):
    item = StrategyItem(
        case_id=data.case_id,
        priority=data.priority,
        strategy_type=data.strategy_type,
        title=data.title,
        description=data.description,
        action_items=json.dumps(data.action_items or []),
        estimated_timeline=data.estimated_timeline,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _out(item)


@router.patch("/{item_id}")
def update_strategy(item_id: int, data: StrategyUpdate, db: Session = Depends(get_db)):
    s = db.query(StrategyItem).filter(StrategyItem.id == item_id).first()
    if not s:
        raise HTTPException(404, "Strategy item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return _out(s)
