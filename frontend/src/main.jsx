import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

async function backendIsUp() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1500);
    const response = await fetch("/api/health", { signal: controller.signal });
    clearTimeout(timer);
    return response.ok && Boolean((await response.json()).ok);
  } catch {
    return false;
  }
}

async function start() {
  // The placeholder backend only exists in development builds; it is never shipped.
  // ?mock=1 / ?mock=0 (or VITE_MOCK) force it on or off. Otherwise it is used only when the
  // FastAPI server is not running.
  if (import.meta.env.DEV) {
    const params = new URLSearchParams(location.search);
    const forced = params.get("mock") ?? import.meta.env.VITE_MOCK;
    const wanted = forced ?? ((await backendIsUp()) ? "false" : "true");
    if (wanted === "true" || wanted === "1") {
      const { installMockApi } = await import("./mock/mockApi.js");
      installMockApi();
    }
  }
  createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
start();
