# Synthetic patients

Everything in this folder is invented. No real patient information was used.

| File | What it is |
|---|---|
| `fhir_bundle.json` | 60 inpatients as FHIR R4 resources, in one transaction Bundle. The app reads this. |
| `patients_summary.csv` | The same patients, one row each, for people to read. |

Both files are written by `scripts/make_patients.py`. Do not edit them by hand. Change the script, then run:

    python -m scripts.make_patients

`python -m scripts.make_patients --check` fails if the files and the script disagree. The tests check this too.

## What is in it

- Two units of 30 single rooms: 4 West (401 to 430) and 5 West (501 to 530). Every room has one patient.
- For each patient: `Patient`, `Encounter`, `NutritionOrder`, and where they apply `AllergyIntolerance` and `Flag`.
- 66 `Location` resources: the rooms, the two units, and four places a patient can be when off the unit.
- Every resource carries HL7's test-data marker (`HTEST`) and the tag `team07-call-bell-router`.

## The eight pinned patients

Written by hand in `PINNED`. The demo, the tests and the evaluation use only these.

| Room | Name | Language | Diet | Food allergy | Fall risk | Isolation | Where | Why |
|---|---|---|---|---|---|---|---|---|
| 412 | Harold Whitaker | English | regular | none | standard | none | in room | Baseline |
| 414 | Rosa Delgado | Spanish | nothing by mouth | none | standard | none | in room | Asks for water in Spanish: the nurse is told |
| 415 | Dorothy Okafor | English | diabetic | peanut | high | none | in room | Diet and allergy on a food ticket; bathroom help becomes Level 2 |
| 417 | Lian Zhou | Chinese | fluid restricted | none | high | none | in room | Fluid restriction on a drink ticket |
| 419 | Marcus Bell | English | clear liquids | shellfish | standard | contact | in room | Isolation on any ticket that sends someone in |
| 421 | Priya Nair | English | regular | none | standard | none | Radiology | Request waits for the patient |
| 423 | Ramesh Kulkarni | Hindi | regular | milk | standard | droplet | in room | Third language, droplet isolation |
| 425 | Daniel Reyes | English | nothing by mouth | none | standard | none | in room | The live demo: "I'm thirsty, can I get some water?" |

## The other 52

Drawn at random with a fixed seed, so everyone gets the same file. The odds are in the script
under "How the 52 random patients are drawn". They are our assumptions, not hospital figures:
do not quote the resulting counts as real-world rates. Names are drawn without regard to language.

## How each fact is stored

| Fact | Where to read it |
|---|---|
| Room | `Encounter.location`, the entry that points at a `Room` location |
| In the room or off the unit | That entry's `status`: `active` is in the room, `reserved` is off the unit |
| Language | `Patient.communication[0].language.coding[0].code` |
| Diet | `NutritionOrder.oralDiet.type[0].coding[0].code`, for the order with status `active` |
| Food allergies | `AllergyIntolerance.code.text`, where `category` contains `food` |
| Fall risk | A `Flag` with code `fall-risk-high`. No flag means standard. |
| Isolation | A `Flag` with code `isolation-contact` or `isolation-droplet`. No flag means none. |

`contexts_from_bundle()` in the script reads all of this and returns only the eight fields the
routing rules need. `app/ehr.py` can reuse it.

## Limits

- Diet and flag codes are our own (`http://example.org/fhir/CodeSystem/...`). A hospital would use standard codes such as SNOMED CT.
- Every resource was checked against the FHIR R4B models for structure. The bundle has not yet been loaded into a FHIR server.

## Loading it into a FHIR server

With HAPI FHIR running in Docker:

    curl -X POST -H "Content-Type: application/fhir+json" \
         --data-binary @data/fhir_bundle.json http://localhost:8080/fhir

Each entry is a PUT with a fixed id, so loading it twice changes nothing.
