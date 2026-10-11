"""Patient-context rules: adjust the planned tickets using the patient's record.

These run after the router, in plain code. The model never sees the record.

A rule may send a request to the nurse, raise a priority, add a note to a ticket,
or hold a ticket until the patient is back. A rule never removes a nurse ticket
and never lowers a priority.

Each note is added only to the tickets of the team that needs it: Food Services
sees diet and allergies, every team entering the room sees isolation, and the
nurse sees fall risk. Nothing else from the record reaches a ticket.

These rules are our proposal. A hospital would set its own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ehr import PatientContext
from .models import FOOD, NURSE, ROUTINE, URGENT
from .router import PlannedTicket

DIET_NOTE = {
    "clear_liquids": "Diet: clear liquids only",
    "diabetic": "Diet: consistent carbohydrate (diabetic)",
    "fluid_restricted": "Diet: fluid restricted",
}
ISOLATION_NOTE = {
    "contact": "Contact isolation: gown and gloves before entering",
    "droplet": "Droplet isolation: mask before entering",
}
# Requests that mean the patient wants to get out of bed. Checked against the
# nurse ticket's summary, which the model writes in English whatever the patient spoke.
MOBILITY = re.compile(
    r"\b(bathroom|restroom|toilet|commode|shower|walk\w*|stand(ing)? up|"
    r"get(ting)? (up|out of bed)|out of (the |my )?bed|to the chair)\b", re.IGNORECASE)

WAITING = "waiting_for_patient"


@dataclass
class PolicyOutcome:
    tickets: list[PlannedTicket]
    applied: list[str] = field(default_factory=list)   # which rules fired, for the trace
    patient_note: str | None = None                    # an extra sentence for the patient, in English


def _nurse_ticket(tickets: list[PlannedTicket]) -> PlannedTicket | None:
    return next((t for t in tickets if t.department == NURSE), None)


def _send_food_to_nurse(tickets: list[PlannedTicket], why: str, rule: str) -> list[PlannedTicket]:
    """Replace the Food Services tickets with a note on the nurse's ticket."""
    asked = "; ".join(t.summary for t in tickets if t.department == FOOD)
    kept = [t for t in tickets if t.department != FOOD]
    message = f"{why} Patient asked for: {asked}"
    nurse = _nurse_ticket(kept)
    if nurse is None:
        kept.append(PlannedTicket(NURSE, ROUTINE, message, [f"patient rule: {rule}"]))
    else:
        nurse.summary = f"{nurse.summary}; {message}"
        nurse.reasons.append(f"patient rule: {rule}")
    return kept


def apply(tickets: list[PlannedTicket], context: PatientContext | None) -> PolicyOutcome:
    """Return the tickets to create for this patient. `context` is None when the
    record could not be read or the room has no patient on file."""
    outcome = PolicyOutcome(tickets=list(tickets))
    wants_food = any(t.department == FOOD for t in outcome.tickets)

    # 1. Food and drink. If we cannot confirm the patient may have it, the nurse decides.
    if wants_food:
        if context is None:
            outcome.tickets = _send_food_to_nurse(
                outcome.tickets, "The diet order could not be checked.", "record unavailable")
            outcome.applied.append("record_unavailable")
        elif context.diet == "npo":
            outcome.tickets = _send_food_to_nurse(
                outcome.tickets, "Patient is not allowed food or drink (nothing by mouth).", "nothing by mouth")
            outcome.applied.append("npo")
        elif context.diet == "unknown":
            outcome.tickets = _send_food_to_nurse(
                outcome.tickets, "No active diet order on record.", "no diet order")
            outcome.applied.append("no_diet_order")
        if outcome.applied:
            outcome.patient_note = "Your nurse will come and talk with you about food and drink."

    if context is not None:
        for ticket in outcome.tickets:
            # 2. Restricted diets and food allergies go on the Food Services ticket.
            if ticket.department == FOOD:
                if context.diet in DIET_NOTE:
                    ticket.notes.append(DIET_NOTE[context.diet])
                    outcome.applied.append("diet_note")
                if context.allergies:
                    ticket.notes.append("Food allergy: " + ", ".join(context.allergies))
                    outcome.applied.append("allergy_note")

            # 3. A high fall risk patient asking to get up is urgent.
            if ticket.department == NURSE and context.fall_risk == "high":
                ticket.notes.append("High fall risk")
                if MOBILITY.search(ticket.summary) and ticket.priority != URGENT:
                    ticket.priority = URGENT
                    ticket.reasons.append("patient rule: high fall risk and asking to get up")
                    outcome.applied.append("fall_risk_urgent")

            # 4. Anyone entering the room needs to know about isolation.
            if context.isolation in ISOLATION_NOTE:
                ticket.notes.append(ISOLATION_NOTE[context.isolation])
                outcome.applied.append("isolation_note")

            # 5. Do not send a support team to an empty room. The nurse still gets clinical tickets.
            if context.location == "off_unit" and ticket.department != NURSE:
                ticket.status = WAITING
                ticket.notes.append("Patient is off the unit. Deliver when they are back.")
                outcome.applied.append("off_unit_hold")

    outcome.applied = list(dict.fromkeys(outcome.applied))          # keep order, drop repeats
    outcome.tickets.sort(key=lambda t: (t.department != NURSE, t.priority != URGENT))
    return outcome
