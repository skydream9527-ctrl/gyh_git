import type { RefObject } from "react";
import { ChatInput } from "@/components/chat/ChatInput";
import type { ChatInputRef } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { ErrorState } from "@/components/feedback/ErrorState";
import AgentUpdateBanner from "@/components/task/AgentUpdateBanner";
import { V6HumanInterventionCard } from "./components/HumanInterventionCard";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { WorkspaceChatHead } from "./WorkspaceChatHead";
import type { WorkspaceChatHeadProps } from "./WorkspaceChatHead";
import type { AgentCard, ChatMessage, FileMeta, HitlRequest, TaskDetail, ToolCall } from "@/types/api";

export interface WorkspaceChatAreaProps {
  task: TaskDetail;
  taskId: string;
  agent: AgentCard | null;
  role: "owner" | "editor" | "viewer" | "admin" | null;
  canWrite: boolean;
  isViewer: boolean;
  // Chat head props
  chatHeadProps: WorkspaceChatHeadProps;
  // Socket-derived
  allMessages: ChatMessage[];
  partial: { id: string; content: string; toolCalls: Array<any> } | null;
  phase: "idle" | "streaming" | "tool" | "typing" | "done" | "error";
  wsErrCode: string | null;
  wsCloseInfo: { code: number; reason?: string } | null;
  isStreaming: boolean;
  planMode: boolean;
  pendingPlan: any;
  toolOverrides: Record<string, any>;
  // Conversation state
  conversationId: string | null;
  conversationLocked: boolean;
  lockedByOther: boolean;
  lockedBySelfElsewhere: boolean;
  inflight: { id: string; name: string } | null;
  // HITL
  hitlRequests: HitlRequest[];
  hitlBusy: boolean;
  taskNeedsHuman: boolean;
  // KB
  kbImportedFiles: FileMeta[];
  // Files for ChatInput
  files: FileMeta[];
  // Refs
  chatInputRef: RefObject<ChatInputRef>;
  // Voice
  voiceEnabled: boolean | null;
  // Access
  editAccessRequested: boolean;
  // History
  historyHasMore: boolean;
  historyLoadingOlder: boolean;
  // Background
  backgroundInflight: boolean;
  // Handlers
  onSend: (text: string) => void;
  onAbort: () => void;
  onRetryToolCall: (call: ToolCall) => void;
  onCrystallize: (m: ChatMessage) => void;
  onLoadOlderHistory: () => void;
  onSetPlanMode: (v: boolean) => void;
  onNewConvFromLock: () => void;
  onRequestEditAccess: () => void;
  onSetActiveRightTab: (tab: string) => void;
  onResolveHitl: (payload: Record<string, unknown>, decision: string, note?: string) => void;
  onTaskUpdated: () => Promise<void>;
  onAbortConversation: () => Promise<void>;
  onRefreshTaskData: () => void;
  onClearError: () => void;
  onRemoveFile: (f: FileMeta) => void;
  onVoiceConvOpen: () => void;
  model: string;
  pushToast: (type: "success" | "error" | "info", msg: string) => void;
}

