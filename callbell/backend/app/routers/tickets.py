"""Department dashboard endpoints (poll GET every ~2s from React)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from ..db import Ticket, get_db, utcnow
from ..schemas import Department, TicketOut, TicketStatus, TicketStatusUpdate

router = APIRouter(prefix="/api/tickets", tags=["departments"])

_PRIORITY_ORDER = case({"urgent": 0, "soon": 1, "routine": 2}, value=Ticket.priority)


@router.get("", response_model=list[TicketOut])
def list_tickets(department: Optional[Department] = None, status: Optional[str] = "open",
                 db: Session = Depends(get_db)):
    q = db.query(Ticket)
    if department:
        q = q.filter(Ticket.department == department.value)
    if status == "open":
        q = q.filter(Ticket.status != TicketStatus.done.value)
    elif status:
        q = q.filter(Ticket.status == status)
    return q.order_by(_PRIORITY_ORDER, Ticket.created_at).all()


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_status(ticket_id: int, body: TicketStatusUpdate, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404)
    t.status = body.status.value
    if body.status == TicketStatus.accepted and not t.accepted_at:
        t.accepted_at = utcnow()
    if body.status == TicketStatus.done:
        t.completed_at = utcnow()
    db.commit()
    db.refresh(t)
    return t


@router.get("/metrics/summary")
def metrics(db: Session = Depends(get_db)):
    """For the impact slide: share of requests kept off nursing."""
    total = db.query(Ticket).count()
    nursing = db.query(Ticket).filter(Ticket.department == "nursing").count()
    by_dept = {d.value: db.query(Ticket).filter(Ticket.department == d.value).count() for d in Department}
    return {"total": total, "by_department": by_dept,
            "diverted_from_nursing_pct": round(100 * (total - nursing) / total, 1) if total else 0}
