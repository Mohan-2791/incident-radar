import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy /graphql (HTTP + WebSocket) to the FastAPI server so there's no CORS in the browser.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/graphql": { target: "http://localhost:8000", ws: true } },
  },
});
