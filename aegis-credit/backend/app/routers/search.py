"""Global search across clients, cases, and tradelines."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import AegisClient, AegisCase, Tradeline
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/")
def global_search(q: str = "", db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Search across clients, cases, and tradeline creditors."""
    if not q or len(q) < 2:
        return {"clients": [], "cases": [], "tradelines": []}

    ql = f"%{q.lower()}%"

    clients = db.query(AegisClient).filter(
        func.lower(AegisClient.first_name + ' ' + AegisClient.last_name).like(ql) |
        func.lower(AegisClient.email).like(ql)
    ).limit(5).all()

    cases = db.query(AegisCase).filter(
        func.lower(AegisCase.case_number).like(ql) |
        func.lower(func.coalesce(AegisCase.goal, '')).like(ql) |
        func.lower(func.coalesce(AegisCase.notes, '')).like(ql)
    ).limit(5).all()

    tradelines = db.query(Tradeline).filter(
        func.lower(Tradeline.creditor_name).like(ql)
    ).limit(10).all()

    return {
        "clients": [
            {"id": c.id, "name": f"{c.first_name} {c.last_name}", "email": c.email, "type": "client"}
            for c in clients
        ],
        "cases": [
            {"id": c.id, "case_number": c.case_number, "status": c.status, "client_id": c.client_id, "type": "case"}
            for c in cases
        ],
        "tradelines": [
            {"id": t.id, "creditor_name": t.creditor_name, "bureau": t.bureau, "case_id": t.case_id, "type": "tradeline"}
            for t in tradelines
        ],
    }
