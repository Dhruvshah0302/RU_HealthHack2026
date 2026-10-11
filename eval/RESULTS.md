# Evaluation results

Run on Saturday 10 October 2026, in the testing AWS account, region us-east-1.

## Headline

On 66 held-out requests, the router with Claude Haiku 4.5 gave an urgent nurse alert for
24 of 25 urgent requests, sent every clinical request to a nurse, and kept all 34
non-clinical requests off the nurse's list. Keyword matching alone caught 13 of the same 25.

## Held-out half (66 requests). These are the numbers to report.

Brackets show the 95% confidence interval. With this few requests the intervals are wide,
so quote them alongside the counts.

| Measure | Claude Haiku 4.5 | Amazon Nova Lite | Keyword baseline |
|---|---|---|---|
| Urgent requests that got an urgent nurse alert | 24 of 25 (80% to 99%) | 22 of 25 (70% to 96%) | 13 of 25 (33% to 70%) |
| Clinical requests that reached a nurse at all | 32 of 32 (89% to 100%) | 32 of 32 (89% to 100%) | 31 of 32 (84% to 99%) |
| Non-clinical requests kept off the nurse's list | 34 of 34 (90% to 100%) | 33 of 34 (85% to 99%) | 25 of 34 (57% to 85%) |
| Non-urgent requests wrongly raised as urgent | 0 of 41 (0% to 9%) | 0 of 41 (0% to 9%) | 0 of 41 (0% to 9%) |
| Requests routed exactly as labeled | 64 of 66 (90% to 99%) | 61 of 66 (83% to 97%) | 42 of 66 (52% to 74%) |
| Time per request, median / 95th percentile | 1.13 s / 1.35 s | 0.92 s / 1.26 s | under 1 ms |
| Tokens per request, in / out | 1,350 / 104 | 1,052 / 59 | none |
| Model cost per 1,000 requests (see note) | about $1.50 | about $0.08 | none |
| Failed or unsure model answers | 0 | 0 | not applicable |

Cost note: prices used are $0.80 and $4.00 per million input and output tokens for Haiku 4.5,
and $0.06 and $0.24 for Nova Lite, taken from two third-party price trackers on 10 October 2026.
Check the AWS pricing page before quoting them. Speech to text and text to speech are extra.

## Decision

Claude Haiku 4.5 is the routing model. Nova Lite is the standby: it costs about a twentieth
as much and is slightly faster, but it marked three urgent requests as routine. At about a
sixth of a cent per request, model cost is not a reason to accept that.

## Every miss on the held-out half, Claude Haiku 4.5

| Request | Expected | Got | Comment |
|---|---|---|---|
| "I can't keep my eyes open since they gave me that shot." | Nurse, urgent | Nurse, routine | Possible reaction to a medicine. It reached the nurse, but not as urgent. This is the one missed urgent request. |
| "The machine next to me keeps beeping and the bag is empty." | Nurse, urgent | Nurse, urgent, plus Housekeeping | The nurse alert was right. The extra Housekeeping ticket was not needed: the prompt lists "noise from equipment" under room requests. |

No urgent request failed to reach a nurse on either half, with either model.

Nova Lite's three missed urgent requests were the one above, "My tongue feels thick and my
throat is itchy since the new medicine", and the beeping machine with the empty bag. All
three reached the nurse as routine.

## Tuning half (70 requests). Not for reporting.

The prompt and the rules were adjusted against this half, so its numbers flatter the system.
After tuning, Haiku 4.5 caught 26 of 26 urgent requests and routed 69 of 70 exactly as labeled.
The one difference: "The floor is wet and I almost slipped" came back urgent where the label
says routine. Whether a near-fall is urgent is a question for a clinician.

What the tuning changed:

- A red-flag rule for numbness matched the word "number". Fixed, along with five similar false alarms.
- A model that was unsure could lower an urgent answer to routine. The fallback can no longer lower anything.
- The prompt now sends slips and near-falls, and questions about going home or test results, to the nurse.
- One label was corrected: blood on the bedding expects the nurse plus Housekeeping, as the request catalog says.

## What this does not show

- The requests were written by the team, not collected from patients. Real speech will be messier.
- The requests are typed text. Errors from speech to text are not measured here.
- No clinician has reviewed the labels yet. See `for_clinician_review.md`.
- The rules that use the patient's record (diet, fall risk, isolation, location) are not covered yet.
- Each model was run once on each half, at temperature 0.
- The held-out half is only clean once. If the prompt is changed in response to the misses
  above, these numbers can no longer be called held-out, and new requests are needed.

## To reproduce

    python -m eval.run_eval --model us.anthropic.claude-haiku-4-5-20251001-v1:0 --split test
    python -m eval.run_eval --model us.amazon.nova-lite-v1:0 --split test
    python -m eval.run_eval --mode baseline --split test

Each run writes its per-request results to `eval/results_<model>_<split>.json`. Those files
are not committed.
