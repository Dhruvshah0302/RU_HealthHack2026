"""Routing policy: turn one patient request into one or more department tickets.

The order matters and is the safety argument for the whole project:

1. Red-flag rules run first and can only escalate to the nurse.
2. The classifier (model or baseline) proposes intents.
3. If the classifier fails, returns nothing usable, or is not confident, the
   request goes to the nurse. A request is never dropped and never guessed.
4. A request with several needs becomes several tickets, so a blanket request
   does not hide a clinical one, and a clinical one does not delay the blanket.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from .models import NURSE, ROUTINE, URGENT, Classification, Intent
from .rules import red_flags

logger = logging.getLogger("callbell")


@dataclass
class PlannedTicket:
    department: str
    priority: str
    summary: str
    reasons: list[str] = field(default_factory=list)
    team: str | None = None                          # from the classifier's category; None means the department's own team
    notes: list[str] = field(default_factory=list)   # patient facts this team needs (app/policy.py)
    status: str = "open"                             # "waiting_for_patient" when the patient is off the unit


@dataclass
class Decision:
    tickets: list[PlannedTicket]
    rule_flags: list[str]
    classifier_source: str
    confidence: float | None
    fail_safe: str | None        # why the nurse fallback was used, if it was
    language: str | None = None


def _min_confidence() -> float:
    return float(os.getenv("MIN_CONFIDENCE", "0.7"))


def route(text: str, classifier, direct_nurse: bool = False) -> Decision:
    text = (text or "").strip()

    if direct_nurse:
        ticket = PlannedTicket(NURSE, URGENT, text or "Patient pressed 'Call my nurse now'",
                               ["patient pressed the nurse button"])
        return Decision([ticket], [], "none", None, None)

    flags = red_flags(text)
    result: Classification | None = None
    fail_safe = None
    try:
        result = classifier.classify(text)
        if not result.intents:
            raise ValueError("classifier returned no intents")
    except Exception as exc:                      # any failure means the nurse decides
        fail_safe = f"classifier failed: {type(exc).__name__}"
        logger.warning("classifier failed, routing to nurse: %s", exc)

    if result is not None and result.confidence < _min_confidence():
        fail_safe = f"low confidence ({result.confidence:.2f})"

    if fail_safe:
        # The fallback can raise a request but never lower it. A model that was unsure
        # but still called something urgent leaves the nurse ticket urgent.
        was_urgent = result is not None and any(i.priority == URGENT for i in result.intents)
        intents = [Intent(category="unknown", priority=URGENT if was_urgent else ROUTINE,
                          summary="Could not sort this request. Please check on the patient.")]
    else:
        intents = result.intents

    # One ticket per team, so a cleaning need and a broken bed go to the two teams that do them.
    # The nurse's team key is NURSE, so the red-flag step below finds the nurse ticket as before.
    by_department: dict[str, PlannedTicket] = {}
    for intent in intents:
        summary = intent.summary or text[:120]
        existing = by_department.get(intent.team)
        if existing is None:
            reason = fail_safe or f"{getattr(classifier, 'source', 'classifier')}: {intent.category}"
            by_department[intent.team] = PlannedTicket(intent.department, intent.priority, summary, [reason],
                                                       team=intent.team)
        else:
            if summary not in existing.summary:
                existing.summary = f"{existing.summary}; {summary}"
            if intent.priority == URGENT:
                existing.priority = URGENT

    if flags:
        nurse = by_department.get(NURSE)
        reason = "red-flag rule: " + ", ".join(flags)
        if nurse is None:
            by_department[NURSE] = PlannedTicket(NURSE, URGENT, text[:160], [reason])
        else:
            nurse.priority = URGENT
            nurse.reasons.append(reason)
            if fail_safe:                         # show the patient's words, not the fallback text
                nurse.summary = text[:160]

    # nurse first, then urgent before routine
    tickets = sorted(by_department.values(), key=lambda t: (t.department != NURSE, t.priority != URGENT))
    return Decision(
        tickets=tickets, rule_flags=flags,
        classifier_source=getattr(classifier, "source", "classifier"),
        confidence=None if result is None else result.confidence,
        fail_safe=fail_safe, language=None if result is None else result.language,
    )
