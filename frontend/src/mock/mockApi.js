/* Placeholder backend for building the UI without a server. Development only:
   main.jsx loads it when VITE_MOCK=true (.env.development) or the address has ?mock=1,
   and it is never included in a production build.

   It answers the same API as the real server, so nothing else changes when the backend lands.
   NOT the real routing: a few keywords so the screens can be clicked through. The real
   decision comes from app/router.py and app/rules.py. */

const DEPT_NAMES = {
  nurse: "Nurse",
  housekeeping_facilities: "Housekeeping & Facilities",
  food_services: "Food Services",
  unit_clerk_it: "Unit Clerk / IT",
};
const KEYWORDS = [
  ["food_services", /\b(water|drink|juice|coffee|tea|food|eat|meal|snack|hungry|thirsty|agua|comida|comer)\b/i],
  ["housekeeping_facilities", /\b(blanket|pillow|clean|trash|towel|sheet|cobija|almohada|limpi)\w*/i],
  ["unit_clerk_it", /\b(tv|television|wi-?fi|internet|remote|phone|charger|televisi)\w*/i],
];
let nextId = 1;

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function ticket(room, text, department) {
  return {
    id: `M${String(nextId++).padStart(4, "0")}`, room, department,
    department_name: DEPT_NAMES[department], priority: "routine",
    summary: text || "Patient pressed the call button.", original_text: text,
    created_at: Date.now() / 1000, status: "open", reasons: [],
  };
}

async function handle(path, init) {
  await wait(400);                                           // feel like a network call
  if (path === "/api/requests" && init.method === "POST") {
    const { room, text = "", direct_nurse = false } = JSON.parse(init.body || "{}");
    if (!direct_nurse && !text.trim()) return json({ detail: "Type or say what you need." }, 422);
    if (direct_nurse) return json({ tickets: [ticket(room, text, "nurse")], trace: { mock: true } });
    const hits = KEYWORDS.filter(([, re]) => re.test(text)).map(([d]) => d);
    const departments = hits.length ? hits : ["nurse"];      // unknown goes to the nurse
    return json({ tickets: departments.map((d) => ticket(room, text, d)), trace: { mock: true } });
  }
  if (path === "/api/transcribe" || path === "/api/speak") {
    return json({ detail: "voice service not configured" }, 503);   // browser speech takes over
  }
  if (path === "/api/tickets") return json({ tickets: [], stats: { requests_total: 0, requests_without_nurse: 0 } });
  return json({ detail: "not in mock" }, 404);
}

export function installMockApi() {
  const realFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.origin);
    if (url.pathname.startsWith("/api/")) return handle(url.pathname, { method: "GET", ...init });
    return realFetch(input, init);
  };

  const strip = document.createElement("div");
  strip.textContent = "Demo mode: placeholder backend";
  strip.className = "mock-strip";
  document.body.prepend(strip);
}
