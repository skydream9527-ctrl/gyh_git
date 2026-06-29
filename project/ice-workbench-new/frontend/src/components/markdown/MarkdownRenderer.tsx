/**
 * Lazy-loading wrapper for MarkdownRenderer.
 *
 * react-markdown + remark-gfm + DOMPurify are heavy (~60KB parsed). Since
 * multiple lazy-loaded pages import MarkdownRenderer, vite hoists them into
 * the shared vendor chunk — meaning the login page pays for markdown it
 * never renders. This wrapper creates a dynamic import boundary so the
 * markdown stack loads only when a component actually renders markdown.
 *
 * Fallback: while the chunk loads, we render the raw content in a plain
 * <pre> (same as what streaming=true already does), so the user sees text
 * immediately. Once loaded, full markdown formatting kicks in seamlessly.
 *
 * All 7 consumers keep their existing import path unchanged.
 */
import { lazy, memo, Suspense } from "react";

const Core = lazy(() =>
  import("./MarkdownRendererCore").then((m) => ({
    default: m.MarkdownRenderer,
  })),
);

interface Props {
  content: string;
  streaming?: boolean;
}

function MarkdownRendererImpl({ content, streaming }: Props) {
  return (
    <Suspense
      fallback={
        <div className="md-body">
          <pre style={{ whiteSpace: "pre-wrap", margin: 0, font: "inherit" }}>
            {content}
          </pre>
        </div>
      }
    >
      <Core content={content} streaming={streaming} />
    </Suspense>
  );
}

export const MarkdownRenderer = memo(MarkdownRendererImpl);
