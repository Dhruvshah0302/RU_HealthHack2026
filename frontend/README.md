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

## With the real backend

The FastAPI server serves the built pages itself. From the project folder:

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn app.main:app --reload
```

Then open http://localhost:8000/?room=412 (patient) and http://localhost:8000/dashboard (staff).
Rebuild (`npm run build`) after changing anything in `frontend/`.

While working on the pages, `npm run dev` (http://localhost:5173) is faster: it reloads on save and
forwards `/api` and `/ws` to the server on port 8000.

## Placeholder backend

When the server is not running, `npm run dev` uses `src/mock/mockApi.js` instead and shows a yellow
"Demo mode" strip. It routes to all seven teams by keyword (not the real routing), starts with a few
example tickets, and shares tickets between tabs. `?mock=1` or `?mock=0` forces it on or off. It is
never included in `npm run build`. To clear its tickets, run `__callbellMockFeed.reset()` in the
browser console and reload.

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
