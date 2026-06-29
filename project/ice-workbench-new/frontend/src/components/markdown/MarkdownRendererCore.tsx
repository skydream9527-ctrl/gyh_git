import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DOMPurify from "dompurify";
import { useUIStore } from "@/stores/uiStore";
import "./markdown.css";

interface Props {
  content: string;
  // streaming=true 时用更轻的行内代码块、不挂复制按钮：流式态每个 token 都会重渲，
  // 省掉复制按钮组件的开销；done 后切回带复制按钮的 CodeBlock。
  // 注意：代码块统一渲染为纯 <pre><code>，当前没有接语法高亮库。
  streaming?: boolean;
}

function MarkdownRendererImpl({ content, streaming }: Props) {
  const safe = useMemo(
    () => DOMPurify.sanitize(content, { USE_PROFILES: { html: true } }),
    [content],
  );
  const components = useMemo(() => buildComponents(streaming), [streaming]);
  return (
    <div className="md-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {safe}
      </ReactMarkdown>
    </div>
  );
}

function buildComponents(streaming?: boolean) {
  return {
    a: ({ children, href }: any) => (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
    code({ inline, className, children, ...rest }: any) {
      const match = /language-(\w+)/.exec(className || "");
      if (!inline && match) {
        const code = String(children).replace(/\n$/, "");
        if (streaming) {
          return (
            <div className="md-code-block">
              <div className="md-code-head">
                <span className="md-lang">{match[1]}</span>
              </div>
              <pre className="md-code-plain">
                <code>{code}</code>
              </pre>
            </div>
          );
        }
        return <CodeBlock language={match[1]} code={code} />;
      }
      return (
        <code className={className} {...rest}>
          {children}
        </code>
      );
    },
  };
}

import { CodeHighlighter } from "./CodeHighlighter";

function CodeBlock({ language, code }: { language: string; code: string }) {
  const pushToast = useUIStore((s) => s.pushToast);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      pushToast("success", "代码已复制");
    } catch (err) {
      pushToast("error", `复制失败：${(err as Error).message}`);
    }
  };
  return (
    <div className="md-code-block">
      <div className="md-code-head">
        <span className="md-lang">{language}</span>
        <button className="md-copy" onClick={onCopy}>
          复制
        </button>
      </div>
      <CodeHighlighter code={code} language={language} />
    </div>
  );
}

export const MarkdownRenderer = memo(MarkdownRendererImpl);
