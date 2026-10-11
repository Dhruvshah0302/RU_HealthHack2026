# Evaluation results

Run on Sunday 11 October 2026 against the code in this repository (the seven-team prompt), in
region us-east-1.

## Headline

On 66 held-out requests, the router gave an urgent nurse alert for all 25 urgent requests and
sent every clinical request to a nurse, with either model. With Claude Haiku 4.5 it kept all 34
non-clinical requests off the nurse's list; with Amazon Nova 2 Lite, 33 of 34. Keyword matching
alone caught 13 of the 25 urgent requests and kept 27 of 34 non-clinical requests off the nurse.

## Held-out half (66 requests)

Brackets show the 95% confidence interval. With this few requests the intervals are wide, so
quote them alongside the counts.

| Measure | Claude Haiku 4.5 | Amazon Nova 2 Lite | Keyword baseline |
|---|---|---|---|
| Urgent requests that got an urgent nurse alert | 25 of 25 (87% to 100%) | 25 of 25 (87% to 100%) | 13 of 25 (33% to 70%) |
| Clinical requests that reached a nurse at all | 32 of 32 (89% to 100%) | 32 of 32 (89% to 100%) | 31 of 32 (84% to 99%) |
| Non-clinical requests kept off the nurse's list | 34 of 34 (90% to 100%) | 33 of 34 (85% to 99%) | 27 of 34 (63% to 90%) |
| Non-urgent requests wrongly raised as urgent | 0 of 41 (0% to 9%) | 0 of 41 (0% to 9%) | 0 of 41 (0% to 9%) |
| Requests routed exactly as labeled | 63 of 66 (87% to 98%) | 58 of 66 (78% to 94%) | 44 of 66 (55% to 77%) |
| Failed or unsure model answers | 0 | 0 | not applicable |

Speed and size, Claude Haiku 4.5: 1.13 seconds median and 1.33 seconds at the 95th percentile
per request; about 1,530 tokens in and 104 out. At third-party list prices of $0.80 and $4.00
per million tokens (check the AWS pricing page before quoting), that is about $1.64 per 1,000
requests, or a sixth of a cent each. Speech to text and text to speech are extra.

Amazon Nova 2 Lite ran at a 0.7 second median on the previous version of the prompt. Its time on
this version was not kept.

## Which model

Both models met the safety bar on this half: no urgent request was missed and none failed to
reach a nurse. `deploy/DEPLOY.md` sets Nova 2 Lite, which is faster and is Amazon's own model.
Haiku 4.5 routed one more non-clinical request correctly and matched the labels more often. The
model is one setting (`BEDROCK_MODEL_ID`), so either can be used without a code change.

## Every difference from the labels, Claude Haiku 4.5

| Request | Label | Got | Comment |
|---|---|---|---|
| "The tablet at my bed is frozen." | Unit Clerk | Facilities | See the note below |
| "The TV is broken and I need a blanket." | Housekeeping and Unit Clerk | Housekeeping and Facilities | See the note below |
| "Can someone fix the TV? Also the IV in my arm really hurts." | Nurse (urgent) and Unit Clerk | Nurse (urgent) and Facilities | The urgent nurse alert was right |

Note: all three are the same thing. The labels were written when there were four teams and a
broken TV or tablet went to the Unit Clerk. The seven-team design sends broken equipment to
Facilities & Biomed (`frontend/DEPARTMENTS.md`). The model followed the new design; the labels
were left as they were so the comparison stays honest. None involves a clinical request going
astray.

## Every difference from the labels, Amazon Nova 2 Lite

Seven of its eight differences are the same broken TV, tablet or remote requests going to
Facilities. The eighth is a real miss: "The bed won't go up or down when I press the button" went
to the nurse as routine when it should have gone to Facilities. That is the one non-clinical
request that reached the nurse.

## How to read these numbers

- **The held-out half has been run more than once.** An earlier, four-team version of the prompt
  scored 24 of 25 urgent on it with Haiku 4.5; the request it marked routine was "I can't keep my
  eyes open since they gave me that shot." The prompt was then rewritten to add teams, not to fix
  that request, and the same half was run again. Treat these numbers as a strong check, not as a
  first-and-only look.
- The requests were written by the team, not collected from patients. Real speech will be messier.
- The requests are typed text. Errors from speech to text are not measured here.
- No clinician has reviewed the labels yet. See `for_clinician_review.md`.
- The set has no requests for Patient Advocacy or Case Management, so routing to those two teams
  is covered by tests only, not by this evaluation.
- The rules that use the patient's record (diet, fall risk, isolation, location) are covered by
  tests (`tests/test_policy.py`), not by this evaluation.
- Each model was run once on this half, at temperature 0.

## The other half (70 requests)

The prompt and the red-flag rules were adjusted against this half on Saturday, so its numbers
flatter the system and are not reported. What that tuning changed:

- A red-flag rule for numbness matched the word "number". Fixed, along with five similar false alarms.
- A model that was unsure could lower an urgent answer to routine. The fallback can no longer lower anything.
- The prompt now sends slips and near-falls, and questions about going home or test results, to the nurse.
- One label was corrected: blood on the bedding expects the nurse plus Housekeeping.

## To reproduce

    python -m eval.run_eval --model us.anthropic.claude-haiku-4-5-20251001-v1:0 --split test
    python -m eval.run_eval --model us.amazon.nova-2-lite-v1:0 --split test
    python -m eval.run_eval --mode baseline --split test

Each run writes its per-request results to `eval/results_<model>_<split>.json`. Those files
are not committed.
