import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DOMPurify from "dompurify";
import { useUIStore } from "@/stores/uiStore";
import "./markdown.css";

interface Props {
  content: string;
  // streaming=true 跳过 Prism 语法高亮，只用 <pre><code>。流式态每个 token 会重渲一次，
  // refractor 构建成本太高；done 后切回完整渲染。
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
      <pre className="md-code-plain">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export const MarkdownRenderer = memo(MarkdownRendererImpl);
