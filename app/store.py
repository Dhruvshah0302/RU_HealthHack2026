"""Ticket store. In memory for now; the methods are the ones a DynamoDB table would need."""
from __future__ import annotations

import itertools
import time

from .models import NURSE, Ticket


class TicketStore:
    def __init__(self):
        self._tickets: dict[str, Ticket] = {}
        self._ids = itertools.count(1)
        self.requests_total = 0
        self.requests_without_nurse = 0

    def add(self, room: str, original_text: str, planned, patient_name: str | None = None,
            team: str | None = None, classified_by: str | None = None) -> Ticket:
        ticket = Ticket(
            id=f"T{next(self._ids):04d}", room=room, department=planned.department,
            priority=planned.priority, summary=planned.summary, original_text=original_text,
            created_at=time.time(), status=planned.status, reasons=list(planned.reasons),
            notes=list(planned.notes), patient_name=patient_name, team=team, classified_by=classified_by,
        )
        self._tickets[ticket.id] = ticket
        return ticket

    def record_request(self, departments: list[str]) -> None:
        self.requests_total += 1
        if NURSE not in departments:
            self.requests_without_nurse += 1

    def set_status(self, ticket_id: str, status: str) -> Ticket | None:
        ticket = self._tickets.get(ticket_id)
        if ticket is not None:
            ticket.status = status
        return ticket

    def open_tickets(self) -> list[Ticket]:
        return [t for t in self._tickets.values() if t.status != "done"]

    def stats(self) -> dict:
        # by_team: every ticket each team has received, open or done (for the staff dashboard)
        by_team: dict[str, dict[str, int]] = {}
        for t in self._tickets.values():
            counts = by_team.setdefault(t.team or t.department, {"total": 0, "done": 0})
            counts["total"] += 1
            if t.status == "done":
                counts["done"] += 1
        return {"requests_total": self.requests_total,
                "requests_without_nurse": self.requests_without_nurse,
                "by_team": by_team}
