from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Invoice, Client, Case, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


class InvoiceCreate(BaseModel):
    client_id: int
    case_id: Optional[int] = None
    amount: float
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    amount: Optional[float] = None
    paid: Optional[float] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class PaymentRecord(BaseModel):
    amount: float
    notes: Optional[str] = None


class InvoiceOut(BaseModel):
    id: int
    client_id: int
    case_id: Optional[int]
    amount: float
    paid: float
    status: str
    due_date: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[InvoiceOut])
def list_invoices(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Invoice)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=InvoiceOut, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")

    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.case_id:
        case = db.query(Case).filter(Case.id == payload.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log = AuditLog(
        user_id=current_user.id,
        action="create_invoice",
        resource_type="invoice",
        resource_id=invoice.id,
        details=f"amount=${payload.amount:.2f}",
    )
    db.add(log)
    db.commit()

    background_tasks.add_task(_email_invoice, invoice.id)

    return invoice


def _email_invoice(invoice_id: int):
    from app.services.automation import on_invoice_created
    try:
        on_invoice_created(invoice_id)
    except Exception:
        pass


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(invoice, key, val)

    # Auto-update status
    if invoice.paid >= invoice.amount:
        invoice.status = "paid"

    db.commit()
    db.refresh(invoice)

    log = AuditLog(
        user_id=current_user.id,
        action="update_invoice",
        resource_type="invoice",
        resource_id=invoice_id,
        details=str(list(updates.keys())),
    )
    db.add(log)
    db.commit()

    return invoice


@router.post("/{invoice_id}/payment", response_model=InvoiceOut)
def record_payment(
    invoice_id: int,
    payload: PaymentRecord,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Payment amount must be positive")

    invoice.paid = (invoice.paid or 0) + payload.amount
    if invoice.paid >= invoice.amount:
        invoice.status = "paid"

    if payload.notes:
        existing = invoice.notes or ""
        invoice.notes = f"{existing}\n[Payment ${payload.amount:.2f} on {datetime.utcnow().date()}] {payload.notes}".strip()

    db.commit()
    db.refresh(invoice)

    log = AuditLog(
        user_id=current_user.id,
        action="record_payment",
        resource_type="invoice",
        resource_id=invoice_id,
        details=f"amount=${payload.amount:.2f}",
    )
    db.add(log)
    db.commit()

    return invoice


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.services.pdf_generator import generate_pdf
    from fastapi.responses import FileResponse

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = db.query(Client).filter(Client.id == invoice.client_id).first()

    pdf_path = generate_pdf("invoice", {
        "client_id": client.id if client else invoice.client_id,
        "first_name": client.first_name if client else "",
        "last_name": client.last_name if client else "",
        "address": client.address if client else "",
        "city": client.city if client else "",
        "state": client.state if client else "SC",
        "zip_code": client.zip_code if client else "",
        "invoice_id": invoice.id,
        "invoice_number": f"INV-{invoice.id:04d}",
        "amount": invoice.amount,
        "paid": invoice.paid,
        "due_date": invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "Upon Receipt",
        "notes": invoice.notes,
    })

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"invoice_{invoice.id}.pdf",
    )
