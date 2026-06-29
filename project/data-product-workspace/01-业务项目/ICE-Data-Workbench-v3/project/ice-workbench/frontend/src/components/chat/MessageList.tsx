import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ChatMessage, ToolCall } from "@/types/api";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { ToolCallCard } from "./ToolCallCard";
import { VoicePlayButton } from "./VoicePlayButton";
import { useUIStore } from "@/stores/uiStore";
import type { PartialAssistant, StreamPhase } from "@/hooks/useChatSocket";
import "./MessageList.css";

interface Props {
  finalized: ChatMessage[];
  partial: PartialAssistant | null;
  phase: StreamPhase;
  onCrystallize?: (msg: ChatMessage) => void;
  /** 当前 conv 后端 _inflight_turns 仍在跑，但本 WS 没在收 stream（典型场景：
   * 用户切走又切回，旧任务还在后台跑）。开启后底部强制显示 Thinking 横幅，
   * 避免用户以为任务停了。 */
  backgroundInflight?: boolean;
}

/**
 * Sticky-bottom 滚动：
 * - 用户在底部 80px 以内 → 自动跟随；流式中用 instant 滚动避开多次 smooth 互相打架
 * - 用户向上翻 → 不再 yank 回底部，留出阅读空间
 * - 用户手动滚回底部 → 自动恢复跟随
 * - 流式结束 / 切换对话时用 smooth，让最终落点有缓动
 */
