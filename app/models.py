"""Shared types: departments, categories, and what a classifier returns."""
from __future__ import annotations

from dataclasses import dataclass, field

NURSE = "nurse"
HOUSEKEEPING = "housekeeping_facilities"
FOOD = "food_services"
UNIT_CLERK = "unit_clerk_it"
ADVOCACY = "patient_advocacy"
CASE_MANAGEMENT = "case_management"

DEPARTMENTS = {
    NURSE: "Nurse",
    HOUSEKEEPING: "Housekeeping & Facilities",
    FOOD: "Food Services",
    UNIT_CLERK: "Unit Clerk / IT",
    ADVOCACY: "Patient Advocacy",
    CASE_MANAGEMENT: "Case Management",
}

URGENT = "urgent"
ROUTINE = "routine"

# A classifier picks a category; the department and the team are always derived from it
# here, so a model can never invent a department or send a clinical request elsewhere.
CATEGORY_TO_DEPARTMENT = {
    "cleaning_environment": HOUSEKEEPING,
    "facilities_equipment": HOUSEKEEPING,
    "dietary": FOOD,
    "tech_amenities": UNIT_CLERK,
    "patient_relations": ADVOCACY,
    "care_coordination": CASE_MANAGEMENT,
    "clinical": NURSE,
    "unknown": NURSE,
}

# The team that works the ticket: the model's category picks it (one screen per team).
CATEGORY_TO_TEAM = {
    "cleaning_environment": "environmental_services",
    "facilities_equipment": "facilities_biomed",
    "dietary": FOOD,
    "tech_amenities": "unit_clerk",
    "patient_relations": ADVOCACY,
    "care_coordination": CASE_MANAGEMENT,
    "clinical": NURSE,
    "unknown": NURSE,
}


@dataclass
class Intent:
    """One need found in a patient's request."""
    category: str
    priority: str = ROUTINE
    summary: str = ""

    @property
    def department(self) -> str:
        return CATEGORY_TO_DEPARTMENT[self.category]

    @property
    def team(self) -> str:
        return CATEGORY_TO_TEAM[self.category]


@dataclass
class Classification:
    intents: list[Intent]
    confidence: float = 1.0
    language: str | None = None
    source: str = "baseline"


@dataclass
class Ticket:
    id: str
    room: str
    department: str
    priority: str
    summary: str
    original_text: str
    created_at: float
    status: str = "open"          # open or waiting_for_patient -> acknowledged -> done
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # patient facts this team needs
    patient_name: str | None = None
    team: str | None = None       # who works it, from the classifier's category
    classified_by: str | None = None   # "llm" (Bedrock), "baseline" (keyword fallback) or "none" (nurse button)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "room": self.room, "department": self.department,
            "department_name": DEPARTMENTS[self.department], "priority": self.priority,
            "summary": self.summary, "original_text": self.original_text,
            "created_at": self.created_at, "status": self.status, "reasons": self.reasons,
            "notes": self.notes, "patient_name": self.patient_name,
            "team": self.team or self.department, "team_name": _team_name(self.team or self.department),
            "classified_by": self.classified_by,
        }


def _team_name(team: str) -> str:
    from .teams import team_name        # imported here: teams.py imports this module
    return team_name(team)
