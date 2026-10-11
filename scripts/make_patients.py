"""Generate the synthetic patients for the Call Bell Router.

Writes two files:

    data/fhir_bundle.json       FHIR R4 transaction Bundle: 60 inpatients on two units
    data/patients_summary.csv   one row per patient, for people to read

Run from the repository root:

    python -m scripts.make_patients            # write both files
    python -m scripts.make_patients --check    # confirm the files on disk match this script

Everything here is invented. No real patient information was used.

The output is fixed: the same script always writes the same bytes. To change a
patient, edit PINNED or the weights below and run the script again. Do not edit
the JSON by hand.

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Settings. Change these, then run the script again.
# ---------------------------------------------------------------------------

SEED = 7
TODAY = date(2026, 10, 10)               # fixed, so ages and dates never drift
EASTERN = timezone(timedelta(hours=-4))
PREFIX = "t07"                           # keeps our ids apart on a shared FHIR server

UNITS = [                                # (id, name, rooms). One bed per room.
    ("4w", "4 West", range(401, 431)),
    ("5w", "5 West", range(501, 531)),
]
OFF_UNIT_PLACES = [                      # where a patient can be when not in the room
    ("radiology", "Radiology"),
    ("dialysis", "Dialysis"),
    ("pt", "Physical Therapy"),
    ("or", "Operating Room"),
]

# The values the routing rules understand. See SPEC.md, "Patient-context rules".
LANGUAGES = {"en": "English", "es": "Spanish", "hi": "Hindi", "zh": "Chinese",
             "ar": "Arabic", "pt": "Portuguese"}
DIETS = {
    "regular": "Regular diet",
    "npo": "NPO (nothing by mouth)",
    "clear_liquids": "Clear liquid diet",
    "diabetic": "Consistent carbohydrate (diabetic) diet",
    "fluid_restricted": "Fluid restricted diet",
}
DIET_INSTRUCTION = {
    "npo": "Nothing by mouth, including water and ice chips.",
    "clear_liquids": "Clear liquids only.",
    "fluid_restricted": "Total fluids limited to 1500 mL per day.",
}
ISOLATION = {"contact": "Contact isolation", "droplet": "Droplet isolation"}
FOOD_ALLERGENS = ["Peanut", "Tree nuts", "Shellfish", "Egg", "Milk", "Wheat", "Soy", "Fish"]
OTHER_ALLERGENS = ["Penicillin", "Sulfa drugs", "Latex", "Codeine"]

# How the 52 random patients are drawn. These are our assumptions, chosen so each
# rule fires a believable number of times. They are not taken from hospital data.
LANGUAGE_WEIGHTS = {"en": 70, "es": 14, "zh": 5, "hi": 4, "pt": 4, "ar": 3}
DIET_WEIGHTS = {"regular": 52, "diabetic": 20, "npo": 12, "clear_liquids": 8, "fluid_restricted": 8}
ISOLATION_WEIGHTS = {"none": 85, "contact": 10, "droplet": 5}
P_FOOD_ALLERGY = 0.18
P_SECOND_FOOD_ALLERGY = 0.20
P_OTHER_ALLERGY = 0.15
P_HIGH_FALL_RISK_70_PLUS = 0.45
P_HIGH_FALL_RISK_UNDER_70 = 0.12
P_OFF_UNIT = 0.08

# Fixed name lists. Names are drawn without regard to language.
FIRST_NAMES_F = ["Alice", "Beatrice", "Carmen", "Diane", "Elena", "Fatima", "Grace", "Hannah",
                 "Irene", "Joyce", "Karen", "Leila", "Maria", "Nadia", "Olivia", "Patricia",
                 "Renee", "Sofia", "Teresa", "Uma", "Vera", "Wendy", "Yasmin", "Zoe",
                 "Anita", "Bianca", "Chloe", "Deepa", "Esther", "Farah"]
FIRST_NAMES_M = ["Adam", "Benjamin", "Carlos", "David", "Edgar", "Felix", "George", "Hassan",
                 "Ivan", "James", "Kevin", "Louis", "Miguel", "Nikhil", "Omar", "Peter",
                 "Rafael", "Samuel", "Thomas", "Victor", "Walter", "Xavier", "Yusuf", "Arjun",
                 "Bruno", "Curtis", "Dennis", "Emeka", "Frank", "Gabriel"]
LAST_NAMES = ["Abbott", "Banerjee", "Castillo", "Dawson", "Ellison", "Farouk", "Greene",
              "Haddad", "Iyer", "Jensen", "Kowalski", "Lambert", "Mendoza", "Novak", "Osei",
              "Pereira", "Quinn", "Romano", "Santos", "Thackeray", "Underwood", "Vasquez",
              "Whitlock", "Yamada", "Zielinski", "Ahmadi", "Barros", "Chaudhry", "Dimitrov",
              "Espinoza", "Fitzgerald", "Guerrero", "Holloway", "Ibrahim", "Joshi", "Keller",
              "Lindqvist", "Marchetti", "Nwosu", "Ortega", "Petrov", "Ramirez", "Sandoval",
              "Tanaka", "Uribe", "Venter", "Wainwright", "Xu", "Yilmaz", "Zamora",
              "Aldridge", "Bergstrom", "Calloway", "Desai", "Engel", "Fontaine"]


@dataclass
class Person:
    """One synthetic patient, before it is turned into FHIR resources."""
    room: int
    first: str
    last: str
    gender: str                       # "female" or "male"
    age: int
    language: str = "en"
    diet: str = "regular"
    food_allergies: list[str] = field(default_factory=list)
    other_allergies: list[str] = field(default_factory=list)
    fall_risk: str = "standard"       # "standard" or "high"
    isolation: str = "none"           # "none", "contact" or "droplet"
    off_unit_at: str | None = None    # key from OFF_UNIT_PLACES, or None when in the room
    purpose: str = ""                 # why a pinned patient exists; blank for random ones


# The eight patients the demo, the tests and the evaluation rely on. Written by hand
# so that each one exercises a rule. Change them here, never in the JSON.
PINNED = [
    Person(412, "Harold", "Whitaker", "male", 67,
           purpose="Baseline. Nothing special: a pillow goes to Housekeeping, water goes to Food Services."),
    Person(414, "Rosa", "Delgado", "female", 58, language="es", diet="npo",
           purpose="May not eat or drink, speaks Spanish. Asks for water: the nurse is told, Food Services is not."),
    Person(415, "Dorothy", "Okafor", "female", 74, diet="diabetic",
           food_allergies=["Peanut"], other_allergies=["Penicillin"], fall_risk="high",
           purpose="Diet and food allergy show on a food ticket. High fall risk: help to the bathroom becomes Level 2."),
    Person(417, "Lian", "Zhou", "female", 81, language="zh", diet="fluid_restricted", fall_risk="high",
           purpose="Fluid restriction shows on a drink ticket. Second non-English speaker, second high fall risk."),
    Person(419, "Marcus", "Bell", "male", 45, diet="clear_liquids",
           food_allergies=["Shellfish"], isolation="contact",
           purpose="Contact isolation shows on any ticket that sends someone into the room."),
    Person(421, "Priya", "Nair", "female", 33, off_unit_at="radiology",
           purpose="Off the unit. A non-clinical request is created as waiting for patient."),
    Person(423, "Ramesh", "Kulkarni", "male", 62, language="hi",
           food_allergies=["Milk"], isolation="droplet",
           purpose="Hindi speaker in droplet isolation with a food allergy."),
    Person(425, "Daniel", "Reyes", "male", 29, diet="npo",
           purpose="May not eat or drink, speaks English. The live demo: \"I'm thirsty, can I get some water?\""),
]


# ---------------------------------------------------------------------------
# Drawing the random patients
# ---------------------------------------------------------------------------

def _pick(rng: random.Random, weights: dict[str, int]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def all_rooms() -> list[int]:
    return [room for _, _, rooms in UNITS for room in rooms]


def build_people() -> list[Person]:
    """The 8 pinned patients plus one random patient for every other room."""
    rng = random.Random(SEED)
    pinned = {p.room: p for p in PINNED}
    used_names = {(p.first, p.last) for p in PINNED}
    people = []
    for room in all_rooms():
        if room in pinned:
            people.append(pinned[room])
            continue
        gender = rng.choice(["female", "male"])
        while True:
            first = rng.choice(FIRST_NAMES_F if gender == "female" else FIRST_NAMES_M)
            last = rng.choice(LAST_NAMES)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break
        age = int(rng.triangular(19, 94, 68))
        food = []
        if rng.random() < P_FOOD_ALLERGY:
            food = rng.sample(FOOD_ALLERGENS, 2 if rng.random() < P_SECOND_FOOD_ALLERGY else 1)
        other = [rng.choice(OTHER_ALLERGENS)] if rng.random() < P_OTHER_ALLERGY else []
        p_fall = P_HIGH_FALL_RISK_70_PLUS if age >= 70 else P_HIGH_FALL_RISK_UNDER_70
        people.append(Person(
            room=room, first=first, last=last, gender=gender, age=age,
            language=_pick(rng, LANGUAGE_WEIGHTS),
            diet=_pick(rng, DIET_WEIGHTS),
            food_allergies=food, other_allergies=other,
            fall_risk="high" if rng.random() < p_fall else "standard",
            isolation=_pick(rng, ISOLATION_WEIGHTS),
            off_unit_at=rng.choice(OFF_UNIT_PLACES)[0] if rng.random() < P_OFF_UNIT else None,
        ))
    return people


# ---------------------------------------------------------------------------
# Turning people into FHIR R4 resources
# ---------------------------------------------------------------------------

LOCAL = "http://example.org/fhir/CodeSystem"     # our own codes; a hospital would use SNOMED CT
META = {
    # HL7's marker for test data, plus our own tag so the records are easy to find.
    "security": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                  "code": "HTEST", "display": "test health data"}],
    "tag": [{"system": "http://example.org/fhir/tag", "code": "team07-call-bell-router"}],
}


def _ref(kind: str, key: object) -> dict:
    return {"reference": f"{kind}/{PREFIX}-{key}"}


def _stamp(days_ago: int, hour: int, minute: int) -> str:
    moment = datetime(TODAY.year, TODAY.month, TODAY.day, hour, minute, tzinfo=EASTERN)
    return (moment - timedelta(days=days_ago)).isoformat()


def location_resources() -> list[dict]:
    out = []
    for unit_id, unit_name, rooms in UNITS:
        out.append({
            "resourceType": "Location", "id": f"{PREFIX}-unit-{unit_id}", "meta": META,
            "status": "active", "name": unit_name, "mode": "instance",
            "physicalType": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "code": "wa", "display": "Ward"}]},
        })
        for room in rooms:
            out.append({
                "resourceType": "Location", "id": f"{PREFIX}-room-{room}", "meta": META,
                "status": "active", "name": f"Room {room}", "mode": "instance",
                "physicalType": {"coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                    "code": "ro", "display": "Room"}]},
                "partOf": {"reference": f"Location/{PREFIX}-unit-{unit_id}", "display": unit_name},
            })
    for place_id, place_name in OFF_UNIT_PLACES:
        out.append({
            "resourceType": "Location", "id": f"{PREFIX}-dept-{place_id}", "meta": META,
            "status": "active", "name": place_name, "mode": "instance",
        })
    return out


def patient_resources(p: Person, rng: random.Random) -> list[dict]:
    """Every resource for one patient: Patient, Encounter, NutritionOrder, allergies, flags."""
    patient = _ref("Patient", f"pat-{p.room}")
    encounter = _ref("Encounter", f"enc-{p.room}")
    born = date(TODAY.year - p.age, 1, 1) + timedelta(days=rng.randint(0, 270))  # birthday already passed
    admitted = _stamp(rng.randint(0, 8), rng.randint(0, 23), rng.choice([0, 10, 20, 30, 40, 50]))

    room_stay = {"location": {"reference": f"Location/{PREFIX}-room-{p.room}", "display": f"Room {p.room}"},
                 "status": "active"}
    stays = [room_stay]
    if p.off_unit_at:
        # The bed is held ("reserved") while the patient is somewhere else ("active").
        room_stay["status"] = "reserved"
        stays.append({"location": {"reference": f"Location/{PREFIX}-dept-{p.off_unit_at}",
                                   "display": dict(OFF_UNIT_PLACES)[p.off_unit_at]},
                      "status": "active"})

    diet = {"type": [{"coding": [{"system": f"{LOCAL}/diet", "code": p.diet, "display": DIETS[p.diet]}],
                      "text": DIETS[p.diet]}]}
    if p.diet in DIET_INSTRUCTION:
        diet["instruction"] = DIET_INSTRUCTION[p.diet]

    out = [
        {
            "resourceType": "Patient", "id": f"{PREFIX}-pat-{p.room}", "meta": META,
            "identifier": [{"system": "http://example.org/fhir/mrn", "value": f"T07-{p.room:06d}"}],
            "active": True,
            "name": [{"use": "official", "family": p.last, "given": [p.first]}],
            "gender": p.gender,
            "birthDate": born.isoformat(),
            "communication": [{
                "language": {"coding": [{"system": "urn:ietf:bcp:47", "code": p.language,
                                         "display": LANGUAGES[p.language]}],
                             "text": LANGUAGES[p.language]},
                "preferred": True}],
        },
        {
            "resourceType": "Encounter", "id": f"{PREFIX}-enc-{p.room}", "meta": META,
            "status": "in-progress",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                      "code": "IMP", "display": "inpatient encounter"},
            "subject": patient,
            "period": {"start": admitted},
            "location": stays,
        },
        {
            "resourceType": "NutritionOrder", "id": f"{PREFIX}-diet-{p.room}", "meta": META,
            "status": "active", "intent": "order",
            "patient": patient, "encounter": encounter,
            "dateTime": admitted,
            "oralDiet": diet,
        },
    ]
    allergies = [(name, "food") for name in p.food_allergies] + \
                [(name, "environment" if name == "Latex" else "medication") for name in p.other_allergies]
    for number, (name, category) in enumerate(allergies, start=1):
        out.append({
            "resourceType": "AllergyIntolerance", "id": f"{PREFIX}-alg-{p.room}-{number}", "meta": META,
            "clinicalStatus": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": "active"}]},
            "verificationStatus": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code": "confirmed"}]},
            "category": [category],
            "code": {"text": name},
            "patient": patient,
        })
    flags = []
    if p.fall_risk == "high":
        flags.append(("fall", "fall-risk-high", "High fall risk", "safety", "Safety"))
    if p.isolation != "none":
        flags.append(("iso", f"isolation-{p.isolation}", ISOLATION[p.isolation], "clinical", "Clinical"))
    for key, code, text, category, category_display in flags:
        out.append({
            "resourceType": "Flag", "id": f"{PREFIX}-flag-{p.room}-{key}", "meta": META,
            "status": "active",
            "category": [{"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                "code": category, "display": category_display}]}],
            "code": {"coding": [{"system": f"{LOCAL}/flag", "code": code, "display": text}], "text": text},
            "subject": patient, "encounter": encounter,
            "period": {"start": admitted},
        })
    return out


def build_bundle(people: list[Person] | None = None) -> dict:
    """A transaction Bundle. Each entry is a PUT, so loading it twice changes nothing."""
    people = build_people() if people is None else people
    rng = random.Random(SEED + 1)        # separate stream for dates, so editing a patient moves no one else
    resources = location_resources()
    for person in people:
        resources.extend(patient_resources(person, rng))
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [{"resource": r, "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}}
                  for r in resources],
    }


# ---------------------------------------------------------------------------
# Reading the bundle back. This is the logic app/ehr.py needs: it pulls out only
# the fields the routing rules use and nothing else.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Checks, files and the command line
# ---------------------------------------------------------------------------

def validate(bundle: dict, people: list[Person]) -> None:
    """Stop with a clear message if the data is not what the rest of the project expects."""
    resources = [e["resource"] for e in bundle["entry"]]
    ids = [f"{r['resourceType']}/{r['id']}" for r in resources]
    assert len(ids) == len(set(ids)), "duplicate resource id"
    known = set(ids)

    def references(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "reference":
                    yield value
                else:
                    yield from references(value)
        elif isinstance(node, list):
            for item in node:
                yield from references(item)

    for r in resources:
        assert r["meta"]["security"][0]["code"] == "HTEST", f"{r['id']} is not marked as test data"
        for ref in references(r):
            assert ref in known, f"{r['id']} points at {ref}, which is not in the bundle"

    contexts = contexts_from_bundle(bundle)
    rooms = [str(r) for r in all_rooms()]
    assert sorted(contexts) == rooms, "every room must have exactly one patient"
    assert len({c["name"] for c in contexts.values()}) == len(rooms), "two patients share a name"
    for p in people:                                  # what we wrote is what we read back
        c = contexts[str(p.room)]
        assert c == {
            "room": str(p.room), "name": f"{p.first} {p.last}", "language": p.language, "diet": p.diet,
            "allergies": p.food_allergies, "fall_risk": p.fall_risk, "isolation": p.isolation,
            "location": "off_unit" if p.off_unit_at else "in_room",
        }, f"room {p.room} does not read back as written"

    pinned = [contexts[str(p.room)] for p in PINNED]  # the demo set must cover every rule
    assert {c["diet"] for c in pinned} == set(DIETS), "pinned patients must cover every diet"
    assert sum(c["language"] != "en" for c in pinned) >= 2, "need two non-English pinned patients"
    assert sum(c["fall_risk"] == "high" for c in pinned) >= 2, "need two high fall risk pinned patients"
    assert any(c["isolation"] != "none" for c in pinned), "need a pinned patient in isolation"
    assert any(c["location"] == "off_unit" for c in pinned), "need a pinned patient off the unit"
    assert any(c["allergies"] for c in pinned), "need a pinned patient with a food allergy"


def bundle_text(bundle: dict) -> str:
    return json.dumps(bundle, indent=2, ensure_ascii=True) + "\n"


def summary_text(bundle: dict, people: list[Person]) -> str:
    contexts = contexts_from_bundle(bundle)
    unit_of = {room: name for _, name, rooms in UNITS for room in rooms}
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["room", "unit", "name", "age", "gender", "language", "diet", "food_allergies",
                     "other_allergies", "fall_risk", "isolation", "location", "pinned", "purpose"])
    for p in people:
        c = contexts[str(p.room)]
        place = dict(OFF_UNIT_PLACES)[p.off_unit_at] if p.off_unit_at else ""
        writer.writerow([c["room"], unit_of[p.room], c["name"], p.age, p.gender, c["language"], c["diet"],
                         "; ".join(c["allergies"]), "; ".join(p.other_allergies), c["fall_risk"],
                         c["isolation"], c["location"] + (f" ({place})" if place else ""),
                         "yes" if p.purpose else "", p.purpose])
    return buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default="data", help="where to write the two files (default: data)")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; fail if the files on disk differ from what this script makes")
    args = parser.parse_args(argv)

    people = build_people()
    bundle = build_bundle(people)
    validate(bundle, people)
    files = {"fhir_bundle.json": bundle_text(bundle), "patients_summary.csv": summary_text(bundle, people)}
    out_dir = Path(args.out_dir)

    if args.check:
        stale = [name for name, text in files.items()
                 if not (out_dir / name).exists() or (out_dir / name).read_text(encoding="utf-8") != text]
        if stale:
            print("Out of date: " + ", ".join(stale) + ". Run: python -m scripts.make_patients")
            return 1
        print("Patient files match the script.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    contexts = contexts_from_bundle(bundle).values()
    print(f"Wrote {len(people)} patients, {len(bundle['entry'])} resources, to {out_dir}/")
    for label, key in (("diet", "diet"), ("language", "language"), ("fall risk", "fall_risk"),
                       ("isolation", "isolation"), ("location", "location")):
        counts: dict[str, int] = {}
        for c in contexts:
            counts[c[key]] = counts.get(c[key], 0) + 1
        print(f"  {label}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    print(f"  food allergy: {sum(bool(c['allergies']) for c in contexts)} patients")
    return 0


if __name__ == "__main__":
    sys.exit(main())
