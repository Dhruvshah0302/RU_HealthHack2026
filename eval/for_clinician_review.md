# Labels to check with a clinician

These are the test requests whose labels are a judgment call. The label shown is a first guess
by a non-clinician. Please correct it. The rest of the set is in `requests.jsonl`.

| ID | Patient says | Current label | Question |
|---|---|---|---|
| ui-12 | The machine next to me keeps beeping and the bag is empty. | Nurse (urgent) | IV pump alarm: nurse, but is it urgent? |
| nr-03 | I need help getting to the bathroom. | Nurse (routine) | fall risk: should this be urgent? |
| nr-10 | My bandage is coming loose, can someone re-tape it? | Nurse (routine) | Urgent or routine? |
| nr-11 | Can I get my blood sugar checked? | Nurse (routine) | Urgent or routine? |
| mx-05 | The floor is wet and I almost slipped. | Nurse (routine) + Housekeeping (routine) | Urgent or routine? |
| mx-08 | I need the bathroom cleaned, and I've been throwing up all morning. | Nurse (urgent) + Housekeeping (routine) | Urgent or routine? |
| mx-12 | My sheets are soaked with sweat and I feel feverish. | Nurse (urgent) + Housekeeping (routine) | Urgent or routine? |

## Wider questions

1. Which requests must always reach a nurse, even when they sound routine?
2. Food and drink: a patient may not be allowed to eat or drink. Should every dietary request be
   checked against the diet order before it reaches Food Services?
3. Which words do patients really use for serious symptoms that this set is missing?
4. Is the red-flag list in `app/rules.py` missing anything obvious, or flagging anything it should not?
