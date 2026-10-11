# Frontend (React + Vite)

Two pages in one app. Plain React, no UI library.

| Address | Page |
|---|---|
| `/?room=412` | Bedside patient page |
| `/dashboard` | Staff dashboard: one screen per team in the team's colour, `?team=food_services` opens that team |

## Run it

Needs Node.js 18 or newer.

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173/?room=412 in Chrome (`&lang=es` for Spanish, `&mode=type` to open on typing,
`&debug=1` to see the live microphone reading), and http://localhost:5173/dashboard in another tab.

## Placeholder backend

Until the FastAPI server exists, `src/mock/mockApi.js` answers `/api/*` in the browser and a yellow
"Demo mode" strip shows at the top. It is on by default in `npm run dev`; turn it off with
`?mock=0` in the address, or for good by creating `frontend/.env.development` with `VITE_MOCK=false`.
It is never included in `npm run build`.

The mock sorts by a few keywords only. It is not the routing policy; that lives in `app/router.py`.
It routes to all seven teams in `DEPARTMENTS.md`, starts with a few example tickets, and shares
tickets between tabs, so a request sent from the patient page shows up on the dashboard at once.
To clear them, run `__callbellMockFeed.reset()` in the browser console and reload.

When the server runs on port 8000, turn the mock off: the dev server forwards `/api` to it.

## Layout

```
src/
  main.jsx                 starts the app (and the mock in development)
  pages/PatientPage.jsx    the page: state, submit, nurse fallback
  dashboard/DashboardPage.jsx  staff screen: team switch, queue, live updates
  dashboard/departments.js the seven teams and the backend codes each accepts
  dashboard/levels.js      priority levels and time targets (from SPEC.md)
  dashboard/feed.js        /api/tickets, ticket status, and the /ws live feed
  components/              ModeSwitch, VoicePanel, MicButton, TypePanel, Confirmation, NurseBar
  hooks/useVoiceCapture.js microphone, loudness meter, ElevenLabs + browser speech fallback
  lib/api.js               the only code that calls the server
  lib/i18n.js              English and Spanish text
  lib/params.js            room, language and mode from the address
  styles/patient.css
  mock/mockApi.js          placeholder backend (development only)
```

## Rules the page keeps

- Room and language come from the address. Default language en-US.
- Never shows priority. Never says a person was notified.
- If anything fails, the request goes to the nurse (`direct_nurse=true`).
- The ElevenLabs key stays on the server; the page only calls `/api/transcribe` and `/api/speak`.
