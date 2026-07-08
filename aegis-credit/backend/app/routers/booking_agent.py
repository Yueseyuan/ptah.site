"""AI booking agent — conversational appointment scheduling via Claude tool use."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Appointment, AegisClient, User

router = APIRouter(prefix="/api/booking", tags=["booking"])

ET = ZoneInfo("America/New_York")
_BSTART = 9   # 9 AM Eastern
_BEND   = 17  # 5 PM Eastern (last 60-min slot starts at 4 PM)

DIVISIONS = {
    "credit":     "Credit Repair",
    "criminal":   "Record Relief",
    "document":   "Document Preparation",
    "notary":     "Mobile Notary",
    "judgment":   "Judgment Relief",
    "consulting": "Consulting",
    "overages":   "Tax / Overages Recovery",
}

_SYSTEM = """You are the Aegis scheduling assistant for Cruel & Associates — professional, warm, and efficient. Your only job: book appointments in 2–3 messages. No email back-and-forth.

Services available:
- Credit Repair (credit): credit score restoration, dispute strategy
- Record Relief (criminal): criminal records, background check issues
- Document Preparation (document): legal and financial documents
- Mobile Notary (notary): notary signing services
- Judgment Relief (judgment): judgment removal and relief
- Consulting (consulting): general financial consulting
- Tax / Overages Recovery (overages): tax overages and asset recovery

Booking flow (strictly follow this):
1. If service unclear: ask ONE question — "What brings you in today?"
2. Ask ONE question about timing: "Any preference — this week, next week? Mornings or afternoons?"
3. Call get_available_slots for that window immediately
4. Show exactly 3 options: "Tuesday July 15 at 10 AM · Wednesday July 16 at 2 PM · Thursday July 17 at 11 AM — which works?"
5. Client picks → call book_appointment → reply with confirmation summary

