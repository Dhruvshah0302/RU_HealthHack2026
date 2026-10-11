import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api/* goes to the FastAPI server on port 8000 once it exists.
// Until then the placeholder backend (src/mock/mockApi.js) answers instead; see .env.development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000", "/ws": { target: "ws://localhost:8000", ws: true } },
  },
});
