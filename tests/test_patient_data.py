"""The synthetic patients: the files on disk match the generator, and the eight
pinned patients are exactly what the demo and the routing rules expect."""
import json
from pathlib import Path

from scripts import make_patients as mp

DATA = Path(__file__).resolve().parent.parent / "data"


def load():
    return json.loads((DATA / "fhir_bundle.json").read_text(encoding="utf-8"))


def test_files_on_disk_match_the_generator():
    people = mp.build_people()
    bundle = mp.build_bundle(people)
    assert (DATA / "fhir_bundle.json").read_text(encoding="utf-8") == mp.bundle_text(bundle)
    assert (DATA / "patients_summary.csv").read_text(encoding="utf-8") == mp.summary_text(bundle, people)


def test_generator_is_repeatable():
    assert mp.bundle_text(mp.build_bundle()) == mp.bundle_text(mp.build_bundle())


def test_bundle_passes_its_own_checks():
    mp.validate(load(), mp.build_people())


def test_sixty_patients_one_per_room():
    contexts = mp.contexts_from_bundle(load())
    assert len(contexts) == 60
    assert set(contexts) == {str(r) for r in list(range(401, 431)) + list(range(501, 531))}


def test_pinned_patients():
    c = mp.contexts_from_bundle(load())
    assert c["412"] == {"room": "412", "name": "Harold Whitaker", "language": "en", "diet": "regular",
                        "allergies": [], "fall_risk": "standard", "isolation": "none", "location": "in_room"}
    assert (c["414"]["language"], c["414"]["diet"]) == ("es", "npo")
    assert (c["415"]["diet"], c["415"]["allergies"], c["415"]["fall_risk"]) == ("diabetic", ["Peanut"], "high")
    assert (c["417"]["language"], c["417"]["diet"], c["417"]["fall_risk"]) == ("zh", "fluid_restricted", "high")
    assert (c["419"]["diet"], c["419"]["allergies"], c["419"]["isolation"]) == ("clear_liquids", ["Shellfish"], "contact")
    assert c["421"]["location"] == "off_unit"
    assert (c["423"]["language"], c["423"]["allergies"], c["423"]["isolation"]) == ("hi", ["Milk"], "droplet")
    assert (c["425"]["language"], c["425"]["diet"]) == ("en", "npo")


def test_only_food_allergies_are_returned():
    # Dorothy Okafor (415) is also allergic to penicillin. Food Services does not need that.
    assert mp.contexts_from_bundle(load())["415"]["allergies"] == ["Peanut"]


def test_context_has_only_the_agreed_fields():
    for context in mp.contexts_from_bundle(load()).values():
        assert set(context) == {"room", "name", "language", "diet", "allergies",
                                "fall_risk", "isolation", "location"}


def test_every_resource_is_marked_as_test_data():
    for entry in load()["entry"]:
        assert entry["resource"]["meta"]["security"][0]["code"] == "HTEST"
