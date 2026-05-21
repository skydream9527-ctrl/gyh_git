import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// LAN testing toggle: `VITE_LAN=1 npm run dev` binds 0.0.0.0 so a phone on
// the same WiFi can reach http://<lan-ip>:5173/. Plain http — voice / mic
// features won't work over LAN (browsers require a secure context for
// getUserMedia), but everything else does. Wire up HTTPS via a real
// reverse-proxy / mkcert setup before re-enabling voice for LAN testing.
const LAN_MODE = process.env.VITE_LAN === "1";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    host: LAN_MODE ? true : "localhost",
    proxy: {
      // /api/v1/ws/conversations/* upgrades through here, so this single proxy
      // entry needs ws:true to forward both HTTP + WebSocket upgrade frames.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          // Only split out React core. Every other vendor lives in one chunk —
          // splitting markdown / hast / refractor creates circular ESM imports
          // (`Ti is undefined` at load time, white screen). One bigger chunk
          // is worth it for correctness on an internal tool.
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/scheduler/") ||
            id.includes("/react-router-dom/") ||
            id.includes("/react-router/") ||
            id.includes("/@remix-run/")
          ) {
            return "vendor-react";
          }
          return "vendor";
        },
      },
    },
  },
});
