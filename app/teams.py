"""Team names. Which team works a ticket is chosen by the classifier: the model's category
maps to a team in app/models.py (CATEGORY_TO_TEAM). Nothing here re-routes a ticket."""
from __future__ import annotations

from .models import ADVOCACY, CASE_MANAGEMENT, FOOD, NURSE

TEAMS = {
    NURSE: "Clinical",
    "unit_clerk": "Unit Clerk",
    "environmental_services": "Housekeeping",
    FOOD: "Food & Nutrition",
    "facilities_biomed": "Facilities & Biomed",
    ADVOCACY: "Patient Advocacy",
    CASE_MANAGEMENT: "Case Management",
}
# A ticket made without a category (a patient rule sending food to the nurse, the nurse
# button) belongs to its department's own team.
DEPARTMENT_TEAM = {"housekeeping_facilities": "environmental_services", "unit_clerk_it": "unit_clerk"}


def team_for(planned) -> str:
    return planned.team or DEPARTMENT_TEAM.get(planned.department, planned.department)


def team_name(team: str) -> str:
    return TEAMS.get(team, team)
