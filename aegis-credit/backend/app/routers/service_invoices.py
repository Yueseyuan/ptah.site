import json
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AegisClient, ServiceCase, ServiceInvoice, User

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

_VALID_STATUSES = {"draft", "sent", "paid", "void"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    total: float


class InvoiceCreate(BaseModel):
    client_id: int
    service_case_id: Optional[int] = None
    division_slug: str
    line_items: Optional[List[LineItem]] = None   # parsed list; serialised to JSON on save
    subtotal: Optional[float] = 0.0
    tax_rate: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    total: Optional[float] = 0.0
    status: Optional[str] = "draft"
    due_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    service_case_id: Optional[int] = None
    division_slug: Optional[str] = None
    line_items: Optional[List[LineItem]] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class InvoiceOut(BaseModel):
    id: int
    client_id: int
    service_case_id: Optional[int]
    invoice_number: Optional[str]
    division_slug: Optional[str]
    line_items: Optional[List[Any]]    # parsed from JSON string
    subtotal: Optional[float]
    tax_rate: Optional[float]
    tax_amount: Optional[float]
    total: Optional[float]
    status: Optional[str]
    due_date: Optional[str]
    paid_at: Optional[str]
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_line_items(raw: Optional[str]) -> Optional[list]:
    """Safely parse a JSON string of line items into a Python list."""
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _out(inv: ServiceInvoice) -> dict:
    return {
        "id": inv.id,
        "client_id": inv.client_id,
        "service_case_id": inv.service_case_id,
        "invoice_number": inv.invoice_number,
        "division_slug": inv.division_slug,
        "line_items": _parse_line_items(inv.line_items),
        "subtotal": inv.subtotal,
        "tax_rate": inv.tax_rate,
        "tax_amount": inv.tax_amount,
        "total": inv.total,
        "status": inv.status,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "payment_method": inv.payment_method,
        "notes": inv.notes,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


def _gen_invoice_number(year: int, record_id: int) -> str:
    return f"INV-{year}-{record_id:05d}"


def _serialize_line_items(items: Optional[List[LineItem]]) -> Optional[str]:
    if items is None:
        return None
    return json.dumps([item.model_dump() for item in items])


# ---------------------------------------------------------------------------
# Routes — /mark-paid sub-routes defined before /{id} to avoid conflicts
# ---------------------------------------------------------------------------

@router.get("/")
def list_invoices(
    client_id: Optional[int] = None,
    division: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List invoices with optional filters: client_id, division slug, status."""
    q = db.query(ServiceInvoice)
    if client_id is not None:
        q = q.filter(ServiceInvoice.client_id == client_id)
    if division is not None:
        q = q.filter(ServiceInvoice.division_slug == division)
    if status is not None:
        q = q.filter(ServiceInvoice.status == status)
    return [_out(inv) for inv in q.order_by(ServiceInvoice.id.desc()).all()]


@router.post("/", status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a new service invoice. invoice_number is auto-generated as INV-{year}-{id:05d}."""
    client = db.query(AegisClient).filter(AegisClient.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    if data.status and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    payload = data.model_dump(exclude={"line_items"})
    payload["line_items"] = _serialize_line_items(data.line_items)
    payload["invoice_number"] = "INV-PENDING"

    inv = ServiceInvoice(**payload)
    db.add(inv)
    db.flush()   # populates inv.id without committing

    year = (inv.created_at or datetime.utcnow()).year
    inv.invoice_number = _gen_invoice_number(year, inv.id)
    db.commit()
    db.refresh(inv)
    return _out(inv)


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Retrieve a single invoice by ID."""
    inv = db.query(ServiceInvoice).filter(ServiceInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _out(inv)


@router.put("/{invoice_id}/mark-paid")
def mark_invoice_paid(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Mark an invoice as paid and record the payment timestamp."""
    inv = db.query(ServiceInvoice).filter(ServiceInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status == "void":
        raise HTTPException(status_code=422, detail="Cannot mark a voided invoice as paid.")
    inv.status = "paid"
    inv.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return _out(inv)


@router.put("/{invoice_id}")
def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update an invoice's fields."""
    inv = db.query(ServiceInvoice).filter(ServiceInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if data.status is not None and data.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    if data.service_case_id is not None:
        sc = db.query(ServiceCase).filter(ServiceCase.id == data.service_case_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Service case not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"line_items"})
    if "line_items" in data.model_fields_set:
        update_data["line_items"] = _serialize_line_items(data.line_items)

    for field, value in update_data.items():
        setattr(inv, field, value)

    db.commit()
    db.refresh(inv)
    return _out(inv)


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete an invoice by ID."""
    inv = db.query(ServiceInvoice).filter(ServiceInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(inv)
    db.commit()
