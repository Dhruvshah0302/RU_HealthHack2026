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
    c.post("/api/requests", json={"room": "1", "text": "Can I get some juice?"})
    c.post("/api/requests", json={"room": "2", "text": "I fell"})
    assert c.get("/api/tickets").json()["stats"] == {"requests_total": 2, "requests_without_nurse": 1}
