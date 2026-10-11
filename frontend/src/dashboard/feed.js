/* Tickets for the staff dashboard, using the API the backend already has:
     GET  /api/tickets                 -> { tickets, stats }
     POST /api/tickets/{id}/status     { status: "acknowledged" | "done" }
     WS   /ws                          -> { type: "ticket_created" | "ticket_updated", ticket, stats }
   The socket brings changes at once; a poll every 10 s catches anything a dropped socket missed. */

const WAIT_MS = 8000;

async function call(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), WAIT_MS);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  } catch (err) {
    if (err.name === "AbortError") throw new Error("The server did not answer in time.");
    if (err instanceof TypeError) throw new Error("Could not reach the server.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const loadTickets = () => call("/api/tickets");

export const setStatus = (id, status) => call(`/api/tickets/${encodeURIComponent(id)}/status`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }),
});

// onEvent(event), onLink("live" | "down"). Returns a function that stops listening.
export function subscribe(onEvent, onLink) {
  if (window.__callbellMockFeed) {                     // development placeholder
    onLink("live");
    return window.__callbellMockFeed.subscribe(onEvent);
  }
  let socket = null;
  let stopped = false;
  let retry = null;
  const connect = () => {
    socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
    socket.onopen = () => onLink("live");
    socket.onmessage = (message) => { try { onEvent(JSON.parse(message.data)); } catch { /* ignore bad frames */ } };
    socket.onclose = () => {
      if (stopped) return;
      onLink("down");
      retry = setTimeout(connect, 2000);
    };
  };
  connect();
  return () => { stopped = true; clearTimeout(retry); socket?.close(); };
}
