# Call Bell Router

Rutgers Health Hack 2026, Ops Unleashed track, Challenge 2 (AI Call Bell Router).

Team: Raghav Bajaj, Dhruv Shah, Jayesh Kasbe, Ansh Datir.

A patient presses one button at the bedside and says what they need, in their own words and
their own language. The system works out what was asked, checks it against the patient's record,
and sends each need to the team that handles it. Anything clinical, urgent or unclear goes to the
nurse. Everything else stays off the nurse's list.

## The problem

Every call bell press reaches a nurse today, whatever the reason. The challenge brief puts
non-clinical requests (a pillow, water, the TV) at 60 to 70 percent of activations. Each one
interrupts clinical work, and the patient who needs a nurse waits in the same queue as the
patient who needs a blanket.

## How a request is handled

1. The patient speaks or types at the bedside page. Speech is turned into text.
2. **Red-flag rules run first, in plain code.** Chest pain, trouble breathing, bleeding, a fall
   and similar phrases raise an urgent nurse alert without waiting for any model. The rules can
   only raise a request, never lower it.
3. **A language model on Amazon Bedrock sorts the words** into one need per team. It is forced to
   answer through a fixed structure, and it only picks a category. The team is looked up in code,
   so the model cannot invent a destination.
4. **If the model fails, answers oddly or is unsure, the request goes to the nurse.** Nothing is
   dropped and nothing is guessed. That is what a call bell does today.
5. **The patient's record is checked, in code.** A patient who may not eat or drink asks for
   water: the nurse is told and Food Services is not. A high fall risk patient asks for help to
   the bathroom: the nurse ticket becomes urgent. The model never sees the record.
6. Each team sees its own queue on the staff dashboard, live, with only the patient facts that
   team needs. Food Services sees diet and allergies. Housekeeping sees isolation precautions and
   never sees a diet.

One request can become several tickets. "A pillow, and my chest feels tight" alerts the nurse
and still gets the pillow delivered.

## What is different about it

- **The safety argument does not rest on the model.** Rules sit in front of it, a fallback sits
  behind it, and the record check runs after it. A wrong model answer can cost a nurse an
  interruption. It cannot hide an emergency or send water to a patient who must not drink.
- **It reads the patient's record.** Routing depends on diet orders, allergies, fall risk,
  isolation and whether the patient is on the unit, read from FHIR resources.
- **It is measured.** 136 labeled requests, half of them held out, scored with confidence
  intervals against a keyword baseline. Every miss is listed in `eval/RESULTS.md`.
- **No new hardware is assumed.** The design uses the call bell the patient already knows. The
  bedside page stands in for the bedside unit in this prototype.

## Architecture

```
 Bedside page (React)            Staff dashboard (React)
        |  voice or text                  ^  live tickets (WebSocket)
        v                                 |
 +--------------------------------------------------------------+
 |  FastAPI on Amazon EC2, behind Amazon CloudFront (HTTPS)     |
 |                                                              |
 |  1. red-flag rules        app/rules.py     (code)            |
 |  2. classifier            app/llm.py   --> Amazon Bedrock    |
 |  3. routing and fallback  app/router.py    (code)            |
 |  4. patient record rules  app/policy.py    (code)            |
 |          ^                                                   |
 |          |  app/ehr.py reads FHIR R4 resources               |
 |  5. tickets and queues    app/store.py                       |
 |  speech in and out        app/voice.py --> ElevenLabs        |
 +--------------------------------------------------------------+
```

| Part | Technology |
|---|---|
| Language model | Amazon Bedrock, Converse API with forced tool use. The model is one setting (`BEDROCK_MODEL_ID`). |
| Hosting | Amazon EC2 running the API and the built pages, Amazon CloudFront in front for HTTPS |
| Speech to text, text to speech | ElevenLabs, called from the server so the key never reaches the browser. The browser's own speech recognition is the fallback. |
| Patient data | FHIR R4 resources: Patient, Encounter, NutritionOrder, AllergyIntolerance, Flag. 60 synthetic patients. |
| Backend | Python, FastAPI, boto3 |
| Frontend | React, Vite |
| Tests | pytest, run on every push by GitHub Actions |

## Healthcare data

All patient data is synthetic. `scripts/make_patients.py` writes 60 inpatients on two units as
one FHIR R4 Bundle (`data/fhir_bundle.json`), with a fixed seed so the file is reproducible.
`app/ehr.py` reads the bundle and returns only the eight fields the routing rules need. A
hospital's FHIR server returns the same resource shapes, so the reader is the only part that
changes. See `data/README.md`.

## Results

On 66 held-out requests (95% confidence intervals in brackets):

