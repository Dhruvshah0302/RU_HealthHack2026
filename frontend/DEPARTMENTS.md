# Teams and department codes (proposal for the backend)

The staff dashboard (`/dashboard`) has one screen per team, seven in all, each in its own colour. Clinical requests all go to one Clinical team
(nursing answers and brings in the physician, respiratory therapy, pharmacy or PT/OT as needed).
Every other request goes to the support team that does that work.

| Team | Code to send | Code the backend sends today | Covers |
|---|---|---|---|
| Clinical | `nurse` | `nurse` | Pain, symptoms, medication, bathroom help, breathing, oxygen, anything clinical or unclear |
| Unit Clerk | `unit_clerk` | `unit_clerk_it` | Desk triage, phone, visitors, Wi-Fi and TV account help |
| Environmental Services | `environmental_services` | `housekeeping_facilities` | Cleaning, spills, trash, fresh linens |
| Food & Nutrition | `food_services` | `food_services` | Meals, snacks, drinks, dietary questions |
| Facilities & Biomed | `facilities_biomed` | (part of `housekeeping_facilities`) | Room temperature, broken TV or bed, equipment faults |
| Patient Advocacy | `patient_advocacy` | (none, goes to nurse) | Complaints, interpreters, patient rights |
| Case Management | `case_management` | (none, goes to nurse) | Insurance, post-discharge care, home equipment, social work |

The dashboard already accepts both columns, so nothing breaks while the backend changes:
`unit_clerk_it` shows under Unit Clerk and `housekeeping_facilities` under Environmental Services.
A code it does not know is never dropped: the ticket appears on the Clinical screen with a note
naming the unknown code (the same safe default the routing uses).

## What the backend would change (backend team's call)

- `app/models.py`: add the three new departments and their categories to `DEPARTMENTS` and
  `CATEGORY_TO_DEPARTMENT` (for example `facilities`, `advocacy`, `case_management`), and split
  `housekeeping_facilities` into `environmental_services` and `facilities_biomed`.
- The model prompt (`app/llm.py`) and the keyword baseline (`app/baseline.py`): teach the new categories.
- `eval/requests.jsonl`: label examples for the new teams, then rerun the evaluation.
- Unchanged safety rule: a red flag or an unclear request still goes to Clinical.
  An interpreter request is Patient Advocacy, but if the patient also says something clinical,
  Clinical gets a ticket too.

## Fields the dashboard reads

`id, room, department, department_name, priority, summary, original_text, created_at, status,
reasons, notes, patient_name`, and `level` (1 to 4, from SPEC.md) when the backend adds it. Until then
the level comes from `priority`: urgent is 2, routine is 3 for Clinical and 4 for everyone else.

## Per-team numbers on the dashboard

Each team screen shows Open, Urgent waiting and Overdue (worked out from `/api/tickets`), and
**Requests so far** for that team. For that last number the dashboard reads
`stats.by_department` from `/api/tickets` and from each `/ws` event:

```json
"stats": {
  "requests_total": 42,
  "requests_without_nurse": 30,
  "by_department": { "nurse": { "total": 12, "done": 7 }, "food_services": { "total": 9, "done": 6 } }
}
```

`total` counts every ticket the department has received, open or done. Until the backend sends
`by_department`, the dashboard counts the tickets it has seen since the screen was opened.
