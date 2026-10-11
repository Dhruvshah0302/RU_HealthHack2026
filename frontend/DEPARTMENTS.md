# Teams on the staff dashboard

The dashboard (`/dashboard`) has one screen per team, each in its own colour. Clinical requests
all go to the Clinical team (nursing answers and brings in the physician, respiratory therapy,
pharmacy or PT/OT as needed). Every other request goes to the support team that does that work.

## How a ticket reaches a team (backend)

1. `app/router.py` and the classifier choose the **department**, exactly as before. Red flags and
   unclear requests still go to the nurse. The department drives the patient rules
   (`app/policy.py`) and the evaluation (`eval/`), so those are unchanged.
2. `app/teams.py` then picks the **team** that works the ticket inside the support departments:

| Team | `team` code | Comes from department | Covers |
|---|---|---|---|
| Clinical | `nurse` | `nurse` | Pain, symptoms, medication, bathroom help, breathing, anything clinical or unclear |
| Unit Clerk | `unit_clerk` | `unit_clerk_it` | Wi-Fi, phone, channels, visiting hours, parking, chaplain |
| Housekeeping | `environmental_services` | `housekeeping_facilities` | Cleaning, spills, trash, linens, pillows, blankets |
| Facilities & Biomed | `facilities_biomed` | `housekeeping_facilities` or `unit_clerk_it` | Room temperature, lights, plumbing, broken TV, bed or tablet |
| Food & Nutrition | `food_services` | `food_services` | Meals, snacks, drinks |
| Patient Advocacy | `patient_advocacy` | `patient_advocacy` (new) | Complaints, interpreters, patient rights |
| Case Management | `case_management` | `case_management` (new) | Insurance, nursing home or rehab after discharge, home equipment, social work |

Patient Advocacy and Case Management are new departments, with new classifier categories
(`patient_relations`, `care_coordination`) in the model prompt and the keyword baseline. Before,
those requests went to the nurse. A request that is also clinical still gets a nurse ticket.

The evaluation is unchanged by this: the keyword baseline scores the same on all 136 requests
(urgent caught 24/51, kept off the nurse 56/70, exact 87/136, false urgent 0/85).

## What a ticket carries

`id, room, department, department_name, team, team_name, priority, summary, original_text,
created_at, status, reasons, notes, patient_name`. The dashboard places a ticket by `team`
(falling back to `department`). A code it does not know goes to the Clinical screen with a note,
never dropped.

## Per-team numbers

`/api/tickets` and every `/ws` event include `stats.by_team`:

```json
"stats": {
  "requests_total": 42, "requests_without_nurse": 30,
  "by_team": { "nurse": { "total": 12, "done": 7 }, "food_services": { "total": 9, "done": 6 } }
}
```

`total` counts every ticket the team has received, open or done. Each screen shows Open, Urgent
waiting and Overdue (from the open tickets) and Requests so far (from `by_team`).
