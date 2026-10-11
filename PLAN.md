# Team plan

Team 07: Raghav, Dhruv, Jayesh, Ansh. What we are building is in `SPEC.md`. This file says who
does what and in what order.

Revised Saturday 3:15 PM. Two tasks of equal size changed hands: Raghav now builds the synthetic
patients and the EHR adapter (R2), and Dhruv gets the model working on Bedrock (D1). Hosting is in
Dhruv's AWS account and testing is in Ansh's. Earlier today: Jayesh builds a bell page with voice
instead of a TV screen, Raghav adds the request catalog and the priority levels, Ansh adds the
override buttons. The split is unchanged.

Work is split by effort points, 100 in total: Raghav 30, Dhruv 30, Jayesh 20, Ansh 20. Each
person owns one part of the product from start to finish, so each can demo it and speak for it.

The split assumes nothing about who is strongest at what. Swap tasks of equal points if it suits.

## Steps, in order

### Step 0. Set up (everyone, first hour)

1. Raghav creates the GitHub repository from this folder and adds the other three.
2. Everyone clones it, runs it offline (see `README.md`) and runs `python -m pytest`.
3. Raghav walks the team through `app/router.py` for 20 minutes. It is the whole safety argument.
4. Everyone reads `SPEC.md` and agrees the API contract in it. Changes after this go through the group chat.
5. AWS: the product lives in Dhruv's account. Lambda, DynamoDB and the public address are
   created there and nowhere else. Evaluation runs use Ansh's account, so a burst of test calls
   cannot slow the demo. Ansh runs them with Raghav. Nobody needs an AWS account to build their
   own part: the app runs on a laptop without one.
6. Nobody shares AWS keys in chat. The deployed app gets its access from its Lambda role, not from keys.
7. Everyone claims the ElevenLabs credit.

### Step 1. Build in parallel (Saturday afternoon and evening)

Each person works through their own table below, top to bottom. The first task in each table
unblocks someone else, so do it first.

### Step 2. Integrate and measure (Sunday morning)

1. Merge everything to `main`. Deploy. Open the bell page and the dashboard on two devices.
2. Run `python -m eval.run_eval --mode llm`. Read every missed urgent request. Fix the prompt, not the test set.
3. Walk the demo script end to end three times. Write down everything that breaks.

### Step 3. Freeze and rehearse (Sunday midday onward)

1. Feature freeze. Only fixes after this.
2. Record a screen capture of the demo as a backup in case the live one fails.
3. Rehearse the pitch twice with a timer. Each person answers one question outside their own part.
4. Submit.

## Who owns what

### Raghav: patient data, the routing rules, safety and evaluation (30)

| # | Task | Points | Files | Done when |
|---|---|---:|---|---|
| R1 | Create the repository, review and merge pull requests, keep `main` running | 3 | whole repo | The team can clone, run and merge |
| R2 | Synthetic patients and the EHR adapter. A script with a fixed seed writes 60 patients as FHIR resources, 8 of them pinned for the demo. The adapter reads them from the file, or from a FHIR server when `EHR_BASE_URL` is set. Do this first; three people need it | 6 | `scripts/make_patients.py` (new), `data/fhir_bundle.json`, `app/ehr.py` | `get_context("412")` returns only the fields listed in `SPEC.md`; the same test passes against the file and against a FHIR server |
| R3 | Request catalog, the four priority levels, and the patient-context rules | 10 | `data/catalog.json` (new), `app/rules.py`, `app/policy.py` (new), `app/router.py`, `tests/` | Team and level come from the catalog; every row of the rules table in `SPEC.md` has a passing test |
| R4 | Evaluation: add requests paired with a patient record, apply the mentor's label corrections, run the keyword baseline, Haiku and Sonnet on the same set (in Ansh's account); report accuracy, safety, time and cost per request. Keep Haiku unless Sonnet catches urgent requests that Haiku misses | 7 | `eval/` | One results table covers all four measures, with every miss explained and no Level 1 request given a lower level |
| R5 | Pitch: safety, accuracy and who decides what. Final end-to-end check before submission | 4 | slides | Can explain why a wrong model answer cannot hurt a patient |

### Dhruv: the model on Bedrock, ticket lifecycle and AWS (30)

| # | Task | Points | Files | Done when |
|---|---|---:|---|---|
| D1 | Get the model working on Bedrock: the smallest current Claude (Haiku), called through its `us.` inference profile. Remove identifiers from the text before the call. Record the tokens each request used. Raghav reviews, since he wrote `app/llm.py` | 6 | `app/llm.py`, `app/scrub.py` (new) | `/api/health` reports the model; a test fails if a name or record field reaches the model |
| D2 | Ticket lifecycle and queue: ordering by level then wait, overdue flag, patient not in room, try again, cancel, and the override endpoint (send to nurse, raise, lower by nurse only) | 8 | `app/store.py`, `app/main.py` | `GET /api/tickets` returns lanes in queue order; a "lower" from Housekeeping is refused |
| D3 | DynamoDB ticket store behind the same methods as the in-memory one | 5 | `app/store.py` | Tickets survive a restart |
| D4 | Hosting: Lambda with a function URL, dashboard on 2-second polling. Fallback: one laptop behind a tunnel | 7 | `deploy/` (new), `app/main.py` | One HTTPS address opens on a phone and a laptop at the same time |
| D5 | Pitch: architecture, where a hospital's nurse call system and health record would connect, and what data goes where | 4 | slides | Can draw the system from memory |

### Jayesh: the bell and the voice (20)

