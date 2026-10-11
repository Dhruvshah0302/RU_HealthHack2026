import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

async function start() {
  // The placeholder backend only exists in development builds; it is never shipped.
  if (import.meta.env.DEV) {
    const params = new URLSearchParams(location.search);
    // On by default until the server exists. Turn off with VITE_MOCK=false (or ?mock=0).
    const wanted = params.get("mock") ?? import.meta.env.VITE_MOCK ?? "true";
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
