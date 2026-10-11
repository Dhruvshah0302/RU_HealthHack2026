// Everything the page takes from its address, e.g. /patient?room=412&lang=es&mode=type
const params = new URLSearchParams(window.location.search);

export const room = params.get("room") || "412";
export const langTag = params.get("lang") || "en-US";        // passed to speech services as given
export const lang = langTag.toLowerCase().startsWith("es") ? "es" : "en"; // which screen text to show
export const initialMode = params.get("mode") === "type" ? "type" : "voice";
export const DEBUG = params.has("debug");                       // ?debug=1 shows the live mic reading
