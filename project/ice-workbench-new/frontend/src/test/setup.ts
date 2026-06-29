// Global test setup for the websocket-token-stability frontend test suite.
// Runs once per test file before any tests (registered via setupFiles in
// vitest.config.ts). With `globals: true`, Vitest's lifecycle hooks are
// available without importing them.
//
// @testing-library/react unmounts components and cleans up the jsdom DOM
// between tests so state never leaks across cases.
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Node 25 ships a built-in Web Storage `localStorage` global that shadows
// jsdom's implementation but is inert unless `--localstorage-file` is given a
// valid path (its `getItem`/`setItem` are undefined here). Any module that
// touches `localStorage` at import time (e.g. the UI store reading the saved
// theme) then throws "localStorage.getItem is not a function". Install a small
// in-memory Storage polyfill when the active global is missing the Storage API
// so module-level and runtime localStorage access works deterministically under
// the test runner. This only activates when the current global is broken, so it
// leaves a working jsdom/browser localStorage untouched.
function installMemoryStorage(): void {
  const current = (globalThis as { localStorage?: unknown }).localStorage as
    | { getItem?: unknown }
    | undefined;
  if (current && typeof current.getItem === "function") return;

  const store = new Map<string, string>();
  const memoryStorage: Storage = {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? (store.get(key) as string) : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  };

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: memoryStorage,
  });
  if (typeof window !== "undefined") {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: memoryStorage,
    });
  }
}

installMemoryStorage();

afterEach(() => {
  cleanup();
});