| Measure | Claude Haiku 4.5 | Amazon Nova 2 Lite | Keyword baseline |
|---|---|---|---|
| Urgent requests that got an urgent nurse alert | 25 of 25 (87% to 100%) | 25 of 25 (87% to 100%) | 13 of 25 (33% to 70%) |
| Clinical requests that reached a nurse | 32 of 32 | 32 of 32 | 31 of 32 |
| Non-clinical requests kept off the nurse's list | 34 of 34 (90% to 100%) | 33 of 34 (85% to 99%) | 27 of 34 (63% to 90%) |
| Non-urgent requests wrongly raised as urgent | 0 of 41 | 0 of 41 | 0 of 41 |

About one second and a sixth of a cent of model cost per request with Haiku 4.5. The method,
every difference from the labels, and what these numbers do not show are in `eval/RESULTS.md`.

## Run it on your own machine

Needs Python 3.11 or newer and Node.js 18 or newer.

```bash
git clone https://github.com/Dhruvshah0302/RU_HealthHack2026.git
cd RU_HealthHack2026

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cd frontend && npm install && npm run build && cd ..

cp .env.example .env          # then fill it in, see below
uvicorn app.main:app --reload
```

Open http://localhost:8000/patient?room=412 for the bedside page and
http://localhost:8000/dashboard for the staff screens. Use Chrome for the microphone.

Settings in `.env`:

| Setting | Purpose |
|---|---|
| `BEDROCK_MODEL_ID` | The Bedrock model or inference profile, for example `us.amazon.nova-2-lite-v1:0`. Empty runs an offline keyword sorter, which is enough to click through but is not the product. |
| `AWS_REGION` | The region of your Bedrock access |
| AWS credentials | Sign in to AWS in the same terminal, or set `AWS_BEARER_TOKEN_BEDROCK` to a Bedrock API key |
| `ELEVENLABS_API_KEY` | Speech to text and spoken replies. Without it the page uses the browser's speech recognition. |

`http://localhost:8000/api/health` reports `"classifier": "llm"` when the model is on.

Rooms to try (all patients are fictional, see `data/README.md`):

| Room | Patient | Try | What should happen |
|---|---|---|---|
| 412 | Regular diet | "Can I get a pillow and some water?" | One ticket for Housekeeping, one for Food & Nutrition, none for Clinical |
| 425 | May not eat or drink | "I'm thirsty, can I get some water?" | Clinical is told. Food & Nutrition gets nothing. |
| 415 | Diabetic, peanut allergy | "Could I have a snack?" | Food & Nutrition, with the diet and the allergy on the ticket |
| 419 | Contact isolation | "Can I get an extra pillow?" | Housekeeping, with the isolation precaution on the ticket |
| 417 | High fall risk | "I need help getting to the bathroom" | Clinical, urgent |
| 414 | Speaks Spanish (add `&lang=es`) | A request in Spanish | Routed the same way, summarised in English for staff |

## Deploy it

`deploy/DEPLOY.md` has the full steps. In short:

1. Launch one Amazon Linux 2023 EC2 instance with `deploy/ec2-user-data.sh` as its user data.
   It installs the app, builds the pages and starts the service on port 80.
2. Put the settings above into `/opt/callbell/src/.env` on the server and restart the service.
3. Create a CloudFront distribution with the instance as its origin, to get an HTTPS address.
   Browsers only allow the microphone over HTTPS.
4. After a new push, run `sudo bash /opt/callbell/src/deploy/update.sh` on the server.

## Tests and evaluation

```bash
python -m pytest                                   # 114 tests, no network needed
python -m eval.run_eval --mode baseline            # keyword baseline
python -m eval.run_eval --model <bedrock-model-id> --split test
```

## Where things are

```
app/
  main.py       API, live updates, serves the built pages
  rules.py      red-flag rules
  llm.py        Bedrock classifier (prompt and structured output)
  router.py     routing and the nurse fallback
  ehr.py        reads the patient's facts from FHIR resources
  policy.py     patient record rules
  teams.py      the seven teams
  voice.py      ElevenLabs speech to text and text to speech
  store.py      tickets
  baseline.py   keyword sorter: offline mode and the evaluation floor
frontend/       React app: bedside page and staff dashboard
data/           synthetic patients (FHIR R4) and how they were made
eval/           labeled requests, scoring script, results
tests/          automated tests
deploy/         EC2 and CloudFront setup
SPEC.md         the design: who decides what, privacy, patient rules
```

## Limits

This is a prototype built in a weekend. It is not ready for patients.

- The clinical rules, the labels and the time targets were written by engineers. A hospital
  would set its own, and no clinician has reviewed ours yet (`eval/for_clinician_review.md`).
- The evaluation uses typed requests written by the team. Errors from speech to text and the way
  real patients speak are not measured.
- Tickets are held in memory and are lost on a restart. There are no staff logins.
- Speech is sent to ElevenLabs. With real patients that needs a signed agreement with the
  vendor, or a speech service inside the hospital's own cloud account.
- The request text goes to the model as the patient said it. Removing names and other
  identifiers before that call is designed (`SPEC.md`) but not built.
- The patient record is a file of synthetic FHIR resources, not a live hospital system.
- Admission, discharge and the record itself stay with the hospital's existing staff and
  systems. This app only reads.