export function WorkspaceChatArea({
  task,
  taskId,
  agent,
  role,
  canWrite,
  isViewer,
  chatHeadProps,
  allMessages,
  partial,
  phase,
  wsErrCode,
  wsCloseInfo,
  isStreaming,
  planMode,
  pendingPlan,
  toolOverrides,
  conversationId,
  conversationLocked,
  lockedByOther,
  lockedBySelfElsewhere,
  inflight,
  hitlRequests,
  hitlBusy,
  taskNeedsHuman,
  kbImportedFiles,
  files,
  chatInputRef,
  voiceEnabled,
  editAccessRequested,
  historyHasMore,
  historyLoadingOlder,
  backgroundInflight,
  onSend,
  onAbort,
  onRetryToolCall,
  onCrystallize,
  onLoadOlderHistory,
  onSetPlanMode,
  onNewConvFromLock,
  onRequestEditAccess,
  onSetActiveRightTab,
  onResolveHitl,
  onTaskUpdated,
  onAbortConversation,
  onRefreshTaskData,
  onClearError,
  onRemoveFile,
  onVoiceConvOpen,
  model,
  pushToast: _pushToast,
}: WorkspaceChatAreaProps) {
  return (
    <main className="ws-main">
      <WorkspaceChatHead {...chatHeadProps} />
      <AgentUpdateBanner
        task={task}
        isOwnerOrAdmin={role === "owner" || role === "admin"}
        onUpdated={onTaskUpdated}
      />
      {taskNeedsHuman && (
        <V6HumanInterventionCard
          taskName={task.name}
          request={hitlRequests[0] || null}
          busy={hitlBusy}
          onOpenSandbox={() => onSetActiveRightTab("agent")}
          onContinue={(payload, decision, note) => onResolveHitl(payload, decision, note)}
        />
      )}
      {wsErrCode && (
        <div className="ws-banner">
          <ErrorState
            icon="⚠"
            title="对话异常"
            description={
              wsErrCode === "LLM_KEY_MISSING"
                ? "LLM API Key 未配置，请在 .env 填入 ANTHROPIC_API_KEY 后重启后端"
                : wsErrCode === "WS_DISCONNECTED"
                  ? "WebSocket 已断开，正在尝试重连…"
                  : wsErrCode === "STREAM_INTERRUPTED"
                    ? `回复期间连接中断${
                        wsCloseInfo
                          ? `（close=${wsCloseInfo.code}${
                              wsCloseInfo.reason ? ` "${wsCloseInfo.reason}"` : ""
                            }）`
                          : ""
                      }；后台任务可能仍在继续。可点「⏹ 终止后台任务」停止，或「🔁 重新加载」拉取最新结果`
                    : wsErrCode === "CONVERSATION_INFLIGHT"
                      ? "上一轮回复仍在后台进行中；点「⏹ 终止后台任务」中断后才能发新消息"
                      : "请稍后重试"
            }
            errorCode={wsErrCode}
            actions={
              <>
                {(wsErrCode === "STREAM_INTERRUPTED" ||
                  wsErrCode === "CONVERSATION_INFLIGHT") &&
                  conversationId && (
                    <button
                      className="btn-secondary"
                      onClick={onAbortConversation}
                      title="HTTP 通道终止后台正在跑的 LLM 回合"
                    >
                      ⏹ 终止后台任务
                    </button>
                  )}
                <button className="btn-secondary" onClick={onRefreshTaskData}>
                  🔁 重新加载
                </button>
                <button className="btn-secondary" onClick={onClearError}>
                  我知道了
                </button>
              </>
            }
          />
        </div>
      )}
      {allMessages.length === 0 && !partial && (
        <WelcomeScreen agent={agent} onSendStarter={onSend} />
      )}
      <MessageList
        finalized={allMessages}
        partial={partial}
        phase={phase}
        historyHasMore={historyHasMore}
        historyLoading={historyLoadingOlder}
        onLoadOlder={onLoadOlderHistory}
        toolOverrides={toolOverrides}
        onRetryToolCall={onRetryToolCall}
        onCrystallize={onCrystallize}
        backgroundInflight={backgroundInflight}
      />
      {planMode && !pendingPlan && (
        <div className="plan-mode-banner">
          <span>🧭 当前处于 Plan Mode：agent 只能只读调研，调 exit_plan_mode 后等你批准</span>
          <button
            className="plan-mode-banner__exit"
            onClick={() => onSetPlanMode(false)}
          >
            退出 Plan Mode
          </button>
        </div>
      )}
      {lockedByOther && inflight && (
        <div className="conv-locked-banner conv-locked-banner--other" role="alert">
          <span>
            🔒 用户 <b>{inflight.name}</b> 正在对话中，请新建对话或联系 TA 结束任务
          </span>
          <button
            type="button"
            className="conv-locked-banner__action"
            onClick={onNewConvFromLock}
            title="为本任务新开一条独立对话，与对方互不干扰"
          >
            ＋ 新建对话
          </button>
        </div>
      )}
      {lockedBySelfElsewhere && (
        <div className="conv-locked-banner conv-locked-banner--self" role="status">
          <span>🔒 你的另一个标签页或设备正在该对话中，等当前回合结束再发新消息</span>
        </div>
      )}
      {kbImportedFiles.length > 0 && (
        <div className="kb-ref-chips" role="list" aria-label="已引用的知识库文档">
          <span className="kb-ref-chips__label">📎 已引用</span>
          {kbImportedFiles.map((f) => (
            <span key={f.id} className="kb-ref-chip" role="listitem">
              <button
                type="button"
                className="kb-ref-chip__name"
                title="点击在输入框插入 @ 引用"
                onClick={() => {
                  chatInputRef.current?.insertText(`@${f.name} `);
                  chatInputRef.current?.focus();
                }}
              >
                {f.name}
              </button>
              {canWrite && (
                <button
                  type="button"
                  className="kb-ref-chip__close"
                  title="取消引用（移除该任务文件）"
                  onClick={() => onRemoveFile(f)}
                  aria-label={`取消引用 ${f.name}`}
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      )}
      <ChatInput
        ref={chatInputRef}
        paradigm={task.paradigm}
        disabled={
          !conversationId ||
          Boolean(pendingPlan) ||
          conversationLocked
        }
        isStreaming={isStreaming}
        onSend={onSend}
        onAbort={onAbort}
        onVoiceConversation={
          voiceEnabled && conversationId
            ? () => onVoiceConvOpen()
            : undefined
        }
        files={files.map((f) => ({ id: f.file_id ?? f.id, name: f.name }))}
        viewerMode={isViewer}
        onRequestEditAccess={onRequestEditAccess}
        editAccessRequested={editAccessRequested}
      />
      {canWrite && (
        <div className="plan-toggle-row" style={{ display: "flex", gap: 8, padding: "0 16px 12px", alignItems: "center" }}>
          <button
            onClick={() => onSetPlanMode(!planMode)}
            className={planMode ? "plan-toggle active" : "plan-toggle"}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              borderRadius: 6,
              border: "1px solid " + (planMode ? "var(--warning)" : "var(--border-strong)"),
              background: planMode ? "var(--warning-soft)" : "var(--surface)",
              color: planMode ? "var(--warning)" : "var(--text-dim)",
              cursor: "pointer",
            }}
            disabled={!conversationId}
            title="计划模式：agent 先出方案，你批准后再执行"
          >
            🧭 {planMode ? "Plan Mode ON" : "进入 Plan Mode"}
          </button>
        </div>
      )}
    </main>
  );
}
