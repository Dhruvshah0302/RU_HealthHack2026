"""Call Bell Router API: patient requests in, department tickets out, live to the dashboard."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ehr, policy
from .teams import team_for
from .baseline import BaselineClassifier
from .router import route
from .store import TicketStore
from .voice import router as voice_router, voice_status

load_dotenv()
logger = logging.getLogger("callbell")
# The React app (frontend/), built with `npm run build`. Set FRONTEND_DIST to serve another build.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST") or Path(__file__).resolve().parent.parent / "frontend" / "dist")

app = FastAPI(title="Call Bell Router")
app.include_router(voice_router)      # ElevenLabs proxy: /api/transcribe, /api/speak
store = TicketStore()
dashboards: set[WebSocket] = set()


def build_classifier():
    """Use the Bedrock model when BEDROCK_MODEL_ID is set, otherwise the keyword baseline."""
    if os.getenv("BEDROCK_MODEL_ID"):
        from .llm import BedrockClassifier
        return BedrockClassifier()
    logger.warning("BEDROCK_MODEL_ID is not set: running in offline mode with the keyword baseline")
    return BaselineClassifier()


classifier = build_classifier()


class PatientRequest(BaseModel):
    room: str = Field(min_length=1, max_length=12)
    text: str = Field(default="", max_length=600)
    direct_nurse: bool = False


class StatusUpdate(BaseModel):
    status: str


async def broadcast(event: dict) -> None:
    for socket in list(dashboards):
        try:
            await socket.send_json(event)
        except Exception:
            dashboards.discard(socket)


_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Frontend not built</title>
<body style="font-family:system-ui;max-width:40rem;margin:3rem auto;line-height:1.5">
<h1>The frontend has not been built yet</h1>
<p>Run this once, then reload:</p>
<pre style="background:#f3f5f7;padding:1rem;border-radius:8px">cd frontend
npm install
npm run build</pre>
<p>Or, while working on the pages, run <code>npm run dev</code> in <code>frontend/</code> and open
<a href="http://localhost:5173/?mock=0">http://localhost:5173/?mock=0</a> instead.</p></body>"""


def _page():
    """Both pages are one React app; it picks the page from the address."""
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HTMLResponse(_NOT_BUILT, status_code=503)
    return FileResponse(index)


@app.get("/")
def home():
    return _page()


@app.get("/patient")
def patient_page():
    return _page()


@app.get("/dashboard")
def dashboard_page():
    return _page()


if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/api/health")
def health():
    return {"ok": True, "classifier": classifier.source, "voice": voice_status()}


@app.post("/api/requests")
async def create_request(body: PatientRequest):
    if not body.direct_nurse and not body.text.strip():
        raise HTTPException(status_code=422, detail="Type or say what you need.")
    decision = await run_in_threadpool(route, body.text, classifier, body.direct_nurse)
    # The record is read by code, after the model has answered. The model never sees it.
    context = ehr.get_context(body.room)
    outcome = policy.apply(decision.tickets, context)
    name = context.name if context else None
    tickets = [store.add(body.room, body.text, planned, patient_name=name, team=team_for(planned),
                         classified_by=decision.classifier_source)
               for planned in outcome.tickets]
    store.record_request([t.department for t in tickets])
    for ticket in tickets:
        await broadcast({"type": "ticket_created", "ticket": ticket.to_dict(), "stats": store.stats()})
    return {
        "tickets": [t.to_dict() for t in tickets],
        "trace": {
            "rule_flags": decision.rule_flags, "classifier": decision.classifier_source,
            "confidence": decision.confidence, "fail_safe": decision.fail_safe,
            "language": decision.language, "patient_rules": outcome.applied,
            "record_found": context is not None,
        },
        # for the patient's screen: which language to answer in, and anything extra to say
        "patient_language": context.language if context else decision.language,
        "patient_note": outcome.patient_note,
    }


@app.get("/api/patients/{room}")
def patient_for_bell_page(room: str):
    """What the bedside page may know: the room and the language to speak. Nothing else."""
    context = ehr.get_context(room)
    if context is None:
        raise HTTPException(status_code=404, detail="no patient on record for this room")
    return {"room": context.room, "language": context.language}


@app.get("/api/tickets")
def list_tickets():
    return {"tickets": [t.to_dict() for t in store.open_tickets()], "stats": store.stats()}


@app.post("/api/tickets/{ticket_id}/status")
async def update_status(ticket_id: str, body: StatusUpdate):
    if body.status not in ("acknowledged", "done"):
        raise HTTPException(status_code=422, detail="status must be 'acknowledged' or 'done'")
    ticket = store.set_status(ticket_id, body.status)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    await broadcast({"type": "ticket_updated", "ticket": ticket.to_dict(), "stats": store.stats()})
    return ticket.to_dict()


@app.websocket("/ws")
async def dashboard_socket(socket: WebSocket):
    await socket.accept()
    dashboards.add(socket)
    try:
        while True:
            await socket.receive_text()      # keep the connection open; dashboards only listen
    except WebSocketDisconnect:
        dashboards.discard(socket)
