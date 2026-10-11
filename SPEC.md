# Call Bell Router: what we are building

Revised Saturday 3:15 PM after the second round of mentor feedback. Source: Ops Unleashed
Challenge 2 brief. Use only synthetic data. No real patient information.

The clinical content below (request catalog, priority levels, red flags, patient rules, time
targets) is our proposal. In a hospital it is set by the hospital, not by us and not by the
model. Confirm it with a clinician mentor before the pitch.

## What changed in this revision

| Mentor feedback | Decision |
|---|---|
| A TV browser takes too long to reach; patients will fall back to the bell | The bell is the interface. The patient presses the call bell they already use and says what they need. No TV, no browser, no app. |
| Keep track of what is clinical and what is not | A request catalog: a file the hospital owns that lists request types, marks each clinical or non-clinical, and names the team and the priority level. |
| AI cannot make every decision | The model only works out what was asked. Everything else is decided by the hospital's written rules or by a person. See "Who decides what". |
| Severity and a priority queue | Four priority levels. Each lane is ordered by level, then by waiting time. |
| Sensitive patient data must not go to an LLM | The model receives the words of the request with identifiers removed, and nothing else. It never receives the record. See "What data goes where". |
| Can we use EHR APIs | Patient facts come through an adapter that reads FHIR resources. In the demo the resources are synthetic and sit in a file. |

Still standing from the first session: no new hardware, staff can close a ticket as "patient not
in room", every request is checked against the patient's record, synthetic patients, web app.

## The patient interface

