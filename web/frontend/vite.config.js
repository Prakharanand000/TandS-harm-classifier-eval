import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build straight into the backend's static dir so FastAPI serves the app.
// In dev, proxy /api to the local FastAPI server on :8000.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../backend/static", emptyOutDir: true },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
