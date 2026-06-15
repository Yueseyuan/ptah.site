import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import RecoveryCase, RecoveryAsset
from app.auth import get_current_user

router = APIRouter(prefix="/api/recovery", tags=["Asset Recovery"])

YEAR = datetime.utcnow().year
DEFAULT_STATES = ["SC", "NC", "GA", "FL", "TN", "VA", "TX", "NY"]


def _generate_case_number(db: Session) -> str:
    count = db.query(RecoveryCase).count()
    return f"RC-{YEAR}-{count + 1:04d}"


class RecoveryCaseCreate(BaseModel):
    client_id: int
    case_type: str
    subject_name: str
    subject_ssn_last4: str = ""
    subject_dob: str = ""
    claimant_relationship: str
    states_searched: List[str] = DEFAULT_STATES
    notes: Optional[str] = ""


class RecoveryCaseStatusUpdate(BaseModel):
    status: str


class RecoveryAssetCreate(BaseModel):
    source_state: str
    source_agency: str
    asset_type: str
    holder_name: str
    reported_amount: float
    property_id: Optional[str] = ""


class RecoveryFundsUpdate(BaseModel):
    asset_id: int
    recovered_amount: float


@router.get("/cases", summary="List recovery cases")
def list_recovery_cases(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(RecoveryCase)
    if client_id:
        q = q.filter(RecoveryCase.client_id == client_id)
    if status:
        q = q.filter(RecoveryCase.status == status)
    return q.order_by(RecoveryCase.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/cases", status_code=201, summary="Create recovery case")
def create_recovery_case(
    payload: RecoveryCaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case_number = _generate_case_number(db)
    case = RecoveryCase(
        client_id=payload.client_id,
        case_number=case_number,
        case_type=payload.case_type,
        subject_name=payload.subject_name,
        subject_ssn_last4=payload.subject_ssn_last4,
        subject_dob=payload.subject_dob,
        claimant_relationship=payload.claimant_relationship,
        states_searched=json.dumps(payload.states_searched),
        notes=payload.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}", summary="Get recovery case with assets")
def get_recovery_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return {
        "id": case.id,
        "client_id": case.client_id,
        "case_number": case.case_number,
        "case_type": case.case_type,
        "status": case.status,
        "subject_name": case.subject_name,
        "subject_ssn_last4": case.subject_ssn_last4,
        "subject_dob": case.subject_dob,
        "claimant_relationship": case.claimant_relationship,
        "states_searched": json.loads(case.states_searched or "[]"),
        "total_found": case.total_found,
        "total_recovered": case.total_recovered,
        "contingency_pct": case.contingency_pct,
        "notes": case.notes,
        "created_at": case.created_at,
        "assets": case.assets,
    }


@router.patch("/cases/{case_id}/status", summary="Update recovery case status")
def update_recovery_case_status(
    case_id: int,
    payload: RecoveryCaseStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    case.status = payload.status
    db.commit()
    db.refresh(case)
    return case


@router.post("/cases/{case_id}/assets", status_code=201, summary="Add located asset")
def add_recovery_asset(
    case_id: int,
    payload: RecoveryAssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    asset = RecoveryAsset(
        recovery_case_id=case_id,
        source_state=payload.source_state,
        source_agency=payload.source_agency,
        asset_type=payload.asset_type,
        holder_name=payload.holder_name,
        reported_amount=payload.reported_amount,
        property_id=payload.property_id,
        status="located",
    )
    db.add(asset)
    case.total_found = round((case.total_found or 0.0) + payload.reported_amount, 2)
    if case.status == "intake":
        case.status = "assets_located"
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}/claim", summary="Mark asset as claim filed")
def claim_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.query(RecoveryAsset).filter(RecoveryAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = "claim_filed"
    case = db.query(RecoveryCase).filter(RecoveryCase.id == asset.recovery_case_id).first()
    if case:
        case.status = "claim_filed"
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/cases/{case_id}/recovered", summary="Mark funds recovered")
def mark_recovered(
    case_id: int,
    payload: RecoveryFundsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    asset = db.query(RecoveryAsset).filter(RecoveryAsset.id == payload.asset_id).first()
    if not asset or asset.recovery_case_id != case_id:
        raise HTTPException(status_code=404, detail="Asset not found for this case")

    asset.recovered_amount = payload.recovered_amount
    asset.status = "recovered"

    contingency = round(payload.recovered_amount * (case.contingency_pct / 100.0), 2)
    net_to_client = round(payload.recovered_amount - contingency, 2)

    case.total_recovered = round((case.total_recovered or 0.0) + payload.recovered_amount, 2)
    case.status = "recovered"

    db.commit()
    db.refresh(case)
    return {
        "case": case,
        "asset": asset,
        "recovered_amount": payload.recovered_amount,
        "contingency_fee": contingency,
        "net_to_client": net_to_client,
    }
