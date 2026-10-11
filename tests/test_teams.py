"""The classifier's category picks the team. Nothing re-routes a ticket afterwards,
except the safety rules, which only add or escalate a clinical ticket."""
from app.models import CATEGORY_TO_DEPARTMENT, CATEGORY_TO_TEAM, NURSE, Intent
from app.llm import CATEGORIES
from app.router import PlannedTicket
from app.teams import team_for, team_name


def test_every_model_category_has_a_team_and_a_department():
    assert set(CATEGORIES) == set(CATEGORY_TO_TEAM) == set(CATEGORY_TO_DEPARTMENT)


def test_clinical_and_unknown_always_go_to_the_clinical_team():
    assert Intent("clinical").team == Intent("unknown").team == NURSE


def test_cleaning_and_facilities_are_separate_teams():
    assert Intent("cleaning_environment").team == "environmental_services"
    assert Intent("facilities_equipment").team == "facilities_biomed"


def test_tickets_without_a_category_belong_to_their_department_team():
    assert team_for(PlannedTicket(NURSE, "routine", "food check")) == NURSE
    assert team_for(PlannedTicket("unit_clerk_it", "routine", "x")) == "unit_clerk"
    assert team_for(PlannedTicket("housekeeping_facilities", "routine", "x", team="facilities_biomed")) == "facilities_biomed"


def test_every_team_has_a_name():
    for team in set(CATEGORY_TO_TEAM.values()):
        assert team_name(team) != team