Hard rules:
- Never invent availability — always call get_available_slots first
- If no slots in their window, silently widen the search and try again
- All appointments: 60 minutes, phone or video call (unless client says otherwise)
- Business hours: Monday–Friday, 9 AM – 5 PM Eastern
- Keep messages short. One question at a time."""


class ChatMsg(BaseModel):
    role: str
    content: str


class BookingChatRequest(BaseModel):
    messages: List[ChatMsg]
    client_id: Optional[int] = None


def _available_slots(date_from: str, date_to: str, division: Optional[str], db: Session) -> List[str]:
    try:
        d_from = datetime.fromisoformat(date_from).replace(tzinfo=ET)
        d_to   = datetime.fromisoformat(date_to).replace(tzinfo=ET)
    except (ValueError, TypeError):
        return []

    now    = datetime.now(ET)
    d_from = max(d_from, now + timedelta(hours=1))
    d_to   = min(d_to,   now + timedelta(days=30))

    # Fetch booked slots in window (stored as UTC naive)
    start_utc = d_from.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end_utc   = d_to.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    q = db.query(Appointment.scheduled_at, Appointment.duration_minutes).filter(
        Appointment.status.in_(["scheduled", "confirmed"]),
        Appointment.scheduled_at >= start_utc,
        Appointment.scheduled_at <= end_utc,
    )
    booked = [(a.scheduled_at, a.duration_minutes or 60) for a in q.all()]

    slots: List[str] = []
    cursor = d_from.replace(hour=_BSTART, minute=0, second=0, microsecond=0)

    while cursor <= d_to and len(slots) < 20:
        if cursor.weekday() < 5 and cursor > now:
            slot_end = cursor + timedelta(hours=1)
            if _BSTART <= cursor.hour and slot_end.hour <= _BEND:
                utc_naive = cursor.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                conflict = any(
                    abs((b[0] - utc_naive).total_seconds()) < b[1] * 60
                    for b in booked
                )
                if not conflict:
                    slots.append(cursor.strftime("%Y-%m-%dT%H:%M%z"))

        cursor += timedelta(hours=1)
        if cursor.hour >= _BEND:
            cursor = (cursor + timedelta(days=1)).replace(
                hour=_BSTART, minute=0, second=0, microsecond=0
            )

    return slots


def _book(scheduled_at_str: str, division: str, appt_type: str, notes: str, client_id: int, db: Session) -> dict:
    try:
        dt = datetime.fromisoformat(scheduled_at_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET)
        dt_utc = dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        dt_et  = dt.astimezone(ET)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, f"Invalid scheduled_at: {e}")

    appt = Appointment(
        client_id=client_id,
        division_slug=division,
        appointment_type=appt_type or "consultation",
        scheduled_at=dt_utc,
        duration_minutes=60,
        status="scheduled",
        notes=notes or "",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    day    = dt_et.day
    hour   = dt_et.hour % 12 or 12
    am_pm  = "AM" if dt_et.hour < 12 else "PM"
    minute = dt_et.strftime("%M")
    label  = dt_et.strftime(f"%A, %B {day} at {hour}:{minute} {am_pm} Eastern")

    return {
        "appointment_id": appt.id,
        "confirmed_time": label,
        "division": DIVISIONS.get(division, division),
        "status": "scheduled",
    }


@router.post("/chat")
def booking_chat(
    data: BookingChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(503, "AI booking is not configured. Please call or email to schedule.")

    # Resolve client_id
    if current_user.role == "client":
        portal_client = db.query(AegisClient).filter(
            AegisClient.portal_user_id == current_user.id
        ).first()
        if not portal_client:
            raise HTTPException(404, "No client profile linked to your account. Contact your case manager.")
        client_id = portal_client.id
    else:
        if not data.client_id:
            raise HTTPException(400, "client_id is required for staff booking")
        client_id = data.client_id

    import anthropic as _anthropic

    ai = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    tools = [
        {
            "name": "get_available_slots",
            "description": "Get open appointment slots for a date range. Always call this before presenting time options.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Start date ISO (e.g. 2025-07-14)"},
                    "date_to":   {"type": "string", "description": "End date ISO (e.g. 2025-07-20)"},
                    "division":  {"type": "string", "description": "Optional division slug to filter"},
                },
                "required": ["date_from", "date_to"],
            },
        },
        {
            "name": "book_appointment",
            "description": "Create the appointment once the client confirms a specific slot.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "scheduled_at":     {"type": "string", "description": "ISO datetime with offset (e.g. 2025-07-15T10:00:00-04:00)"},
                    "division":         {"type": "string", "description": "Division slug"},
                    "appointment_type": {"type": "string", "description": "consultation | signing | document_review | intake"},
                    "notes":            {"type": "string", "description": "Any notes from the client"},
                },
                "required": ["scheduled_at", "division", "appointment_type"],
            },
        },
    ]

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    booking_result = None

    for _ in range(6):  # max agentic turns
        resp = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            tools=tools,
            messages=messages,
        )

        if resp.stop_reason == "end_turn":
            text = next((b.text for b in resp.content if hasattr(b, "text")), "")
            return {"message": text, "booking": booking_result}

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []

            for block in resp.content:
                if block.type != "tool_use":
                    continue
                inp = block.input

                if block.name == "get_available_slots":
                    slots = _available_slots(
                        inp.get("date_from", ""),
                        inp.get("date_to", ""),
                        inp.get("division"),
                        db,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"slots": slots, "count": len(slots)}),
                    })

                elif block.name == "book_appointment":
                    try:
                        booking_result = _book(
                            inp.get("scheduled_at", ""),
                            inp.get("division", "consulting"),
                            inp.get("appointment_type", "consultation"),
                            inp.get("notes", ""),
                            client_id,
                            db,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(booking_result),
                        })
                    except HTTPException as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": exc.detail}),
                            "is_error": True,
                        })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {"message": "Something went wrong. Please try again.", "booking": booking_result}
