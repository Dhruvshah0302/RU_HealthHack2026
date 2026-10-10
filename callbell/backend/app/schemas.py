"""Shared contract. Frontend, triage and DB all use these enums and shapes.
Change this file only by team agreement (it is the API contract)."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Department(str, Enum):
    housekeeping = "housekeeping"     # linens, pillows, blankets, cleaning
    facilities = "facilities"         # temperature, lights, broken fixtures
    food_services = "food_services"   # water, juice, meals, snacks
    it_support = "it_support"         # TV, remote, Wi-Fi, phone, tablet
    nursing = "nursing"               # anything clinical + safety fallback


class Category(str, Enum):
    comfort_linens = "comfort_linens"
    cleaning = "cleaning"
    room_environment = "room_environment"
    dietary = "dietary"
    tech_amenities = "tech_amenities"
    clinical = "clinical"
    other = "other"


class Priority(str, Enum):
    routine = "routine"
    soon = "soon"
    urgent = "urgent"


class TicketStatus(str, Enum):
    new = "new"
    accepted = "accepted"
    done = "done"


# Default routing table for non-clinical categories
CATEGORY_TO_DEPARTMENT: dict[Category, Department] = {
    Category.comfort_linens: Department.housekeeping,
    Category.cleaning: Department.housekeeping,
    Category.room_environment: Department.facilities,
    Category.dietary: Department.food_services,
    Category.tech_amenities: Department.it_support,
    Category.clinical: Department.nursing,
    Category.other: Department.nursing,  # unknown -> human review
}


# ---------- What the LLM must return (validated strictly) ----------
class LLMClassification(BaseModel):
    category: Category
    is_clinical: bool
    priority: Priority
    summary: str = Field(..., max_length=120)
    items: list[str] = []
    translated_text: Optional[str] = None   # English translation if input wasn't English
    language: str = "en"
    confidence: float = Field(..., ge=0, le=1)
    reason: str = Field("", max_length=200)


# ---------- Final triage decision (after guardrails) ----------
class TriageResult(BaseModel):
    category: Category
    department: Department
    priority: Priority
    is_clinical: bool
    summary: str
    items: list[str] = []
    language: str = "en"
    translated_text: Optional[str] = None
    confidence: Optional[float] = None
    escalation_reason: Optional[str] = None
    needs_review: bool = False
    decided_by: str  # "llm", "red_flag+llm", "fallback", ...


# ---------- API shapes ----------
class TextRequestIn(BaseModel):
    bed_id: str
    text: str = Field(..., min_length=1, max_length=1000)


class TicketOut(BaseModel):
    ticket_id: int
    bed_id: str
    room_label: Optional[str] = None
    original_text: str
    translated_text: Optional[str] = None
    language: str
    category: Category
    department: Department
    priority: Priority
    is_clinical: bool
    summary: str
    escalation_reason: Optional[str] = None
    needs_review: bool
    status: TicketStatus
    created_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RequestResult(BaseModel):
    ticket: TicketOut
    patient_message: str          # what the bedside screen shows / speaks
    tts_url: Optional[str] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class RoomIn(BaseModel):
    room_id: str          # e.g. "412"
    unit: str = "Med-Surg"


class BedIn(BaseModel):
    bed_id: str           # e.g. "412B"
    room_id: str
    patient_alias: Optional[str] = None   # demo label only, never real names


class BedOut(BedIn):
    occupied: bool
    model_config = {"from_attributes": True}
