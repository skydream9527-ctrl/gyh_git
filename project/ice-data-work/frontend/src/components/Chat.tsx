import { useEffect, useRef, useState } from "react";
import type { ChatTurn, Speaker } from "@/hooks/useTaskSocket";

function speakerLabel(s: Speaker): { avatar: string; name: string; cls: string } {
  if (s.type === "user") return { avatar: "我", name: "我", cls: "user" };
  if (s.type === "twin") return { avatar: "TW", name: "我的 Twin", cls: "twin" };
  if (s.id === "system") return { avatar: "⚙", name: "系统", cls: "system" };
  return { avatar: s.id.slice(0, 2).toUpperCase(), name: s.id, cls: "agent" };
}

interface RunData {
  stdout?: string;
  stderr?: string;
  exit_code?: number | null;
  timed_out?: boolean;
  duration_ms?: number;
  generated_files?: string[];
}

interface ToolResult {
  ok?: boolean;
  error_code?: string;
  message?: string;
  data?: RunData;
}

/** 工具调用卡：run_user_code 展示沙盒输出/产物/状态，其余工具展示名称+状态。 */
function ToolCard({ tc }: { tc: { tool: string; args: unknown; result?: unknown } }) {
  const r = (tc.result as ToolResult | undefined) ?? {};
  const ok = r.ok !== false;
  const isRun = tc.tool === "run_user_code";
  const data: RunData = r.data ?? {};
  const statusText = ok ? "成功" : r.error_code || "失败";
  const output = [data.stdout, data.stderr ? `[stderr] ${data.stderr}` : ""].filter(Boolean).join("\n");
  return (
    <div className={`tool-card ${ok ? "" : "tool-error"}`}>
      <div className="tool-head">
        <span className="tool-icon">{isRun ? "🐍" : "🔧"}</span>
        <span className="tool-name">{tc.tool}</span>
        <span className={`tool-status ${ok ? "ok" : "err"}`}>{statusText}</span>
        {isRun && typeof data.duration_ms === "number" && (
          <span className="tool-meta">{data.duration_ms}ms</span>
        )}
      </div>
      {isRun && output && <pre className="tool-output">{output.slice(0, 4000)}</pre>}
      {isRun && (data.generated_files?.length ?? 0) > 0 && (
        <div className="tool-files">产物：{data.generated_files!.join(", ")}</div>
      )}
      {isRun && !ok && r.message && <div className="tool-msg">{r.message}</div>}
    </div>
  );
}

interface ChatProps {
  turns: ChatTurn[];
  thinking: boolean;
  connected: boolean;
  onSend: (content: string, mentioned?: string) => void;
}

export default function Chat({ turns, thinking, connected, onSend }: ChatProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="chat">
      <div className="chat-stream" ref={scrollRef}>
        {turns.length === 0 && (
          <div className="chat-empty">
            开始对话。你的 Twin 会编排合适的 Agent 协作完成任务。
          </div>
        )}
        {turns.map((turn) => {
          const sl = speakerLabel(turn.speaker);
          const isUser = turn.speaker.type === "user";
          return (
            <div key={turn.id} className={`chat-turn ${isUser ? "from-user" : "from-agent"}`}>
              <div className={`chat-avatar ${sl.cls}`}>{sl.avatar}</div>
              <div className="chat-bubble">
                <div className="chat-speaker-name">{sl.name}</div>
                {turn.tool_calls?.map((tc, i) => (
                  <ToolCard key={i} tc={tc} />
                ))}
                <div className="chat-content">
                  {turn.content}
                  {turn.streaming && <span className="cursor">▋</span>}
                </div>
              </div>
            </div>
          );
        })}
        {thinking && turns.every((t) => !t.streaming) && (
          <div className="chat-thinking">正在思考…</div>
        )}
      </div>

      <div className="chat-input-bar">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={connected ? "输入消息，Enter 发送（Shift+Enter 换行）" : "连接中…"}
          rows={2}
          disabled={!connected}
        />
        <button className="btn-primary" onClick={handleSend} disabled={!connected || !input.trim()}>
          发送
        </button>
      </div>
    </div>
  );
}
