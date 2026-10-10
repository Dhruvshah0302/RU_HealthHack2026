"""Admin: rooms and beds. Patient info is a demo alias only (no PHI, no EMR)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import Bed, Room, get_db
from ..schemas import BedIn, BedOut, RoomIn

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/rooms", status_code=201)
def create_room(body: RoomIn, db: Session = Depends(get_db)):
    if db.get(Room, body.room_id):
        raise HTTPException(409, "Room exists")
    db.add(Room(**body.model_dump()))
    db.commit()
    return body


@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    return [{"room_id": r.room_id, "unit": r.unit} for r in db.query(Room).all()]


@router.post("/beds", response_model=BedOut, status_code=201)
def create_bed(body: BedIn, db: Session = Depends(get_db)):
    if not db.get(Room, body.room_id):
        raise HTTPException(404, "Room not found")
    bed = Bed(**body.model_dump(), occupied=bool(body.patient_alias))
    db.add(bed)
    db.commit()
    return bed


@router.get("/beds", response_model=list[BedOut])
def list_beds(db: Session = Depends(get_db)):
    return db.query(Bed).all()


@router.patch("/beds/{bed_id}/assign", response_model=BedOut)
def assign(bed_id: str, patient_alias: str, db: Session = Depends(get_db)):
    bed = db.get(Bed, bed_id) or (_ for _ in ()).throw(HTTPException(404))
    bed.patient_alias, bed.occupied = patient_alias, True
    db.commit()
    return bed


@router.patch("/beds/{bed_id}/discharge", response_model=BedOut)
def discharge(bed_id: str, db: Session = Depends(get_db)):
    bed = db.get(Bed, bed_id) or (_ for _ in ()).throw(HTTPException(404))
    bed.patient_alias, bed.occupied = None, False
    db.commit()
    return bed
