/* Placeholder backend for building the UI without a server. Development only:
   main.jsx loads it unless VITE_MOCK=false or the address has ?mock=0, and it is never
   included in a production build.

   It answers the same API as the real server (/api/requests, /api/tickets, ticket status,
   and a stand-in for the /ws live feed), so nothing else changes when the backend lands.
   Tickets are shared between browser tabs, so the patient page in one tab and the
   dashboard in another behave like the real thing.

   NOT the real routing: a few keywords so the screens can be clicked through. The real
   decision comes from app/router.py, app/rules.py and the model. */

const STORE = "callbell-mock-v3";
const channel = "BroadcastChannel" in window ? new BroadcastChannel("callbell-mock") : null;
const listeners = new Set();

const NAMES = {
  nurse: "Clinical", unit_clerk: "Unit Clerk", environmental_services: "Housekeeping",
  food_services: "Food & Nutrition", facilities_biomed: "Facilities & Biomed",
  patient_advocacy: "Patient Advocacy", case_management: "Case Management",
};

// Red flags first: they always go to Clinical, at level 1 or 2.
const RED_FLAGS = [
  [1, "trouble breathing", /\b(can'?t breathe|cannot breathe|short(ness)? of breath|gasping|choking)\b/i],
  [1, "chest pain", /\bchest (pain|hurts|tight)/i],
  [1, "bleeding", /\bbleed\w*/i],
  [1, "fall", /\b(i|he|she) (fell|have fallen|has fallen)\b|\bfell (out of|down)/i],
  [1, "emergency", /\bemergency\b/i],
  [2, "severe pain", /\b(severe|terrible|unbearable|worst) pain\b|pain is (8|9|10)\b/i],
  [2, "dizziness", /\bdizz\w+|light-?headed/i],
  [2, "vomiting", /\bvomit\w*|throw(ing)? up/i],
];
const ROUTES = [
  ["nurse", 3, /\b(pain|medicine|medication|pill|nurse|bathroom|toilet|bedpan|oxygen|nebuli[sz]er|iv|doctor|lab results)\b/i],
  ["patient_advocacy", 4, /\b(complain\w*|translator|interpreter|my rights|rude|speak to (a |the )?manager)\b/i],
  ["case_management", 4, /\b(insurance|nursing home|rehab facility|home equipment|walker|wheelchair at home|social worker|after (i go|discharge))\b/i],
  ["facilities_biomed", 4, /\b(too (hot|cold)|temperature|thermostat|broken|not working|bed (won'?t|doesn'?t)|light (is )?out)\b/i],
  ["environmental_services", 4, /\b(clean\w*|spill\w*|trash|garbage|linens?|sheets?|towels?|blanket|pillow|cobija|almohada|limpi\w*)\b/i],
  ["food_services", 4, /\b(water|drink|juice|coffee|tea|food|eat|meal|snack|hungry|thirsty|menu|agua|comida|comer)\b/i],
  ["unit_clerk", 4, /\b(wi-?fi|internet|phone|tv|television|remote|visitor|visiting hours|charger|parking)\b/i],
];

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;

function read() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE) || "null");
    if (saved?.tickets) return saved;
  } catch { /* storage blocked: fall back to memory */ }
  return null;
}
let memory = read();
if (!memory) { memory = seed(); save(memory); }     // first tab seeds; others read the same store
function load() { memory = read() || memory; return memory; }
function save(data) {
  memory = data;
  try { localStorage.setItem(STORE, JSON.stringify(data)); } catch { /* memory only */ }
}
function stats(data) {
  // by_team: every ticket each team has received, open or done.
  const by_team = {};
  for (const t of data.tickets) {
    const d = (by_team[t.team || t.department] ||= { total: 0, done: 0 });
    d.total += 1;
    if (t.status === "done") d.done += 1;
  }
  return { requests_total: data.requests_total, requests_without_nurse: data.requests_without_nurse, by_team };
}
function emit(event) {
  listeners.forEach((fn) => fn(event));          // this tab
  channel?.postMessage(event);                    // other tabs
}
channel?.addEventListener("message", (e) => listeners.forEach((fn) => fn(e.data)));

function makeTicket(data, room, text, department, level, extra = {}) {
  return {
    id: `M${String(data.nextId++).padStart(4, "0")}`, room, department,
    department_name: NAMES[department], level, priority: level <= 2 ? "urgent" : "routine",
    summary: extra.summary || text || "Patient pressed the call button. Nothing was understood.",
    original_text: text, created_at: extra.created_at || now(), status: extra.status || "open",
    reasons: extra.reasons || [], notes: extra.notes || [], patient_name: null,
    team: department, team_name: NAMES[department],
  };
}

