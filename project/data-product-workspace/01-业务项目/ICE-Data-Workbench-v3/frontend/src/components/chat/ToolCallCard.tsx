import { useEffect, useMemo, useRef, useState } from "react";
import type { ToolCall } from "@/types/api";
import "./ToolCallCard.css";

const STATUS_META: Record<ToolCall["status"], { color: string; badge: string; label: string }> = {
  executing: { color: "warning", badge: "⏳", label: "执行中" },
  done: { color: "success", badge: "✅", label: "已完成" },
  error: { color: "error", badge: "❌", label: "失败" },
  timeout: { color: "info", badge: "⏱", label: "已超时" },
};

interface Props {
  call: ToolCall;
  onRetry?: (call: ToolCall) => void;
  onCopyError?: (call: ToolCall) => void;
}

export function ToolCallCard({ call, onRetry, onCopyError }: Props) {
  const meta = STATUS_META[call.status];
  const [showArgs, setShowArgs] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const { ref, visible } = useNearViewport<HTMLDivElement>();
  const resultSummary = useMemo(() => summarizeResult(call.result), [call.result]);

  if (!visible && call.status !== "executing") {
    return (
      <div ref={ref} className={`tool-card tool-${meta.color} tool-card-placeholder`}>
        <div className="tool-head">
          <span>{meta.badge}</span>
          <span>
            {meta.label} · {call.display_name || call.tool_name}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div ref={ref} className={`tool-card tool-${meta.color}`}>
      <div className="tool-head">
        <span>{meta.badge}</span>
        <span>
          {meta.label} · {call.display_name || call.tool_name}
        </span>
        <button className="tool-toggle" onClick={() => setShowArgs((v) => !v)}>
          {showArgs ? "收起参数" : "查看完整参数"}
        </button>
      </div>
      {showArgs && (
        <pre className="tool-args">{JSON.stringify(call.arguments, null, 2)}</pre>
      )}
      {call.status === "done" && call.result != null && (
        <div className="tool-result success">
          <span>{resultSummary}</span>
          <button className="tool-inline-btn" onClick={() => setShowResult((v) => !v)}>
            {showResult ? "收起结果" : "查看结果"}
          </button>
        </div>
      )}
      {showResult && <pre className="tool-args">{formatPreview(call.result, 6000)}</pre>}
      {(call.status === "error" || call.status === "timeout") && (
        <>
          <div className="tool-result fail">
            {call.error?.message || "执行失败"}
          </div>
          <div className="tool-error-code">
            error_code: {call.error?.code || call.error?.error_code || "UNKNOWN"}
          </div>
          <div className="tool-fail-actions">
            {onRetry && (
              <button onClick={() => onRetry(call)} className="btn-mini">
                🔁 重试
              </button>
            )}
            {onCopyError && (
              <button onClick={() => onCopyError(call)} className="btn-mini">
                📋 复制错误
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function summarizeResult(r: unknown): string {
  if (r == null) return "";
  if (typeof r === "string") return r.slice(0, 240);
  if (Array.isArray(r)) return `数组结果 · ${r.length} 项`;
  if (typeof r === "object") {
    const keys = Object.keys(r as Record<string, unknown>);
    return `对象结果 · ${keys.slice(0, 8).join(", ")}${keys.length > 8 ? "…" : ""}`;
  }
  try {
    const s = JSON.stringify(r);
    if (s.length < 200) return s;
    return s.slice(0, 200) + "…";
  } catch {
    return String(r);
  }
}

function formatPreview(value: unknown, maxChars: number): string {
  try {
    const text =
      typeof value === "string" ? value : JSON.stringify(value, null, 2);
    return text.length > maxChars ? `${text.slice(0, maxChars)}\n…` : text;
  } catch {
    return String(value);
  }
}

function useNearViewport<T extends Element>() {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { rootMargin: "600px 0px" },
    );
    obs.observe(node);
    return () => obs.disconnect();
  }, []);

  return { ref, visible };
}
