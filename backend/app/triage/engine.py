"""Triage engine: red-flag gate + LLM + guardrails -> final routing decision.

Safety rules (release-blocking):
1. Red flag hit                  -> nursing, urgent (LLM cannot override)
2. LLM says clinical             -> nursing (LLM priority, never 'routine')
3. LLM error/timeout/invalid     -> nursing, needs_review (never drop, never guess non-clinical)
4. Low confidence / 'other'      -> nursing, needs_review
5. Otherwise                     -> department from CATEGORY_TO_DEPARTMENT
"""
import logging
from typing import Callable

from ..config import settings
from ..schemas import (CATEGORY_TO_DEPARTMENT, Category, Department, LLMClassification,
                       Priority, TriageResult)
from . import red_flags
from .llm import classify as bedrock_classify
from .mock_llm import classify as mock_classify

log = logging.getLogger("triage")


def _default_classifier() -> Callable[[str], LLMClassification]:
    return mock_classify if settings.llm_provider == "mock" else bedrock_classify


def triage(text: str, classifier: Callable[[str], LLMClassification] | None = None) -> TriageResult:
    classifier = classifier or _default_classifier()
    rf = red_flags.check(text)

    try:
        llm = classifier(text)
    except Exception as e:  # timeout, auth, throttling, bad JSON, validation error...
        log.warning("LLM failed, using safe fallback: %s", e)
        return TriageResult(
            category=Category.clinical if rf.hit else Category.other,
            department=Department.nursing,
            priority=Priority.urgent if rf.hit else Priority.soon,
            is_clinical=rf.hit,
            summary="Patient request – needs nurse review",
            escalation_reason=(f"Red flags: {', '.join(rf.reasons)}. " if rf.hit else "")
            + "AI classification unavailable; routed to nursing for safety.",
            needs_review=True,
            decided_by="fallback",
        )

    base = dict(summary=llm.summary, items=llm.items, language=llm.language,
                translated_text=llm.translated_text, confidence=llm.confidence)

    # Rule 1: deterministic red flags win
    if rf.hit:
        return TriageResult(category=Category.clinical, department=Department.nursing,
                            priority=Priority.urgent, is_clinical=True,
                            escalation_reason=f"Red flags: {', '.join(rf.reasons)}",
                            decided_by="red_flag+llm", **base)

    # Rule 2: LLM says clinical
    if llm.is_clinical or llm.category == Category.clinical:
        prio = llm.priority if llm.priority != Priority.routine else Priority.soon
        return TriageResult(category=Category.clinical, department=Department.nursing,
                            priority=prio, is_clinical=True,
                            escalation_reason=llm.reason or "Clinical request",
                            decided_by="llm", **base)

    # Rule 4: uncertain -> human review by nursing
    if llm.confidence < settings.llm_min_confidence or llm.category == Category.other:
        return TriageResult(category=llm.category, department=Department.nursing,
                            priority=Priority.soon, is_clinical=False,
                            escalation_reason=f"Low confidence ({llm.confidence:.2f}) or unclear request",
                            needs_review=True, decided_by="llm_low_confidence", **base)

    # Rule 5: normal non-clinical routing
    return TriageResult(category=llm.category, department=CATEGORY_TO_DEPARTMENT[llm.category],
                        priority=Priority.routine, is_clinical=False, decided_by="llm", **base)


def patient_message(result: TriageResult) -> str:
    """Wording shown/spoken to the patient. Never claims a human was notified;
    it says the request was placed in a queue (which is what the system actually does)."""
    if result.priority == Priority.urgent:
        return ("Your request has been sent to the nursing team as URGENT. "
                "If you feel worse or this is an emergency, press your bedside call button now.")
    if result.department == Department.nursing:
        return "Your request has been sent to the nursing team's queue."
    names = {Department.housekeeping: "Housekeeping", Department.food_services: "Food Services",
             Department.facilities: "Facilities", Department.it_support: "IT Support"}
    return f"Got it: {result.summary}. Your request has been sent to {names[result.department]}."
