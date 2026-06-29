import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";

export default tseslint.config(
  // Global ignores
  { ignores: ["dist/", "node_modules/", "*.config.js", "*.config.ts"] },

  // Base JS recommended
  js.configs.recommended,

  // TypeScript recommended (type-unaware for speed)
  ...tseslint.configs.recommended,

  // React Hooks rules
  {
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },

  // Project-specific relaxations
  {
    rules: {
      // The codebase uses `any` extensively in WS event handlers and API layers;
      // cleaning it up is a separate effort. Keep as warning, not blocking.
      "@typescript-eslint/no-explicit-any": "warn",
      // Allow unused vars with _ prefix (common pattern for destructuring)
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Empty functions are common in no-op callbacks
      "@typescript-eslint/no-empty-function": "off",
      // Allow non-null assertions (used carefully in the codebase)
      "@typescript-eslint/no-non-null-assertion": "off",
      // Prefer const but don't block
      "prefer-const": "warn",
      // Allow empty catch blocks (WS handlers intentionally swallow)
      "no-empty": ["error", { allowEmptyCatch: true }],
      // Allow unused expressions for short-circuit patterns like `cond && fn()`
      "@typescript-eslint/no-unused-expressions": [
        "error",
        { allowShortCircuit: true, allowTernary: true },
      ],
      // Not applicable — rethrowing with cause is overkill for UI error handlers
      "preserve-caught-error": "off",
    },
  },
);
