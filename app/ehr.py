"""Patient facts for the routing rules, read from FHIR resources.

This is the only module that reads a patient's record. It hands back eight
fields and nothing else, and it is never called by the model: code fetches the
record, code applies the rules (app/policy.py).

Today the resources come from data/fhir_bundle.json, which holds synthetic
patients. A hospital's FHIR server returns the same resource shapes, so a
second source can sit behind get_context() without the rest of the app changing.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("callbell")

DEFAULT_BUNDLE = Path(__file__).resolve().parent.parent / "data" / "fhir_bundle.json"


@dataclass(frozen=True)
class PatientContext:
    room: str
    name: str
    language: str                 # en, es, hi, zh, ar, pt
    diet: str                     # regular, npo, clear_liquids, diabetic, fluid_restricted, unknown
    allergies: tuple[str, ...]    # food allergies only
    fall_risk: str                # standard, high
    isolation: str                # none, contact, droplet
    location: str                 # in_room, off_unit


def contexts_from_bundle(bundle: dict) -> dict[str, dict]:
    """Map each room number to the patient facts the routing rules need."""
    by_type: dict[str, list[dict]] = {}
    for entry in bundle["entry"]:
        resource = entry["resource"]
        by_type.setdefault(resource["resourceType"], []).append(resource)
    room_names = {f"Location/{loc['id']}": loc["name"] for loc in by_type.get("Location", [])
                  if loc["name"].startswith("Room ")}
    patients = {f"Patient/{p['id']}": p for p in by_type.get("Patient", [])}

    def for_patient(kind: str, ref: str, key: str = "patient") -> list[dict]:
        return [r for r in by_type.get(kind, []) if r[key]["reference"] == ref]

    out = {}
    for enc in by_type.get("Encounter", []):
        if enc["status"] != "in-progress":
            continue
        stays = [s for s in enc["location"] if s["location"]["reference"] in room_names]
        if not stays:
            continue
        room = room_names[stays[0]["location"]["reference"]].removeprefix("Room ")
        ref = enc["subject"]["reference"]
        patient = patients[ref]
        diets = [o for o in for_patient("NutritionOrder", ref) if o["status"] == "active"]
        allergies = [a for a in for_patient("AllergyIntolerance", ref)
                     if a["clinicalStatus"]["coding"][0]["code"] == "active"]
        flag_codes = {f["code"]["coding"][0]["code"] for f in for_patient("Flag", ref, "subject")
                      if f["status"] == "active"}
        isolation = next((c.removeprefix("isolation-") for c in sorted(flag_codes)
                          if c.startswith("isolation-")), "none")
        out[room] = {
            "room": room,
            "name": f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}",
            "language": patient["communication"][0]["language"]["coding"][0]["code"],
            # No active diet order means we do not know the diet. Never assume "regular".
            "diet": diets[0]["oralDiet"]["type"][0]["coding"][0]["code"] if diets else "unknown",
            "allergies": [a["code"]["text"] for a in allergies if "food" in a.get("category", [])],
            "fall_risk": "high" if "fall-risk-high" in flag_codes else "standard",
            "isolation": isolation,
            "location": "in_room" if stays[0].get("status") == "active" else "off_unit",
        }
    return out


class FileEHR:
    """Reads the FHIR bundle from disk once and answers from memory."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("EHR_BUNDLE_PATH") or DEFAULT_BUNDLE)
        self._contexts: dict[str, PatientContext] | None = None

    def get_context(self, room: str) -> PatientContext | None:
        if self._contexts is None:
            bundle = json.loads(self.path.read_text(encoding="utf-8"))
            self._contexts = {
                key: PatientContext(**{**facts, "allergies": tuple(facts["allergies"])})
                for key, facts in contexts_from_bundle(bundle).items()
            }
        return self._contexts.get(str(room).strip())


_source = FileEHR()


def get_context(room: str) -> PatientContext | None:
    """The patient in this room, or None when there is no record or it cannot be read.

    None is a normal answer, not an error to hide: the rules treat "we could not
    check the record" as a reason to involve the nurse.
    """
    try:
        return _source.get_context(room)
    except Exception as exc:
        logger.warning("patient record could not be read for room %s: %s", room, exc)
        return None
