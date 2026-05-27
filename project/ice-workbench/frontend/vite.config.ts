import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import type { Plugin, ViteDevServer } from "vite";

// LAN exposure is dangerous: a Vite dev server on 0.0.0.0 leaks /src/**
// (full TS source + sourcemaps), exposes /__open-in-editor + /@vite/client
// HMR WebSocket, and lacks every security header. The right way to demo
// to a phone is `make prod` (single-port, serves dist/ via uvicorn with
// security headers). LAN dev mode is therefore double-gated: VITE_LAN=1
// AND VITE_LAN_ACK=1. Without the ack we refuse to bind 0.0.0.0 and print
// a hint pointing at make prod.
const LAN_REQUESTED = process.env.VITE_LAN === "1";
const LAN_ACKED = process.env.VITE_LAN_ACK === "1";
const LAN_MODE = LAN_REQUESTED && LAN_ACKED;

if (LAN_REQUESTED && !LAN_ACKED) {
  // eslint-disable-next-line no-console
  console.warn(
    "\n⚠ VITE_LAN=1 在 dev server 上是高危配置：会把整个 /src 源码、sourcemap、" +
      "HMR WebSocket、__open-in-editor 端点和未加固的 /api 反代全部暴露给 LAN。\n" +
      "  推荐改用 `make prod`：vite build → uvicorn 0.0.0.0 单端口同时伺服 SPA + API + WS，\n" +
      "  安全头由后端统一注入。\n" +
      "  如果确认需要 dev server LAN 模式，再加 VITE_LAN_ACK=1 才会绑定 0.0.0.0。\n",
  );
}

/**
 * Dev-only hardening middleware. Even with VITE_LAN unset, headers are
 * helpful for the localhost dev path (sets a baseline so devs notice
 * regressions before they ship to prod). When LAN_MODE is on, this is the
 * only thing standing between a curious LAN peer and an XSS payload host.
 */
function devSecurity(): Plugin {
  return {
    name: "ice-dev-security",
    configureServer(server: ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        // 一律屏蔽 Vite 内置的 /__open-in-editor —— 该端点历史上出现过
        // 命令注入 (CVE-2024-23331 类)，且非本机 IDE 永远不需要触达。
        if (req.url && req.url.startsWith("/__open-in-editor")) {
          res.statusCode = 404;
          res.end();
          return;
        }
        res.setHeader("X-Frame-Options", "DENY");
        res.setHeader("X-Content-Type-Options", "nosniff");
        res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
        res.setHeader(
          "Permissions-Policy",
          "geolocation=(), microphone=(self), camera=()",
        );
        // dev 模式不强制 CSP（HMR / inline script 不兼容），生产由后端中间件设置。
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), devSecurity()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    host: LAN_MODE ? true : "localhost",
    // strict file-system serving: deny any read outside the project root
    // (Vite 5 default, but pinned here so a future config edit can't quietly
    // open it back up).
    fs: { strict: true },
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