| Option | Verdict |
|---|---|
| Room TV with a browser | Dropped. Too many steps for someone in bed. It only works where the hospital's TV system can put a tile on its home screen, which is a vendor integration we cannot build or show. |
| Tablet | Dropped in the first session. Cost. |
| Patient's own phone | Not the main route. The text page stays for patients who cannot speak and for family members. No more work goes into it. |
| A new voice device at each bed (smart speaker, Meta's Muse Charm) | Not needed where the bell has a microphone. A plain speaker and microphone unit is the fallback where it does not, at a fraction of a tablet's cost. Muse Charm is ruled out: announced in September 2026 with no price, release date or developer access made public yet, and it is a personal device built around one person's own AI agent. |
| Call bell plus voice | Chosen. One press, same as today. Nothing to learn and nothing to find. |

How it behaves:

1. The patient presses the call bell. A short tone plays, then "How can we help?" in the patient's language.
2. The patient says what they need. Listening stops after 2 seconds of silence or 10 seconds in total.
3. The patient hears which team has the request.
4. If nothing is understood, the press goes to the nurse, exactly as a call bell does today.
5. A second press while the system is listening, or the word "nurse", goes straight to the nurse.

Assumption to check with a mentor: many nurse call systems already have a speaker and a
microphone at the bed, used to talk to the nurses' station. We assume the host hospital's does.
If it does not, the bedside phone on a short extension is the next route.

In the demo, `app/static/bell.html` is one large button, and the laptop microphone and speaker
stand in for the bedside unit.

## The flow

1. Bell press. The room is known from the device, never from what the patient says.
2. Speech becomes text.
3. Red-flag rules check the text, in code. They can only raise a request, never lower it.
4. Identifiers are removed from the text. The model matches what is left to entries in the request catalog.
5. Code looks up the team and the level from the catalog.
6. Code reads the patient's facts through the EHR adapter and applies the patient-context rules.
7. Tickets join the queues. The patient hears a confirmation.
8. Staff press On it, then Done. They can also send a ticket to the nurse or raise its level.

## Who decides what

| Decision | Who decides | How the product enforces it |
|---|---|---|
| What counts as clinical, which team handles each request type, the levels, the red-flag list, the time targets, the patient rules | The hospital: nursing leadership, with patient safety and the privacy officer signing off | These live in files (`data/catalog.json`, `app/rules.py`, `app/policy.py`). They change by review, not by the model learning. |
| What the patient asked for | The model | It matches speech to catalog entries and returns structured data. It cannot choose a team or a level for a catalogued request. |
| Whether a request is dangerous | Written rules first, then the nurse | Red flags are plain code. The model can raise a request but cannot lower one. |
| Anything about care: may this patient drink, is this symptom serious, is pain medicine due | The nurse | Every clinical request goes to the nurse. The system never answers a clinical question or tells a patient what to do. |
| Whether the routing was right | Staff on the floor | Any team can press "Send to nurse" or "Raise priority". Only the nurse can lower a level. |
| Whether a request is still needed | The patient | They can cancel a non-clinical request. |

When the system is unsure, it does what a call bell does today: it sends the request to the nurse.

## Request catalog

`data/catalog.json`. Each entry has an id, a label, clinical yes or no, a team, a default level
and a few example phrases. Starting list:

| Request type | Clinical | Team | Default level |
|---|---|---|---|
| Pillow, blanket, linens, towels, gown | no | Housekeeping and Facilities | 4 |
| Room cleaning, trash, bathroom supplies | no | Housekeeping and Facilities | 4 |
| Room temperature, lights, noise, broken bed control or furniture | no | Housekeeping and Facilities | 4 |
| Meal, snack, menu, missing or wrong tray, utensils | no | Food Services | 4 |
| Water, juice, coffee, ice | no, but checked against the diet order | Food Services | 4 |
| TV, remote, Wi-Fi, phone, charger | no | Unit Clerk and IT | 4 |
| Interpreter, visitor or parking information, paperwork | no | Unit Clerk and IT | 4 |
| Other non-clinical request | no | Unit Clerk and IT | 4 |
| Pain or pain medicine | yes | Nurse | 3 |
| Any question about medicine, tests, the doctor or going home | yes | Nurse | 3 |
| Help to the bathroom, getting up, changing position | yes | Nurse | 3 |
| IV, pump, monitor, oxygen or dressing | yes | Nurse | 3 |
| "Am I allowed to eat or drink?" | yes | Nurse | 3 |
| Spill of blood, vomit or urine | yes | Nurse, plus Housekeeping | 3 |
| New or worsening symptom | yes | Nurse | 2 |
| Asks for the nurse and gives no reason | yes | Nurse | 2 |
| Anything that matches no entry and may be clinical | yes | Nurse | 2 |

The model adds a `request_type` (a catalog id, or `other`) to each intent. For a catalogued type
the team and level come from the file. For `other`, the existing category mapping applies.

## Priority levels and the queue

| Level | Name | Set by | Target to "On it" |
|---|---|---|---|
| 1 | Emergency | A life-threatening red flag: chest pain, trouble breathing, bleeding, a fall, fainting, stroke signs, seizure, choking, allergic reaction, self-harm, the word "emergency" | At once. Alerts again every minute and shows on the charge nurse view. |
| 2 | Urgent | Other red flags (severe pain, dizziness, racing heart, confusion, IV problem, vomiting); a new or worsening symptom; bell pressed and nothing understood; patient asks for the nurse; the model failed or was unsure; a high fall risk patient asking to get up | 2 minutes |
| 3 | Routine clinical | Catalog entries marked clinical | 10 minutes |
| 4 | Non-clinical | Catalog entries marked non-clinical | 15 minutes |

The targets are placeholders. A hospital sets its own.

- Each lane is ordered by level, then longest wait first.
- A ticket past its target is marked overdue. Levels 1 to 3 go to the charge nurse. Level 4 goes to the unit clerk, so a late pillow still does not reach the nurse.
- Waiting never lowers a level. Only the nurse can lower one, and only by hand.
- Each rule in `app/rules.py` gains a level (1 or 2).
- `priority` stays in the data so the existing tests and evaluation keep working: levels 1 and 2 are `urgent`, levels 3 and 4 are `routine`.

## What data goes where

| Data | Where it goes |
|---|---|
| The patient's record (name, diet, allergies, fall risk, isolation, location) | Never to a model. Code reads it through the EHR adapter and takes only the fields the rules need. |
| The words of the request | To Claude on Amazon Bedrock, after names, room numbers, phone numbers and dates are removed. No name, room or record is attached. |
| The red-flag check | Runs in our own code before any model call. An emergency never depends on a model. |
| The voice recording | To speech to text. In the demo this is ElevenLabs with our own voices. In a hospital it needs a signed agreement with the vendor, or a speech service inside the hospital's own AWS account. |
| The spoken confirmation | Generic text such as "Housekeeping has your request." No name and no health detail. |
| Each lane on the dashboard | Shows only the facts that team needs: Food Services sees diet and allergies, Housekeeping sees isolation, the nurse sees all of them. |

To say plainly in the pitch: the request itself can contain health information ("my chest hurts").
That is unavoidable. What we control is that it travels with nothing that identifies the patient.

To confirm before the pitch: ask Aneri (AWS) how Bedrock handles prompts, and whether the
workshop accounts would be covered under a hospital's agreement with AWS. Do not state a
compliance claim we have not checked.

## Patient facts and the EHR adapter

Hospitals expose patient data through FHIR, the standard API for health records. We read the
same shapes a real system returns, so the adapter could later point at a hospital's FHIR server.

| Fact the rules need | FHIR R4 resource |
|---|---|
| Preferred language | `Patient.communication.language` |
| Room, and whether the patient is on the unit | `Encounter.location` |
| Diet order, nothing by mouth, fluid restriction | `NutritionOrder.oralDiet` |
| Allergies | `AllergyIntolerance` |
| Fall risk, isolation precaution | `Flag` |

Where each fact lives varies by hospital and vendor. Treat this mapping as a starting point.

- `scripts/make_patients.py`: writes 60 synthetic patients (two 30-bed units, rooms 401 to 430 and 501 to 530) with a fixed seed, so everyone gets the same file.
- `data/fhir_bundle.json`: the output, one FHIR transaction Bundle. The same file can be posted to any FHIR server as it is.
- Eight patients are pinned by hand in known rooms. The demo, the tests and the evaluation use only these. The other 52 make the unit look real and let us count how often each rule fires.
- The pinned eight cover every diet value (regular, npo, clear_liquids, diabetic, fluid_restricted), two non-English speakers, two high fall risk patients, one in isolation and one off the unit.
- Every resource carries the HL7 test-data tag (`HTEST`), and every name comes from a fixed fictional list.
- `app/ehr.py`: `get_context(room)` returns only `language, diet, allergies, fall_risk, isolation, location`, plus `name` for the staff dashboard. Nothing else leaves the adapter.
- Built: the file source. Not built yet: a second source that reads the same resources from a FHIR server when `EHR_BASE_URL` is set, with a 2-second limit. HAPI FHIR is the free choice: in Docker for development, or the public test server for the hosted demo.
- Code does the fetching. The model has no tool that can read a record.
- If the record cannot be read, the system does not guess. A food or drink request goes to the nurse.

## Patient-context rules

These run in code after the model, in `app/policy.py`. The model never sees the record.

| Patient record | Request | What happens |
|---|---|---|
| diet is npo | food or drink | Nothing goes to Food Services. The nurse gets a Level 3 ticket: "Patient is not allowed food or drink and asked for water." The patient hears that their nurse will come and talk with them. |
| diet is clear_liquids, diabetic or fluid_restricted | food or drink | Goes to Food Services with the diet shown on the ticket. |
| allergies present | food | Goes to Food Services with the allergies shown on the ticket. |
| fall_risk is high | help to the bathroom, getting up, walking | The nurse ticket becomes Level 2. |
| isolation is contact or droplet | any request that sends someone into the room | The ticket shows the precaution. |
| location is off_unit | non-clinical request | The ticket is created as "waiting for patient". |
| record cannot be read, or no active diet order | food or drink | Nothing goes to Food Services. The nurse gets a Level 3 ticket saying the diet could not be checked. |
| language | any | The prompt and the spoken confirmation use it. |

A rule may send a request to the nurse, raise a level, or add information to a ticket. A rule
never removes a nurse ticket and never lowers a level.

## Ticket lifecycle

| Status | Set by | Meaning |
|---|---|---|
| open | system | Created, nobody has it yet |
| acknowledged | staff, "On it" | Someone is handling it |
| done | staff, "Done" | Completed |
| waiting_for_patient | staff, "Patient not in room", or the off-unit rule | Could not be delivered. The nurse gets a Level 3 note naming the room and the time. Staff can press "Try again". |
| cancelled | patient | The patient no longer needs it. Non-clinical tickets only. |

## API contract

Agree on this first so the screens and the backend can be built at the same time.

| Method and path | Purpose | State |
|---|---|---|
| `GET /api/patients/{room}` | Returns `{room, language}` for the bell page. Nothing else. | built |
| `POST /api/requests` `{room, text, direct_nurse, source}` | Create tickets. `source` is `voice` or `text`. Empty text from voice creates a Level 2 nurse ticket. | built with patient context; needs levels and `source` |
| `POST /api/transcribe` (audio file) | Returns `{text, language}` | to build |
| `POST /api/speak` `{text, language}` | Returns audio of the confirmation | to build |
| `GET /api/tickets` | Open tickets, already ordered by level then wait, and counters. The dashboard polls every 2 seconds. | built, needs ordering |
| `POST /api/tickets/{id}/status` `{status, note}` | Staff update | built for acknowledged and done |
| `POST /api/tickets/{id}/override` `{action, by}` | `action` is `send_to_nurse`, `raise` or `lower`. `lower` is refused unless `by` is `nurse`. | to build |
| `POST /api/tickets/{id}/cancel` | Patient cancels a non-clinical ticket | to build |

Each ticket carries `patient_name` and `notes`: the patient facts that team needs and no
others (built). The response also gives `patient_language` and `patient_note` for the bedside
page (built). Still to add to each ticket: `level` (1 to 4), `request_type`, `overdue`.

## Requirements

### Bell page
- B1. One control. A press starts listening. No menus.
- B2. Listening stops after 2 seconds of silence or 10 seconds in total.
- B3. A second press while listening, or the word "nurse", creates a Level 2 nurse ticket without the model.
- B4. Nothing understood creates a Level 2 nurse ticket.
- B5. After a request the page says and shows which team has it.
- B6. If anything fails, the press goes to the nurse.

### Voice
- V1. The request can be in any language the transcription supports.
- V2. The confirmation is spoken in the language the patient used, or the language on their record.
- V3. The confirmation never includes a name or a health detail.

### Routing and safety
- S1. One ticket per team involved. (built)
- S2. Any clinical content yields a nurse ticket. (built)
- S3. Red-flag rules run before the model and can only raise a request. (built; add levels)
- S4. A model error, an unexpected answer or low confidence sends the request to the nurse at Level 2. (built; add level)
- S5. The model returns structured data only. Team and level come from the catalog in code.
- S6. Every ticket records why it was routed where it was. (built)
- S7. The patient-context rules run after the model and can only raise or redirect to the nurse.

### Privacy
- P1. The model call contains the request text only. No name, room, or record.
- P2. Names, room numbers, phone numbers and dates are removed from the text before the model call.
- P3. The record is read only through `app/ehr.py`, which returns only the listed fields. The model has no tool that can read it.
- P4. Only synthetic patients and our own voices are used.
- P5. A test fails if a patient name or record field appears in the text sent to the model.

### Staff dashboard
- D1. One lane per team, ordered by level then wait. Levels 1 and 2 are visually distinct.
- D2. Each lane shows only the patient facts that team needs.
- D3. Staff can press On it, Done, Patient not in room, Send to nurse, Raise priority. The nurse lane also has Lower priority.
- D4. Overdue tickets stand out.

### Hosting
- H1. One public HTTPS address for the bell page and the dashboard. The microphone only works over HTTPS.
- H2. Tickets survive a restart (DynamoDB).

### Evaluation
- E1. The labeled set covers every team, urgent requests in medical and in everyday words, routine clinical requests, mixed requests, figures of speech and several languages. (built, 136)
- E2. The set adds requests paired with a patient record, for every patient-context rule.
- E3. One command reports urgent recall with a confidence interval, the share of non-clinical requests kept off the nurse's list, and every missed urgent request. (built)
- E4. A clinician has reviewed the labels, the catalog, the red-flag rules and the patient-context rules.
- E5. The same command reports routing accuracy, time per request, and model tokens and cost per request.
- E6. The same command reports how many Level 1 requests were given a lower level. The target is zero.

## How we are judged

| Criterion | What we show |
|---|---|
| Safety and accuracy | Measured urgent recall, keyword baseline against the model, with every miss listed; who decides what; the patient-context rules and their tests |
| Web app execution | Live bell page and a matching team routing log |
| Operational impact | Estimate of nursing hours returned, with the assumptions stated |
| Live demo | A spoken pillow request lands with Housekeeping and never reaches the nurse; a patient who may not drink asks for water and the nurse is told instead; a silent press goes to the nurse |

### The four measures a mentor named

A mentor told us the product will be judged on accuracy, cost, safety and time. "Cost" and
"time" can each mean two things, so we show both.

| Measure | What we show | Where it comes from |
|---|---|---|
| Accuracy | Share of requests routed exactly as labeled, keyword baseline against the model | `eval/run_eval.py` |
| Safety | Share of urgent requests that got an urgent nurse alert, with every miss listed; no Level 1 request given a lower level; a wrong model answer falls back to the nurse; the model never sees the record | `eval/run_eval.py`, `app/router.py`, `app/policy.py` |
| Cost to run | Cost per request: model tokens plus speech to text and text to speech; no new hardware and no new screen | token counts recorded in `app/llm.py`, vendor price lists |
| Cost saved | Nursing hours returned per unit per day, in dollars, with every assumption stated | `docs/impact.md` |
| Time to route | Median and 95th percentile seconds from the end of speech to a ticket | `eval/run_eval.py`, timed spoken requests |
| Time saved | Minutes of nurse time per request avoided, and how long tickets wait before "On it" against the targets | `docs/impact.md`, dashboard timers |

## Not building

- Integration with a real nurse call system or a hospital's live health record. The adapter shows where each would connect.
- A TV screen.
- Staff logins. The dashboard trusts the lane it was opened in. A hospital would use its own sign-on.
- Handling of device alarms. The brief mentions them; this covers patient requests only.
- A native phone app.
