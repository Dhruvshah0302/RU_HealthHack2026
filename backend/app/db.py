"""Database setup + tables (SQLAlchemy 2.0)."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Room(Base):
    __tablename__ = "rooms"
    room_id: Mapped[str] = mapped_column(String, primary_key=True)
    unit: Mapped[str] = mapped_column(String, default="Med-Surg")


class Bed(Base):
    __tablename__ = "beds"
    bed_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"))
    patient_alias: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # demo label only
    occupied: Mapped[bool] = mapped_column(Boolean, default=False)


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bed_id: Mapped[str] = mapped_column(ForeignKey("beds.bed_id"))
    room_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String, default="en")
    category: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String, index=True)
    priority: Mapped[str] = mapped_column(String)
    is_clinical: Mapped[bool] = mapped_column(Boolean)
    summary: Mapped[str] = mapped_column(String)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decided_by: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
