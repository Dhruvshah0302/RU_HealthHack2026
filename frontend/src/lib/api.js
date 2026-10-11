// The only place the page talks to the server. Same API as the FastAPI backend:
//   POST /api/requests   {room, text, direct_nurse} -> {tickets: [...]}
//   POST /api/transcribe  raw audio body              -> {text, language}  (ElevenLabs, app/voice.py)

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

// Is server speech to text (ElevenLabs) set up? Then the page trusts it over the browser.
export async function serverSpeechReady() {
  try {
    const response = await fetchWithin("/api/voice/health", {}, 2000);
    return response.ok && (await response.json()).speech_to_text === "elevenlabs";
  } catch {
    return false;
  }
}

// Returns {text, language}; text is "" if ElevenLabs is unavailable, failed or heard nothing.
export async function transcribe(blob, langTag) {
  try {
    // The recording goes as the raw body; ElevenLabs works out the language by itself.
    const url = `/api/transcribe?lang=${encodeURIComponent(langTag)}`;
    const response = await fetchWithin(url, {
      method: "POST", headers: { "Content-Type": (blob.type || "audio/webm").split(";")[0] }, body: blob,
    }, TRANSCRIBE_WAIT_MS);
    if (!response.ok) return { text: "", language: null };
    const data = await response.json();
    return { text: (data.text || "").trim(), language: data.language || null };
  } catch {
    return { text: "", language: null };
  }
}