| # | Task | Points | Files | Done when |
|---|---|---:|---|---|
| J1 | Bell page: one large button, a listening state, stop on silence or after 10 seconds, second press goes to the nurse, confirmation shown, failure goes to the nurse | 6 | `app/static/bell.html` (new) | A full request can be made with one press and no reading |
| J2 | Voice: speech to text, spoken prompt and spoken confirmation in the patient's language, nothing understood goes to the nurse | 10 | `app/voice.py` (new), `app/static/bell.html` | A request spoken in Spanish lands in the right lane and the reply is spoken in Spanish; a silent press creates a nurse ticket |
| J3 | Pitch: the patient's journey. Drives the live demo | 4 | slides | Can run the demo without notes |

### Ansh: the staff dashboard, impact and the pitch (20)

| # | Task | Points | Files | Done when |
|---|---|---:|---|---|
| A1 | Dashboard: level shown on each ticket, lanes in queue order, each lane shows only the facts that team needs, buttons for Patient not in room, Try again, Send to nurse, Raise priority, overdue highlight, polling | 8 | `app/static/dashboard.html` | A housekeeper can tell the room is in isolation, cannot see the diet, and can send a ticket to the nurse |
| A2 | Impact and cost estimate: nursing hours and dollars returned per unit per day; cost to run per request (model from Raghav's numbers, voice from Jayesh's); no new hardware; every assumption stated with its source | 4 | `docs/impact.md` (new) | A cost-saved number and a cost-to-run number that survive the question "where does that come from?" |
| A3 | Slide deck, demo script, architecture diagram, README, submission form | 8 | `docs/`, `README.md` | Deck and backup recording are ready before the freeze |

### Totals

| Person | Points |
|---|---:|
| Raghav | 30 |
| Dhruv | 30 |
| Jayesh | 20 |
| Ansh | 20 |

## Who waits on whom

- Dhruv's D2 and Ansh's A1 need R2 for the record format. The fields are fixed in `SPEC.md`, so start in parallel and hard-code one patient until R2 lands.
- Raghav's R4 needs D1 (the model answering on Bedrock) before the model evaluation can run. The keyword baseline runs without it.
- Ansh's buttons need D2. Build them against the API contract and connect them when D2 merges.
- D2's ordering needs the `level` field from R3. Raghav adds the field to `app/models.py` first, as its own small pull request.
- Jayesh needs nothing from anyone to start. `POST /api/requests` already works.
- D4 changes the dashboard from a live socket to polling. Dhruv and Ansh do that change together.

## Working on GitHub

- Nobody pushes to `main`. Work on a branch named `yourname/what-it-does` and open a pull request.
- Keep pull requests small. One task from the tables above is one pull request.
- Someone who did not write it reviews it. Pick a reviewer from a different part of the product, so
  everyone reads code outside their own area.
- Run `python -m pytest` before you open the pull request. The same tests run on GitHub.
- Pull `main` before you start and again before you open the pull request.
- Stay in your own files where you can. `app/main.py` is shared, so tell Dhruv before you change it.
  Jayesh adds voice endpoints in `app/voice.py`, not in `main.py`.
- Never commit `.env`, AWS keys or the ElevenLabs key. Each person keeps their own `.env`.
- Never put a real person's name, record or voice in the repository. Synthetic patients and our own voices only.
- Say in the pull request if Kiro or another AI tool wrote the code, and read it before you ask for a review.

## Schedule

Times assume hacking ends Sunday around 6 PM. Confirm the submission deadline and move the freeze to four hours before it.

| When | What |
|---|---|
| Saturday by 2:30 PM | Step 0 done. Everyone has run the app |
| Saturday 6 PM | Check-in. R2 merged (patients). `level` field merged. D1 working (Bedrock). A press on the bell page creates a ticket from speech |
| Saturday 10 PM | Check-in. R3, D2, J1, A1 merged or in review |
| Sunday 9 AM | Integrate, deploy, run the evaluation |
| Sunday 12 PM | Feature freeze. Backup recording made |
| Sunday 1 PM to 3 PM | Rehearse twice. Submit |

If time runs short, cut in this order: the live FHIR server (keep the file), D3 (keep tickets in memory),
"Lower priority", the spoken prompt (keep the spoken confirmation), overdue flags, D4 (use the tunnel).
Do not cut R3, R4, J2 or the "Send to nurse" button.

## The pitch

| Order | Who | What |
|---|---|---|
| 1 | Ansh | The problem and the size of it: who answers a call bell today, what it costs, and what this returns |
| 2 | Jayesh | The patient's journey, live: press the bell and ask for a pillow, then a request in another language, then a silent press |
| 3 | Raghav | Safety: the patient who may not drink asks for water; urgent requests in everyday words; who decides what; the measured results |
| 4 | Dhruv | How it is built, what data goes where, where a hospital's systems connect, and what comes next |

## Questions for the mentors

- Does the bedside call bell unit at the host hospital have a speaker and a microphone? The design rests on this.
- Is the request catalog right? Which rows would a nurse move?
- Are the four levels and the time targets reasonable? Should a silent press be Level 1 or Level 2?
- Who would sign off the catalog and the rules in a real hospital?
- Do the patient-context rules match practice, above all the one for patients who may not eat or drink?
- What did "cost" and "time" mean: running cost and routing speed, or money and nurse time saved? We cover both until we know.

## Still to find out

- The submission deadline and the length of the pitch.
- From Aneri (AWS): how Bedrock handles prompts, which Claude models are enabled in the workshop accounts, and when the accounts are deleted. Record the backup demo before that.
- Whether the ElevenLabs credit covers speech to text as well as text to speech.
