"""FastAPI entrypoint.  Run:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Bed, Room, SessionLocal, init_db
from .routers import admin, requests, tickets


def seed_demo_data() -> None:
    """Demo rooms/beds so the bedside app works immediately (aliases are fictional)."""
    with SessionLocal() as db:
        if db.query(Room).count():
            return
        for room in ["410", "411", "412"]:
            db.add(Room(room_id=room, unit="Med-Surg 4"))
            for side in "AB":
                db.add(Bed(bed_id=f"{room}{side}", room_id=room,
                           patient_alias=f"Demo Patient {room}{side}", occupied=True))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_demo_data()
    yield


app = FastAPI(title="AI Call Bell Router", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "*"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(requests.router)
app.include_router(tickets.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"ok": True, "llm_provider": settings.llm_provider,
            "model": settings.bedrock_model_id if settings.llm_provider == "bedrock" else "MOCK (dev only)",
            "tts": settings.enable_tts}
