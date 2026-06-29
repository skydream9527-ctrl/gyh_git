import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vitest config for the websocket-token-stability feature's frontend tests.
// jsdom + globals mirror @testing-library/react expectations; the `@/` alias
// matches vite.config.ts / tsconfig.json so test imports resolve identically
// to app code. Kept separate from vite.config.ts so the dev-server hardening
// plugin and prod chunking config never load under the test runner.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
