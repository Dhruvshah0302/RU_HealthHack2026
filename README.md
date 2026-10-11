# Call Bell Router

**Team: start with `PLAN.md`, then `SPEC.md`.** This README describes the starter as it runs today.

Starter for Ops Unleashed Challenge 2 (Rutgers Health Hack 2026). A patient types a request at the
bedside; the app sends non-clinical requests to the right support team and anything clinical or
uncertain to the nurse.

## What works today

- A bedside patient page (English and Spanish) with free text, six quick taps, and a nurse button
  that skips the sorter entirely.
- A live department dashboard with one lane per team. Tickets appear without a refresh.
- The routing policy and its safety rules, covered by 27 tests.
- A labeled test set of 136 patient requests and a script that scores the router against it.

## What is not done

- **The Bedrock model call has never been run against a real AWS account.** The code is in
  `app/llm.py` and its request and response handling are tested with a stand-in client. Expect to
  fix small things the first time you run it for real.
- Voice input and spoken replies (ElevenLabs) are not wired in.
- Tickets live in memory and are lost on restart. There are no logins.
- The test set labels and the red-flag rules were written by a non-clinician and need a
  clinician's review. See `eval/for_clinician_review.md`.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000/patient?room=412 on one screen and http://localhost:8000/dashboard on
another. With `BEDROCK_MODEL_ID` empty the app runs in offline mode: an English keyword matcher
stands in for the model. That is enough to click through the flow, not to demo.

A single team's screen: http://localhost:8000/dashboard?dept=food_services

## Turn on the model

1. Get your workshop AWS account and sign in from the terminal you run the app in.
2. In the Bedrock console, find a fast Claude model that is enabled for the account and copy its
   model ID or inference profile ID.
3. Put it in `.env` as `BEDROCK_MODEL_ID=...` and restart the app.
4. `curl localhost:8000/api/health` should report `"classifier": "llm"`.

If every request lands with the nurse marked "classifier failed", the model call is erroring. The
reason is printed in the server log.

## How a request is routed

1. Red-flag rules (`app/rules.py`) run first. They can only escalate to the nurse.
2. The classifier proposes one intent per need: the model in `app/llm.py`, or the keyword
   baseline in `app/baseline.py` when offline.
3. If the classifier fails, returns something unexpected, or reports low confidence, the request
   goes to the nurse. Nothing is dropped and nothing is guessed.
4. A request with several needs becomes several tickets, so "water, and my chest feels tight"
   alerts the nurse and still gets the water delivered.

The model only picks a category. The department is derived from the category in code
(`app/models.py`), so the model cannot invent a destination or mark a non-clinical request urgent.

## Measure it

```bash
python -m pytest                      # 27 tests, no network
python -m eval.run_eval --mode baseline
python -m eval.run_eval --mode llm    # once the model is on
```

The script prints urgent recall with a 95% interval, how many non-clinical requests stayed off the
nurse's list, and every urgent request that was missed.

Offline baseline, as shipped:

| | Result |
|---|---|
| Urgent requests that got an urgent alert | 23 of 51 (45%) |
| ... stated in medical words | 14 of 15 |
| ... stated in everyday words | 1 of 21 |
| Non-clinical requests kept off the nurse's list | 55 of 70 (79%) |

Keywords catch "chest pain" and miss "it feels like an elephant is sitting on my chest". Closing
that gap is the job of the model, and the comparison is the result to show the judges.

## Demo script

1. Dashboard on the big screen, patient page on a tablet or phone.
2. Tap **Pillow**. It appears under Housekeeping. The nurse lane stays empty.
3. Type "Can I get some water, and also my chest feels tight." The nurse lane turns red and Food
   Services gets the water.
4. Type an urgent request in everyday words, then one in another language.
5. Show the evaluation table: baseline against model.

## Layout

```
app/
  main.py        API, live updates, serves the two pages
  router.py      routing policy (read this first)
  rules.py       red-flag rules
  llm.py         Bedrock classifier
  baseline.py    keyword classifier for offline mode and as the eval floor
  models.py      departments, categories, ticket
  store.py       in-memory ticket store
  static/        patient.html, dashboard.html
eval/
  requests.jsonl            136 labeled requests
  run_eval.py               scoring script
  for_clinician_review.md   borderline labels to check with a clinician
tests/
SPEC.md          what we are building: decisions, rules, API contract, requirements
PLAN.md          who does what, in what order
```

## Known limits

- A food or drink request is not checked against the patient's diet order.
- Red-flag rules cover English and a little Spanish. Other languages rely on the model.
- All test requests are synthetic and were written by one person.