function route(text) {
  const flags = RED_FLAGS.filter(([, , re]) => re.test(text));
  if (flags.length) return [["nurse", Math.min(...flags.map(([l]) => l)), flags.map(([, why]) => why)]];
  const hits = ROUTES.filter(([, , re]) => re.test(text)).map(([dept, level]) => [dept, level, []]);
  return hits.length ? hits : [["nurse", 2, ["could not sort this request"]]];   // unknown goes to Clinical
}

// A few tickets so the dashboard is not empty on first open.
function seed() {
  const data = { tickets: [], nextId: 1, requests_total: 0, requests_without_nurse: 0 };
  const ago = (min) => now() - min * 60;
  const add = (room, text, dept, level, min, extra = {}) => {
    data.tickets.push(makeTicket(data, room, text, dept, level, { created_at: ago(min), ...extra }));
    data.requests_total += 1;
    if (dept !== "nurse") data.requests_without_nurse += 1;
  };
  add("419", "I can't catch my breath", "nurse", 1, 1, { summary: "Trouble breathing", reasons: ["trouble breathing"], notes: ["Contact isolation"] });
  add("415", "My pain is really bad, like an 8", "nurse", 2, 4, { summary: "Severe pain, rates it 8 of 10", reasons: ["severe pain"], notes: ["High fall risk"] });
  add("412", "Can I get help to the bathroom", "nurse", 3, 7, { summary: "Help to the bathroom" });
  add("425", "I'm thirsty, can I get some water?", "food_services", 4, 3, { summary: "Water", notes: ["Diet: nothing by mouth. Check with the nurse first."] });
  add("423", "Can someone clean up the spill by my bed", "environmental_services", 4, 18, { summary: "Spill by the bed", notes: ["Droplet isolation: mask before entering"] });
  add("417", "It's freezing in here", "facilities_biomed", 4, 9, { summary: "Room too cold" });
  add("421", "I want to talk to someone about a complaint", "patient_advocacy", 4, 12, { summary: "Wants to make a complaint" });
  add("414", "Necesito saber si mi seguro cubre la rehabilitación", "case_management", 4, 25, { summary: "Insurance coverage for rehab (asked in Spanish)" });
  add("430", "The Wi-Fi password doesn't work", "unit_clerk", 4, 6, { summary: "Wi-Fi password not working", status: "acknowledged" });
  return data;
}

async function handle(path, init) {
  await wait(300);                                           // feel like a network call
  const data = load();

  if (path === "/api/requests" && init.method === "POST") {
    const { room, text = "", direct_nurse = false } = JSON.parse(init.body || "{}");
    if (!direct_nurse && !text.trim()) return json({ detail: "Type or say what you need." }, 422);
    const routes = direct_nurse ? [["nurse", 2, ["patient asked for the nurse"]]] : route(text);
    const tickets = routes.map(([dept, level, reasons]) =>
      makeTicket(data, room, text, dept, level, { reasons, summary: direct_nurse && !text ? "Patient asked for the nurse" : undefined }));
    data.tickets.push(...tickets);
    data.requests_total += 1;
    if (!tickets.some((t) => t.department === "nurse")) data.requests_without_nurse += 1;
    save(data);
    tickets.forEach((ticket) => emit({ type: "ticket_created", ticket, stats: stats(data) }));
    return json({ tickets, trace: { mock: true } });
  }

  if (path === "/api/tickets" && (init.method || "GET") === "GET") {
    return json({ tickets: data.tickets.filter((t) => t.status !== "done"), stats: stats(data) });
  }

  const m = path.match(/^\/api\/tickets\/([^/]+)\/status$/);
  if (m && init.method === "POST") {
    const { status } = JSON.parse(init.body || "{}");
    if (status !== "acknowledged" && status !== "done") return json({ detail: "status must be 'acknowledged' or 'done'" }, 422);
    const ticket = data.tickets.find((t) => t.id === decodeURIComponent(m[1]));
    if (!ticket) return json({ detail: "ticket not found" }, 404);
    ticket.status = status;
    save(data);
    emit({ type: "ticket_updated", ticket, stats: stats(data) });
    return json(ticket);
  }

  if (path === "/api/transcribe" || path === "/api/speak") {
    return json({ detail: "voice service not configured" }, 503);   // browser speech takes over
  }
  return json({ detail: "not in mock" }, 404);
}

export function installMockApi() {
  const realFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
    if (url.pathname.startsWith("/api/")) return handle(url.pathname, { method: "GET", ...init });
    return realFetch(input, init);
  };
  // Stand-in for the /ws socket.
  window.__callbellMockFeed = {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    reset() { try { localStorage.removeItem(STORE); } catch { /* ignore */ } memory = seed(); save(memory); },
  };

  const strip = document.createElement("div");
  strip.textContent = "Demo mode: placeholder backend";
  strip.className = "mock-strip";
  document.body.prepend(strip);
}
