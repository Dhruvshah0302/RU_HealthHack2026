import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles/patient.css";

async function start() {
  // The placeholder backend only exists in development builds; it is never shipped.
  if (import.meta.env.DEV) {
    const params = new URLSearchParams(location.search);
    // ?mock=1 / ?mock=0 force it. Otherwise: use the real server when it answers, else the placeholder.
    const forced = params.get("mock");
    const useMock = forced != null ? forced === "1" || forced === "true" : !(await serverIsUp());
    if (useMock) {
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
async function serverIsUp() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1500);
    const response = await fetch("/api/health", { signal: controller.signal });
    clearTimeout(timer);
    return response.ok;
  } catch {
    return false;
  }
}

start();
