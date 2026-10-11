// The only place the page talks to the server. Same API as the FastAPI backend:
//   POST /api/requests   {room, text, direct_nurse} -> {tickets: [...]}
//   POST /api/transcribe  multipart file + lang      -> {text, language}

const REQUEST_WAIT_MS = 8000;
const TRANSCRIBE_WAIT_MS = 10000;      // the server gives up on ElevenLabs at 8 s

async function fetchWithin(url, options, ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function postRequest(body) {
  const response = await fetchWithin("/api/requests", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }, REQUEST_WAIT_MS);
  if (!response.ok) throw new Error(`requests ${response.status}`);
  return response.json();
}

// Any failure sends the request to the nurse instead. Throws only if that fails too.
export async function submitRequest({ room, text = "", direct_nurse = false }) {
  try {
    return await postRequest({ room, text, direct_nurse });
  } catch (err) {
    if (direct_nurse) throw err;
    return postRequest({ room, text, direct_nurse: true });
  }
}

// Returns the transcript, or "" if ElevenLabs is unavailable, failed or heard nothing.
export async function transcribe(blob, langTag) {
  try {
    const form = new FormData();
    form.append("file", blob, "request.webm");
    form.append("lang", langTag);
    const response = await fetchWithin("/api/transcribe", { method: "POST", body: form }, TRANSCRIBE_WAIT_MS);
    if (!response.ok) return "";
    return ((await response.json()).text || "").trim();
  } catch {
    return "";
  }
}
