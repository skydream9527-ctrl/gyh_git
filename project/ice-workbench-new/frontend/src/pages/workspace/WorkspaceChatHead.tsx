/**
 * Chat header bar: model selector + export/copy/reload action buttons.
 */
import { ModelSelector } from "@/components/chat/ModelSelector";

export interface WorkspaceChatHeadProps {
  model: string;
  onModelChange: (m: string) => void;
  onExport: () => void;
  onReload: () => void;
  loadMessagesForBulkAction: () => Promise<any[]>;
  pushToast: (type: "success" | "error" | "info", msg: string) => void;
}

export function WorkspaceChatHead({ model, onModelChange, onExport, onReload, loadMessagesForBulkAction, pushToast }: WorkspaceChatHeadProps) {
  return (
    <div className="ws-chat-head">
      <span className="model">
        📦 <ModelSelector value={model} onChange={onModelChange} compact />
      </span>
      <button
        className="btn-ghost ws-sec-action"
        onClick={onExport}
        title="把当前对话（含工具调用）导出为 Markdown 下载"
      >
        💾 导出对话
      </button>
      <button
        className="btn-ghost ws-sec-action"
        onClick={async () => {
          try {
            const messages = await loadMessagesForBulkAction();
            const text = messages
              .map((m: any) => {
                const role =
                  m.role === "user" ? "👤 用户" : m.role === "assistant" ? "🤖 Agent" : m.role;
                return `## ${role}\n\n${m.content || ""}`;
              })
              .join("\n\n---\n\n");
            if (navigator.clipboard?.writeText) {
              await navigator.clipboard.writeText(text);
            } else {
              const ta = document.createElement("textarea");
              ta.value = text;
              ta.style.position = "fixed";
              ta.style.opacity = "0";
              document.body.appendChild(ta);
              ta.select();
              document.execCommand("copy");
              document.body.removeChild(ta);
            }
            pushToast("success", `已复制 ${messages.length} 条对话到剪贴板`);
          } catch (err) {
            pushToast("error", `复制失败：${(err as Error).message}`);
          }
        }}
        title="把整个对话（用户 + Agent 回复）复制到剪贴板"
      >
        📋 复制对话
      </button>
      <button
        className="btn-ghost ws-sec-action"
        onClick={onReload}
        title="重新拉取任务详情 / 对话历史 / 文件（保持 WS 连接）"
      >
        🔁 重新加载
      </button>
    </div>
  );
}
