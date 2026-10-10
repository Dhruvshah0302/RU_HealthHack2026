# AI Call Bell Router (RUHack – Challenge 2)

React (bedside / dashboards / admin) → FastAPI (REST) → ElevenLabs STT → Red-flag gate + AWS Bedrock → Ticket DB → Department queues.

## Architecture
```
 React app (Vite)
 ├─ /bed/:bedId         Patient bedside: 🎤 voice, text box, quick-tap buttons, ticket status
 ├─ /dept/:department   Queue: housekeeping | facilities | food_services | it_support | nursing
 └─ /admin              Rooms, beds, demo patient alias (no PHI / no EMR)
          │ REST (JSON / multipart audio)        ▲ poll every 2s
          ▼                                      │
 FastAPI
 ├─ POST /api/requests/voice  → ElevenLabs speech-to-text → triage → ticket
 ├─ POST /api/requests/text   → triage → ticket   (fallback if mic/STT fails)
 ├─ GET  /api/bedside/{bed}/tickets               patient sees "On the way / Done"
 ├─ GET  /api/tickets?department=…&status=open    department queue (urgent first)
 ├─ PATCH /api/tickets/{id}  {status}             accept / done
 ├─ GET  /api/tickets/metrics/summary             % diverted from nursing
 ├─ GET  /api/tickets/{id}/confirmation.mp3       ElevenLabs TTS (P1, ENABLE_TTS=true)
 └─ /api/admin/rooms, /api/admin/beds, …/assign, …/discharge

 Triage engine (app/triage/engine.py)
   1. red_flags.check()  deterministic, ms, offline  → if hit: NURSING / URGENT (LLM can't override)
   2. Bedrock Converse   JSON classification, temp 0, 5s timeout, Pydantic-validated
   3. Guardrails: clinical → nursing (never "routine"); error/timeout/invalid → nursing + needs_review;
      low confidence / "other" → nursing review; else category → department table
```

## Run it (two terminals)
```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add ElevenLabs key; run `aws configure` for Bedrock
pytest -q                   # 12 offline safety tests
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs   (demo beds 410A … 412B are seeded)
# No AWS yet? set LLM_PROVIDER=mock in .env (keyword classifier, dev only, never demo it as the AI)

# 2) Frontend
cd frontend
npm install
npm run dev                 # http://localhost:5173  (proxies /api → :8000)
```
Pages: `/` role picker · `/bed/412B` patient · `/dept/housekeeping` (or nursing, food_services, facilities, it_support) · `/admin`

## Who owns what (avoid merge conflicts)
| Member | Owns | Files |
|---|---|---|
| A: Product/PM | Demo script, impact model, deck, test-case list | `docs/` |
| B: Frontend | Bedside, queues, admin UI | `frontend/src/**` |
| C: AI & Safety | Prompt, red flags, eval set, accuracy report | `backend/app/triage/**`, `backend/tests/**` |
| D: Backend/AWS | API, DB, ElevenLabs, Bedrock access, deploy | `backend/app/routers/**`, `services/**`, `db.py`, `main.py` |

`backend/app/schemas.py` is the shared contract: change it only after the team agrees.
Branches: `feat/<area>-<thing>` → PR → one reviewer → merge to `main`. Keep `main` always demo-able.

## Before you rely on it: verify in the first hour
- [ ] Bedrock: model access is enabled in the region; `BEDROCK_MODEL_ID` matches the console (Nova Lite / Claude Haiku etc.)
- [ ] IAM user/role has `bedrock:InvokeModel`
- [ ] ElevenLabs key works; STT model id (`scribe_v1`) still current; quota OK
- [ ] React's MediaRecorder sends `audio/webm` → ElevenLabs accepts it (test once)

## Frontend notes (Member B)
- Record: `navigator.mediaDevices.getUserMedia({audio:true})` + `MediaRecorder` → POST FormData(`bed_id`, `audio`).
- Mic needs HTTPS or localhost. For a tablet in the demo, deploy behind HTTPS (or use ngrok).
- Show `patient_message` from the response in big text; if `tts_url`, play it with `new Audio(url)`.
- Dashboards: `setInterval(fetch, 2000)` on `/api/tickets?department=X`; red cards for `priority=urgent`, banner for `needs_review`.

## Safety notes
- Demo data only: fictional aliases, no real patient information, no EMR.
- The app says requests are "sent to the queue"; it never claims a person was notified.
- Urgent messages tell the patient to press the bedside call button if things get worse.
- Voice audio goes to ElevenLabs (a third party). Fine for synthetic demo audio; production would need a BAA / zero-retention or Amazon Transcribe.
