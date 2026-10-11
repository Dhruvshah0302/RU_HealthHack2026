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

// Asks ElevenLabs (through our server) for the words. Returns { text, error }:
// text is "" when nothing was heard; error says why ElevenLabs could not answer.
const VOICE_ERRORS = { 503: "not set up on the server", 502: "returned an error", 504: "took too long", 413: "recording too long", 415: "audio format not accepted" };

export async function transcribe(blob, langTag) {
  try {
    const form = new FormData();
    form.append("file", blob, "request.webm");
    form.append("lang", langTag);
    const response = await fetchWithin("/api/transcribe", { method: "POST", body: form }, TRANSCRIBE_WAIT_MS);
    if (!response.ok) return { text: "", error: VOICE_ERRORS[response.status] || `error ${response.status}` };
    return { text: ((await response.json()).text || "").trim(), error: null };
  } catch (err) {
    return { text: "", error: err.name === "AbortError" ? "took too long" : "could not be reached" };
  }
}
