"""Personal Information Audit Engine router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import PersonalInfo, Finding
from app.services.pi_service import run_pi_analysis

router = APIRouter(prefix="/api/personal-info", tags=["personal-info"])


def _out(pi: PersonalInfo) -> dict:
    return {
        "id": pi.id,
        "case_id": pi.case_id,
        "report_id": pi.report_id,
        "bureau": pi.bureau,
        "current_name": pi.current_name,
        "aliases": pi.aliases,
        "current_address": pi.current_address,
        "previous_addresses": pi.previous_addresses,
        "current_employer": pi.current_employer,
        "previous_employers": pi.previous_employers,
        "phone_numbers": pi.phone_numbers,
        "dob": pi.dob,
        "ssn_last4": pi.ssn_last4,
        "created_at": pi.created_at.isoformat() if pi.created_at else None,
    }




class PersonalInfoCreate(BaseModel):
    case_id: int
    report_id: Optional[int] = None
    bureau: str
    current_name: Optional[str] = None
    aliases: Optional[str] = None
    current_address: Optional[str] = None
    previous_addresses: Optional[str] = None
    current_employer: Optional[str] = None
    previous_employers: Optional[str] = None
    phone_numbers: Optional[str] = None
    dob: Optional[str] = None
    ssn_last4: Optional[str] = None


@router.post("/", status_code=201)
def create_personal_info(data: PersonalInfoCreate, db: Session = Depends(get_db)):
    record = PersonalInfo(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _out(record)

@router.get("/case/{case_id}")
def list_personal_info(case_id: int, db: Session = Depends(get_db)):
    records = db.query(PersonalInfo).filter(PersonalInfo.case_id == case_id).all()
    return [_out(r) for r in records]


@router.post("/case/{case_id}/analyze")
def analyze_personal_info(case_id: int, db: Session = Depends(get_db)):
    records = db.query(PersonalInfo).filter(PersonalInfo.case_id == case_id).all()
    if not records:
        return {"records_analyzed": 0, "findings_generated": 0, "findings": []}

    pi_dicts = [_out(r) for r in records]
    findings_data = run_pi_analysis(pi_dicts)

    saved_findings = []
    for f in findings_data:
        finding = Finding(
            case_id=case_id,
            finding_type="pi",
            severity=f.get("severity", "medium"),
            title=f.get("rule_name", f.get("rule_code", "PI Finding")),
            description=f.get("description", ""),
            fcra_section=f.get("fcra_section", ""),
            requires_human_review=True,
            status="open",
        )
        db.add(finding)
        db.flush()
        saved_findings.append({
            "id": finding.id,
            "rule_code": f.get("rule_code", ""),
            "rule_name": f.get("rule_name", ""),
            "severity": f.get("severity", "medium"),
            "description": f.get("description", ""),
            "fcra_section": f.get("fcra_section", ""),
        })

    db.commit()

    return {
        "records_analyzed": len(records),
        "findings_generated": len(saved_findings),
        "findings": saved_findings,
    }


@router.delete("/{record_id}", status_code=204)
def delete_personal_info(record_id: int, db: Session = Depends(get_db)):
    record = db.query(PersonalInfo).filter(PersonalInfo.id == record_id).first()
    if not record:
        raise HTTPException(404, "PersonalInfo record not found")
    db.delete(record)
    db.commit()
