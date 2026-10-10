"""Patient-facing endpoints: submit by text or voice; optional spoken confirmation."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import Bed, Ticket, get_db
from ..schemas import RequestResult, TextRequestIn, TicketOut
from ..services import elevenlabs
from ..triage.engine import patient_message, triage

router = APIRouter(prefix="/api", tags=["patient"])


async def _create_ticket(db: Session, bed_id: str, text: str, stt_language: str | None = None) -> RequestResult:
    bed = db.get(Bed, bed_id)
    if not bed:
        raise HTTPException(404, f"Unknown bed '{bed_id}'")

    result = await run_in_threadpool(triage, text)   # boto3 is sync
    t = Ticket(
        bed_id=bed_id, room_label=bed.room_id, original_text=text,
        translated_text=result.translated_text, language=stt_language or result.language,
        category=result.category.value, department=result.department.value,
        priority=result.priority.value, is_clinical=result.is_clinical, summary=result.summary,
        escalation_reason=result.escalation_reason, needs_review=result.needs_review,
        confidence=result.confidence, decided_by=result.decided_by,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return RequestResult(
        ticket=TicketOut.model_validate(t),
        patient_message=patient_message(result),
        tts_url=f"/api/tickets/{t.ticket_id}/confirmation.mp3" if settings.enable_tts else None,
    )


@router.post("/requests/text", response_model=RequestResult)
async def submit_text(body: TextRequestIn, db: Session = Depends(get_db)):
    return await _create_ticket(db, body.bed_id, body.text.strip())


@router.post("/requests/voice", response_model=RequestResult)
async def submit_voice(bed_id: str = Form(...), audio: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty audio")
    try:
        text, lang = await elevenlabs.speech_to_text(data, audio.filename or "note.webm",
                                                      audio.content_type or "audio/webm")
    except elevenlabs.STTError as e:
        # Frontend shows: "Sorry, I couldn't hear that. Please type your request."
        raise HTTPException(502, f"Speech-to-text failed: {e}")
    return await _create_ticket(db, bed_id, text, stt_language=lang)


@router.get("/tickets/{ticket_id}/confirmation.mp3")
async def confirmation_audio(ticket_id: int, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404)
    from ..schemas import TriageResult
    msg = patient_message(TriageResult(
        category=t.category, department=t.department, priority=t.priority,
        is_clinical=t.is_clinical, summary=t.summary, decided_by=t.decided_by))
    try:
        audio = await elevenlabs.text_to_speech(msg)
    except Exception as e:
        raise HTTPException(502, f"TTS failed: {e}")
    return Response(content=audio, media_type="audio/mpeg")


@router.get("/bedside/{bed_id}/tickets", response_model=list[TicketOut])
def bedside_tickets(bed_id: str, db: Session = Depends(get_db)):
    """Patient screen polls this to show 'On the way' / 'Done'."""
    return db.query(Ticket).filter(Ticket.bed_id == bed_id).order_by(Ticket.created_at.desc()).limit(10).all()
