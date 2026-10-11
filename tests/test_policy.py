"""Patient-context rules, one test per row of the table in SPEC.md. No network."""
from app.ehr import PatientContext, get_context
from app.models import FOOD, HOUSEKEEPING, NURSE, ROUTINE, UNIT_CLERK, URGENT
from app.policy import apply
from app.router import PlannedTicket


def patient(**changes):
    facts = dict(room="400", name="Test Patient", language="en", diet="regular", allergies=(),
                 fall_risk="standard", isolation="none", location="in_room")
    facts.update(changes)
    return PatientContext(**facts)


def food(summary="Wants water"):
    return PlannedTicket(FOOD, ROUTINE, summary)


def routes(outcome):
    return [(t.department, t.priority) for t in outcome.tickets]


def test_regular_diet_changes_nothing():
    outcome = apply([food()], patient())
    assert routes(outcome) == [(FOOD, ROUTINE)] and outcome.applied == [] and outcome.tickets[0].notes == []


def test_nothing_by_mouth_sends_food_to_the_nurse_not_food_services():
    outcome = apply([food()], patient(diet="npo"))
    assert routes(outcome) == [(NURSE, ROUTINE)]
    assert "not allowed food or drink" in outcome.tickets[0].summary and "Wants water" in outcome.tickets[0].summary
    assert outcome.patient_note


def test_nothing_by_mouth_joins_an_existing_nurse_ticket_and_keeps_it_urgent():
    outcome = apply([PlannedTicket(NURSE, URGENT, "Chest pain"), food()], patient(diet="npo"))
    assert routes(outcome) == [(NURSE, URGENT)]
    assert "Chest pain" in outcome.tickets[0].summary and "Wants water" in outcome.tickets[0].summary


def test_nothing_by_mouth_does_not_touch_other_teams():
    outcome = apply([PlannedTicket(HOUSEKEEPING, ROUTINE, "Wants a pillow"), food()], patient(diet="npo"))
    assert routes(outcome) == [(NURSE, ROUTINE), (HOUSEKEEPING, ROUTINE)]


def test_restricted_diet_is_shown_on_the_food_ticket():
    for diet, words in (("clear_liquids", "clear liquids"), ("diabetic", "diabetic"), ("fluid_restricted", "fluid restricted")):
        outcome = apply([food()], patient(diet=diet))
        assert routes(outcome) == [(FOOD, ROUTINE)]
        assert words in outcome.tickets[0].notes[0]


def test_food_allergy_is_shown_on_the_food_ticket_only():
    outcome = apply([food(), PlannedTicket(HOUSEKEEPING, ROUTINE, "Wants a pillow")], patient(allergies=("Peanut", "Milk")))
    by_team = {t.department: t.notes for t in outcome.tickets}
    assert by_team[FOOD] == ["Food allergy: Peanut, Milk"] and by_team[HOUSEKEEPING] == []


def test_high_fall_risk_asking_to_get_up_becomes_urgent():
    outcome = apply([PlannedTicket(NURSE, ROUTINE, "Needs help getting to the bathroom")], patient(fall_risk="high"))
    assert routes(outcome) == [(NURSE, URGENT)]
    assert "High fall risk" in outcome.tickets[0].notes


def test_high_fall_risk_with_another_request_stays_routine():
    outcome = apply([PlannedTicket(NURSE, ROUTINE, "Asks when the doctor is coming")], patient(fall_risk="high"))
    assert routes(outcome) == [(NURSE, ROUTINE)]


def test_standard_fall_risk_asking_to_get_up_stays_routine():
    outcome = apply([PlannedTicket(NURSE, ROUTINE, "Needs help getting to the bathroom")], patient())
    assert routes(outcome) == [(NURSE, ROUTINE)]


def test_isolation_is_shown_on_every_ticket():
    outcome = apply([PlannedTicket(NURSE, ROUTINE, "Pain medicine"), PlannedTicket(UNIT_CLERK, ROUTINE, "TV has no sound")],
                    patient(isolation="droplet"))
    assert all(any("Droplet isolation" in note for note in t.notes) for t in outcome.tickets)


def test_off_unit_holds_support_tickets_but_not_the_nurse():
    outcome = apply([PlannedTicket(NURSE, ROUTINE, "Pain medicine"), PlannedTicket(HOUSEKEEPING, ROUTINE, "Wants a blanket")],
                    patient(location="off_unit"))
    status = {t.department: t.status for t in outcome.tickets}
    assert status == {NURSE: "open", HOUSEKEEPING: "waiting_for_patient"}


def test_record_unavailable_sends_food_to_the_nurse():
    outcome = apply([food()], None)
    assert routes(outcome) == [(NURSE, ROUTINE)] and outcome.applied == ["record_unavailable"]
    assert "could not be checked" in outcome.tickets[0].summary


def test_record_unavailable_leaves_other_requests_alone():
    outcome = apply([PlannedTicket(HOUSEKEEPING, ROUTINE, "Wants a pillow")], None)
    assert routes(outcome) == [(HOUSEKEEPING, ROUTINE)] and outcome.applied == []


def test_no_diet_order_on_record_is_not_treated_as_regular():
    outcome = apply([food()], patient(diet="unknown"))
    assert routes(outcome) == [(NURSE, ROUTINE)] and outcome.applied == ["no_diet_order"]


def test_rules_never_remove_a_nurse_ticket_or_lower_a_priority():
    for context in (None, patient(), patient(diet="npo", fall_risk="high", isolation="contact", location="off_unit")):
        outcome = apply([PlannedTicket(NURSE, URGENT, "Chest pain"), food()], context)
        assert (NURSE, URGENT) in routes(outcome)


def test_adapter_reads_the_pinned_patients_and_only_the_agreed_fields():
    rosa = get_context("414")
    assert (rosa.name, rosa.language, rosa.diet, rosa.location) == ("Rosa Delgado", "es", "npo", "in_room")
    assert get_context("415").allergies == ("Peanut",)            # penicillin is not passed on
    assert get_context("999") is None
    assert set(rosa.__dataclass_fields__) == {"room", "name", "language", "diet", "allergies",
                                              "fall_risk", "isolation", "location"}


def test_adapter_returns_none_when_the_file_cannot_be_read(tmp_path, monkeypatch):
    from app import ehr
    monkeypatch.setattr(ehr, "_source", ehr.FileEHR(tmp_path / "missing.json"))
    assert ehr.get_context("412") is None