export function MessageList({ finalized, partial, phase, onCrystallize, backgroundInflight }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      const stuck = distance < 80;
      stickRef.current = stuck;
      setShowJump(!stuck);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // 切对话时强制粘底重置（finalized 长度归零或大幅变化）
  const lastLenRef = useRef(0);
  useLayoutEffect(() => {
    if (finalized.length < lastLenRef.current) {
      stickRef.current = true;
      setShowJump(false);
    }
    lastLenRef.current = finalized.length;
  }, [finalized.length]);

  useLayoutEffect(() => {
    if (!stickRef.current) return;
    const el = scrollRef.current;
    if (!el) return;
    const streaming = phase === "streaming" || phase === "tool" || phase === "typing";
    const behavior: ScrollBehavior = streaming ? "auto" : "smooth";
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, [finalized.length, partial?.content, partial?.toolCalls.length, phase]);

  const jumpToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = true;
    setShowJump(false);
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  // 把 finalized + partial 合并成「轮次组」：一条 user 消息 + 它后面所有连续的
  // assistant 消息合成一个 turn 气泡。后端 5-round 工具循环每轮写一条
  // assistant_record，旧实现按 message_id 拆成 N 个气泡，导致截图里看到的
  // "🔧 2 步工具执行" / "🔧 2 步工具执行" / "🔧 3 步工具执行" 一连串碎片。
  // 这里在渲染层把它们捏回一个气泡，工具卡内联，符合 Claude Code 的流畅感。
  const turns = useMemo(() => buildTurns(finalized, partial), [finalized, partial]);

  const showThinking =
    ((phase === "typing" || phase === "tool" || phase === "streaming") &&
      (!partial || (!partial.content && partial.toolCalls.length === 0))) ||
    // 切走又切回的场景：本 WS 没在 stream 但后端任务还在跑 → 强制显示
    !!backgroundInflight;

  return (
    <div className="msg-list-wrap">
      <div className="msg-list" ref={scrollRef}>
        {turns.map((t) =>
          t.kind === "user" ? (
            <UserBubble key={t.key} content={t.content} />
          ) : (
            <AssistantTurnBubble
              key={t.key}
              messages={t.messages}
              partial={t.partial}
              onCrystallize={onCrystallize}
            />
          ),
        )}
        {showThinking && (
          <ThinkingIndicator
            label={
              backgroundInflight && !["streaming", "tool", "typing"].includes(phase)
                ? "后台仍在生成回复…完成后将自动写入"
                : "Thinking"
            }
          />
        )}
      </div>
      {showJump && (
        <button
          type="button"
          className="msg-jump-bottom"
          onClick={jumpToBottom}
          aria-label="回到底部"
          title="回到底部"
        >
          ↓ 最新
        </button>
      )}
    </div>
  );
}

// ---- 轮次分组 ----------------------------------------------------------

type Turn =
  | { kind: "user"; key: string; content: string }
  | {
      kind: "assistant";
      key: string;
      messages: ChatMessage[];
      partial?: PartialAssistant;
    };

function buildTurns(
  finalized: ChatMessage[],
  partial: PartialAssistant | null,
): Turn[] {
  const turns: Turn[] = [];
  for (const m of finalized) {
    if (m.role === "user") {
      turns.push({ kind: "user", key: m.id, content: m.content });
    } else if (m.role === "assistant") {
      const last = turns[turns.length - 1];
      if (last && last.kind === "assistant") {
        last.messages.push(m);
      } else {
        turns.push({ kind: "assistant", key: m.id, messages: [m] });
      }
    }
  }
  if (partial) {
    const last = turns[turns.length - 1];
    if (last && last.kind === "assistant") {
      last.partial = partial;
    } else {
      turns.push({
        kind: "assistant",
        key: `partial-${partial.id}`,
        messages: [],
        partial,
      });
    }
  }
  return turns;
}

// ---- User 气泡 ---------------------------------------------------------

const UserBubble = memo(function UserBubble({ content }: { content: string }) {
  return (
    <div className="bubble-row user">
      <div className="bubble user-bubble">{content}</div>
    </div>
  );
});

// ---- Assistant 轮次气泡（多 round 合并）-------------------------------

interface AssistantTurnBubbleProps {
  messages: ChatMessage[];
  partial?: PartialAssistant;
  onCrystallize?: (msg: ChatMessage) => void;
}

function AssistantTurnBubbleImpl({
  messages,
  partial,
  onCrystallize,
}: AssistantTurnBubbleProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const voiceEnabled = useUIStore((s) => s.voiceEnabled);
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
    },
    [],
  );

  const streaming = !!partial;

  // 工具卡默认收起（chip 可点开），流式中保持展开让用户看到正在跑的工具
  const [toolsExpanded, setToolsExpanded] = useState<boolean>(streaming);
  useEffect(() => {
    if (!streaming) setToolsExpanded(false);
  }, [streaming]);

  // 按时间顺序铺开：每个 message 的 content + tool_uses 各自渲染；
  // partial 作为最后一段（带光标）。工具卡统一在底部一个 chip。
  // 之所以不混在文本里，是因为后端持久化的 tool_uses 顺序与 content 间没有
  // 严格的"穿插"信号（tool_use_index 是回合级的），按段落划开最稳。
  const segments = useMemo(() => {
    const out: { id: string; content: string; isPartial?: boolean }[] = [];
    for (const m of messages) {
      if (m.content && m.content.trim()) {
        out.push({ id: m.id, content: m.content });
      }
    }
    if (partial && partial.content) {
      out.push({ id: partial.id, content: partial.content, isPartial: true });
    }
    return out;
  }, [messages, partial]);

  const allToolCalls = useMemo<ToolCall[]>(() => {
    const out: ToolCall[] = [];
    for (const m of messages) {
      for (const t of m.tool_uses || []) {
        out.push({
          tool_call_id: t.id,
          tool_name: t.name,
          arguments: t.input as Record<string, unknown>,
          status: "done",
        });
      }
    }
    if (partial) {
      for (const t of partial.toolCalls) {
        out.push({
          tool_call_id: t.tool_call_id,
          tool_name: t.tool_name,
          display_name: t.display_name,
          arguments: t.arguments,
          status: t.status,
        });
      }
    }
    return out;
  }, [messages, partial]);

  // 复制：合并所有段落原文（不含工具调用细节）
  const combinedText = useMemo(
    () => segments.map((s) => s.content).join("\n\n"),
    [segments],
  );

  const copy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(combinedText);
      } else {
        const ta = document.createElement("textarea");
        ta.value = combinedText;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopied(true);
      pushToast("success", "已复制到剪贴板");
      if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
      copyTimerRef.current = window.setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      pushToast("error", `复制失败：${(err as Error).message}`);
    }
  };

  // 沉淀经验：拿最后一条 finalized assistant 消息（最贴近"结论"那条）
  const crystallizeTarget = messages.length > 0 ? messages[messages.length - 1] : null;
  const handleCrystallize =
    onCrystallize && crystallizeTarget
      ? () => onCrystallize(crystallizeTarget)
      : undefined;

  return (
    <div className="bubble-row assistant">
      <div className="agent-avatar">🤖</div>
      <div className={`bubble assistant-bubble${streaming ? " streaming" : ""}`}>
        {segments.length > 0 ? (
          segments.map((s, i) => (
            <div key={`${s.id}-${i}`} className="turn-segment">
              <MarkdownRenderer content={s.content} streaming={!!s.isPartial} />
              {s.isPartial && <span className="cursor" />}
            </div>
          ))
        ) : streaming ? (
          // 流式开始但还没文字、只有工具在跑：占位提示，避免空气泡
          <div className="turn-running-hint">正在执行工具…</div>
        ) : null}

        {allToolCalls.length > 0 && (
          <div className={`tool-calls-block ${toolsExpanded ? "expanded" : ""}`}>
            <button
              type="button"
              className="tool-calls-toggle"
              onClick={() => setToolsExpanded((v) => !v)}
              aria-expanded={toolsExpanded}
              title={toolsExpanded ? "折叠工具执行" : "展开工具执行"}
            >
              🔧 {allToolCalls.length} 步工具执行 {toolsExpanded ? "▲" : "▼"}
            </button>
            <div className="tool-calls-body">
              {allToolCalls.map((tc) => (
                <ToolCallCard key={tc.tool_call_id} call={tc} />
              ))}
            </div>
          </div>
        )}

        {!streaming && combinedText && (
          <div className="msg-actions">
            <button
              className="msg-action-btn"
              onClick={copy}
              title="复制本回合所有结论文本"
            >
              {copied ? "✅ 已复制" : "📋 复制"}
            </button>
            {voiceEnabled && <VoicePlayButton text={combinedText} />}
            {handleCrystallize && (
              <button
                className="msg-action-btn"
                onClick={handleCrystallize}
                title="把这条洞察沉淀为 Agent 经验"
              >
                ✨ 沉淀经验
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const AssistantTurnBubble = memo(
  AssistantTurnBubbleImpl,
  (a, b) =>
    a.messages.length === b.messages.length &&
    a.messages.every((m, i) => {
      const bm = b.messages[i];
      return (
        bm &&
        m.id === bm.id &&
        m.content === bm.content &&
        (m.tool_uses?.length ?? 0) === (bm.tool_uses?.length ?? 0)
      );
    }) &&
    a.partial?.id === b.partial?.id &&
    a.partial?.content === b.partial?.content &&
    a.partial?.toolCalls.length === b.partial?.toolCalls.length &&
    a.onCrystallize === b.onCrystallize,
);

// ---- 思考中指示器 ------------------------------------------------------

function ThinkingIndicator({ label = "Thinking" }: { label?: string }) {
  return (
    <div className="thinking-indicator" aria-live="polite" aria-label="Agent 正在思考">
      <span className="thinking-emoji">💭</span>
      <span className="thinking-label">{label}</span>
      <span className="thinking-dots">
        <i /><i /><i />
      </span>
    </div>
  );
}
