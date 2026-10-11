"""The API end to end, in offline mode."""
from fastapi.testclient import TestClient

from app import main


def client():
    main.store.__init__()            # fresh store for each test
    return TestClient(main.app)


def test_pillow_request_lands_with_housekeeping_only():
    response = client().post("/api/requests", json={"room": "412", "text": "Can I get an extra pillow?"})
    assert response.status_code == 200
    tickets = response.json()["tickets"]
    assert [(t["department"], t["priority"]) for t in tickets] == [("housekeeping_facilities", "routine")]
    assert tickets[0]["room"] == "412"


def test_dashboard_hears_about_a_new_ticket_live():
    c = client()
    with c.websocket_connect("/ws") as socket:
        c.post("/api/requests", json={"room": "7", "text": "I'm having chest pain"})
        event = socket.receive_json()
    assert event["type"] == "ticket_created"
    assert (event["ticket"]["department"], event["ticket"]["priority"]) == ("nurse", "urgent")


def test_nurse_button_needs_no_text():
    response = client().post("/api/requests", json={"room": "3", "direct_nurse": True})
    assert response.json()["tickets"][0]["priority"] == "urgent"


def test_empty_request_is_refused():
    assert client().post("/api/requests", json={"room": "3", "text": "  "}).status_code == 422


def test_ticket_can_be_acknowledged_and_closed():
    c = client()
    ticket_id = c.post("/api/requests", json={"room": "9", "text": "The TV has no sound"}).json()["tickets"][0]["id"]
    assert c.post(f"/api/tickets/{ticket_id}/status", json={"status": "acknowledged"}).json()["status"] == "acknowledged"
    c.post(f"/api/tickets/{ticket_id}/status", json={"status": "done"})
    assert c.get("/api/tickets").json()["tickets"] == []


def test_stats_count_requests_kept_off_the_nurse():
    c = client()
    c.post("/api/requests", json={"room": "412", "text": "Can I get some juice?"})
    c.post("/api/requests", json={"room": "402", "text": "I fell"})
    stats = c.get("/api/tickets").json()["stats"]
    assert (stats["requests_total"], stats["requests_without_nurse"]) == (2, 1)
    assert stats["by_team"] == {"food_services": {"total": 1, "done": 0}, "nurse": {"total": 1, "done": 0}}


# ---- the patient's record changes what happens (rooms are the pinned patients in data/README.md) ----

def ask(room, text):
    response = client().post("/api/requests", json={"room": room, "text": text})
    assert response.status_code == 200
    return response.json()


def test_patient_who_may_not_drink_asks_for_water_and_the_nurse_is_told():
    body = ask("425", "I'm thirsty, can I get some water?")          # Daniel Reyes, nothing by mouth
    assert [(t["department"], t["priority"]) for t in body["tickets"]] == [("nurse", "routine")]
    assert "not allowed food or drink" in body["tickets"][0]["summary"]
    assert body["trace"]["patient_rules"] == ["npo"]
    assert body["patient_note"] == "Your nurse will come and talk with you about food and drink."


def test_same_request_from_a_patient_on_a_regular_diet_goes_to_food_services():
    body = ask("412", "I'm thirsty, can I get some water?")          # Harold Whitaker
    assert [t["department"] for t in body["tickets"]] == ["food_services"]
    assert body["tickets"][0]["notes"] == []


def test_food_ticket_carries_diet_and_allergy_and_nothing_else():
    ticket = ask("415", "Could I have a snack?")["tickets"][0]        # Dorothy Okafor
    assert ticket["department"] == "food_services"
    assert ticket["notes"] == ["Diet: consistent carbohydrate (diabetic)", "Food allergy: Peanut"]


def test_housekeeping_ticket_shows_isolation_but_not_the_diet():
    ticket = ask("419", "Can I get an extra pillow?")["tickets"][0]   # Marcus Bell, clear liquids, contact isolation
    assert ticket["department"] == "housekeeping_facilities"
    assert ticket["notes"] == ["Contact isolation: gown and gloves before entering"]


def test_request_from_a_patient_off_the_unit_waits():
    ticket = ask("421", "Can I get an extra blanket?")["tickets"][0]  # Priya Nair, at Radiology
    assert ticket["status"] == "waiting_for_patient"
    assert "off the unit" in ticket["notes"][0]


def test_unknown_room_sends_food_to_the_nurse_because_the_diet_cannot_be_checked():
    body = ask("999", "Can I get some juice?")
    assert [t["department"] for t in body["tickets"]] == ["nurse"]
    assert body["trace"]["record_found"] is False
    assert body["trace"]["patient_rules"] == ["record_unavailable"]


def test_ticket_shows_the_patient_name_to_staff():
    assert ask("414", "Necesito otra almohada")["tickets"][0]["patient_name"] == "Rosa Delgado"


def test_bell_page_learns_only_the_room_and_the_language():
    c = client()
    assert c.get("/api/patients/414").json() == {"room": "414", "language": "es"}
    assert c.get("/api/patients/999").status_code == 404


# ---- teams, voice and pages for the React frontend ----

def test_tickets_carry_the_team_that_works_them():
    tickets = client().post("/api/requests", json={"room": "412", "text": "The light above my bed keeps flickering."}).json()["tickets"]
    assert [(t["department"], t["team"], t["team_name"]) for t in tickets] == \
        [("housekeeping_facilities", "facilities_biomed", "Facilities & Biomed")]


def test_complaint_and_interpreter_go_to_patient_advocacy():
    tickets = client().post("/api/requests", json={"room": "412", "text": "I want to make a complaint"}).json()["tickets"]
    assert [(t["department"], t["team"]) for t in tickets] == [("patient_advocacy", "patient_advocacy")]


def test_insurance_question_goes_to_case_management():
    tickets = client().post("/api/requests", json={"room": "412", "text": "Does my insurance cover a nursing home?"}).json()["tickets"]
    assert [t["department"] for t in tickets] == ["case_management"]


def test_clinical_words_still_reach_the_nurse_alongside_a_new_team():
    tickets = client().post("/api/requests", json={"room": "412", "text": "I need an interpreter, my chest hurts"}).json()["tickets"]
    assert tickets[0]["department"] == "nurse" and tickets[0]["priority"] == "urgent"
    assert "patient_advocacy" in {t["department"] for t in tickets}


def test_stats_count_each_team_including_done():
    c = client()
    ticket = c.post("/api/requests", json={"room": "412", "text": "Can I get an extra pillow?"}).json()["tickets"][0]
    c.post(f"/api/tickets/{ticket['id']}/status", json={"status": "done"})
    assert c.get("/api/tickets").json()["stats"]["by_team"] == {"environmental_services": {"total": 1, "done": 1}}


def test_voice_endpoints_are_mounted():
    c = client()
    # mounted: a bad body is refused (422), not "not found" (404)
    assert c.post("/api/speak", json={}).status_code == 422
    assert c.post("/api/transcribe").status_code == 422


def test_pages_serve_the_react_build(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<div id=root></div>")
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path)
    c = client()
    for path in ("/", "/patient", "/dashboard"):
        response = c.get(path)
        assert response.status_code == 200 and "root" in response.text


def test_pages_explain_how_to_build_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path / "nothing")
    response = client().get("/dashboard")
    assert response.status_code == 503 and "npm run build" in response.text
