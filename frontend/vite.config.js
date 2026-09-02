import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend calls the backend through a dev proxy so /api works without CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
