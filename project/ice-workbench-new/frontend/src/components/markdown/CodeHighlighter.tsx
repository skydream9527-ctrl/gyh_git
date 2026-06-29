/**
 * Code syntax highlighter powered by shiki (TextMate grammars, VS Code quality).
 *
 * Architecture:
 * - Single shared highlighter instance (lazy-initialized on first render).
 * - While loading: renders plain <pre><code> (same as before — zero flash).
 * - After loaded: renders highlighted HTML via dangerouslySetInnerHTML.
 * - Only used when streaming=false (complete code blocks); streaming uses
 *   plain text to avoid re-running highlighter every token.
 *
 * Bundle optimization:
 * - Uses @shikijs/core + explicit lang/theme imports (NOT shiki/bundle/web).
 * - Only registers ~10 languages actually used in the product (SQL, Python, etc.).
 * - Uses engine-javascript (no oniguruma WASM) for ~80% smaller bundle.
 * - Carved out into vendor-shiki chunk by vite.config manualChunks.
 */
import { memo, useEffect, useState } from "react";

// Lazy singleton — avoids importing shiki at module level (keeps it tree-shakeable
// until actually called).
let highlighterPromise: Promise<any> | null = null;
let highlighterInstance: any = null;

// Languages actually used in this product's code blocks.
// Each is imported individually to avoid pulling the full grammar registry.
const LANG_IMPORTS = [
  () => import("@shikijs/langs/javascript"),
  () => import("@shikijs/langs/typescript"),
  () => import("@shikijs/langs/python"),
  () => import("@shikijs/langs/sql"),
  () => import("@shikijs/langs/json"),
  () => import("@shikijs/langs/bash"),
  () => import("@shikijs/langs/shell"),
  () => import("@shikijs/langs/html"),
  () => import("@shikijs/langs/css"),
  () => import("@shikijs/langs/markdown"),
  () => import("@shikijs/langs/yaml"),
] as const;

function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = (async () => {
      const [{ createHighlighterCore }, { createJavaScriptRegexEngine }, themeDark, themeLight, ...langs] =
        await Promise.all([
          import("@shikijs/core"),
          import("@shikijs/engine-javascript"),
          import("@shikijs/themes/github-dark"),
          import("@shikijs/themes/github-light"),
          ...LANG_IMPORTS.map((fn) => fn()),
        ]);

      const hl = await createHighlighterCore({
        themes: [themeDark.default, themeLight.default],
        langs: langs.map((l) => l.default),
        engine: createJavaScriptRegexEngine(),
      });
      highlighterInstance = hl;
      return hl;
    })();
  }
  return highlighterPromise;
}

// Set of languages we actually registered (for fast fallback check)
const SUPPORTED_LANGS = new Set([
  "javascript", "typescript", "python", "sql", "json",
  "bash", "shell", "html", "css", "markdown", "yaml",
]);

interface Props {
  code: string;
  language: string;
}

function CodeHighlighterImpl({ code, language }: Props) {
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const lang = normalizeLanguage(language);

    // If language isn't registered, skip highlighting entirely (plain fallback)
    if (!SUPPORTED_LANGS.has(lang)) {
      setHtml(null);
      return;
    }

    if (highlighterInstance) {
      // Already loaded — render synchronously
      try {
        const result = highlighterInstance.codeToHtml(code, {
          lang,
          theme: getPreferredTheme(),
        });
        setHtml(result);
      } catch {
        setHtml(null); // fallback to plain
      }
    } else {
      // Still loading — trigger init and render when ready
      getHighlighter().then((hl) => {
        if (cancelled) return;
        try {
          const result = hl.codeToHtml(code, {
            lang,
            theme: getPreferredTheme(),
          });
          setHtml(result);
        } catch {
          setHtml(null);
        }
      }).catch(() => {
        // shiki load failed — stay with plain fallback
      });
    }
    return () => { cancelled = true; };
  }, [code, language]);

  if (html) {
    return (
      <div
        className="shiki-wrapper"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  // Fallback: plain text (identical to current behavior)
  return (
    <pre className="md-code-plain">
      <code>{code}</code>
    </pre>
  );
}

export const CodeHighlighter = memo(CodeHighlighterImpl);

// --- Helpers ---

function normalizeLanguage(lang: string): string {
  const map: Record<string, string> = {
    js: "javascript",
    ts: "typescript",
    py: "python",
    sh: "bash",
    zsh: "bash",
    yml: "yaml",
    jsonc: "json",
    tsx: "typescript",
    jsx: "javascript",
  };
  const normalized = lang.toLowerCase();
  return map[normalized] || normalized;
}

function getPreferredTheme(): string {
  // Respect system/user dark mode preference
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches) {
    return "github-dark";
  }
  return "github-light";
}
