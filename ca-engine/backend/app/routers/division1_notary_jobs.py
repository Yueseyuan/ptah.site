import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import NotaryJob
from app.auth import get_current_user

router = APIRouter(prefix="/api/notary-jobs", tags=["Notary Jobs"])

YEAR = datetime.utcnow().year

BASE_FEE_MAP = {
    "loan_signing": 150.0,
    "real_estate": 125.0,
    "general_notary": 75.0,
    "ron": 100.0,
    "apostille": 100.0,
}


def _calculate_fees(job_type: str, travel_miles: float, num_signers: int):
    base_fee = BASE_FEE_MAP.get(job_type, 75.0)
    travel_fee = round(travel_miles * 1.00, 2)
    signer_fee = round(max(0, num_signers - 1) * 10.0, 2)
    ron_fee = 25.0 if job_type == "ron" else 0.0
    total_fee = round(base_fee + travel_fee + signer_fee + ron_fee, 2)
    return base_fee, travel_fee, signer_fee, total_fee


def _generate_job_number(db: Session) -> str:
    count = db.query(NotaryJob).count()
    return f"NJ-{YEAR}-{count + 1:04d}"


class NotaryJobCreate(BaseModel):
    client_id: int
    job_type: str
    service_mode: str = "in_person"
    appointment_at: Optional[datetime] = None
    document_type: Optional[str] = None
    num_signers: int = 1
    travel_miles: float = 0.0
    signing_company: str = ""
    platform_source: str = "manual"
    notes: str = ""


class NotaryJobStatusUpdate(BaseModel):
    status: str


@router.get("/", summary="List notary jobs")
def list_notary_jobs(
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(NotaryJob)
    if status:
        q = q.filter(NotaryJob.status == status)
    if client_id:
        q = q.filter(NotaryJob.client_id == client_id)
    jobs = q.order_by(NotaryJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@router.post("/", status_code=201, summary="Create notary job")
def create_notary_job(
    payload: NotaryJobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    base_fee, travel_fee, signer_fee, total_fee = _calculate_fees(
        payload.job_type, payload.travel_miles, payload.num_signers
    )
    job_number = _generate_job_number(db)
    job = NotaryJob(
        client_id=payload.client_id,
        job_number=job_number,
        job_type=payload.job_type,
        service_mode=payload.service_mode,
        appointment_at=payload.appointment_at,
        document_type=payload.document_type,
        num_signers=payload.num_signers,
        travel_miles=payload.travel_miles,
        signing_company=payload.signing_company,
        base_fee=base_fee,
        travel_fee=travel_fee,
        signer_fee=signer_fee,
        total_fee=total_fee,
        platform_source=payload.platform_source,
        notes=payload.notes,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", summary="Get notary job")
def get_notary_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = db.query(NotaryJob).filter(NotaryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Notary job not found")
    return job


@router.patch("/{job_id}/status", summary="Update notary job status")
def update_notary_job_status(
    job_id: int,
    payload: NotaryJobStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = db.query(NotaryJob).filter(NotaryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Notary job not found")
    job.status = payload.status
    db.commit()
    db.refresh(job)
    return job
