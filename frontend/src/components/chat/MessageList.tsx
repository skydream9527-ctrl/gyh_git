import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
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
}

/**
 * Sticky-bottom 滚动：
 * - 用户在底部 80px 以内 → 自动跟随；流式中用 instant 滚动避开多次 smooth 互相打架
 * - 用户向上翻 → 不再 yank 回底部，留出阅读空间
 * - 用户手动滚回底部 → 自动恢复跟随
 * - 流式结束 / 切换对话时用 smooth，让最终落点有缓动
 */
export function MessageList({ finalized, partial, phase, onCrystallize }: Props) {
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

  return (
    <div className="msg-list-wrap">
      <div className="msg-list" ref={scrollRef}>
        <FinalizedList items={finalized} onCrystallize={onCrystallize} />
        {partial && (
          <AssistantBubble
            content={partial.content}
            toolCalls={partial.toolCalls}
            streaming
          />
        )}
        {phase === "typing" && !partial && <TypingDots />}
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

const FinalizedList = memo(function FinalizedList({
  items,
  onCrystallize,
}: {
  items: ChatMessage[];
  onCrystallize?: (msg: ChatMessage) => void;
}) {
  return (
    <>
      {items.map((m) =>
        m.role === "user" ? (
          <UserBubble key={m.id} content={m.content} />
        ) : (
          <FinalizedAssistant
            key={m.id}
            message={m}
            onCrystallize={onCrystallize}
          />
        ),
      )}
    </>
  );
});

// 把 message → toolCalls 的转换移到组件里，并且用 memo 包一层；
// onCrystallize 父级用 useCallback 维持稳定引用，单条历史就不会因为流式
// 而无谓重渲染了。
const FinalizedAssistant = memo(
  function FinalizedAssistant({
    message,
    onCrystallize,
  }: {
    message: ChatMessage;
    onCrystallize?: (msg: ChatMessage) => void;
  }) {
    const handle = onCrystallize ? () => onCrystallize(message) : undefined;
    const calls: ToolCall[] = (message.tool_uses || []).map((t) => ({
      tool_call_id: t.id,
      tool_name: t.name,
      arguments: t.input as Record<string, unknown>,
      status: "done",
    }));
    return (
      <AssistantBubble
        content={message.content}
        toolCalls={calls}
        onCrystallize={handle}
      />
    );
  },
  (a, b) =>
    a.message.id === b.message.id &&
    a.message.content === b.message.content &&
    a.message.tool_uses?.length === b.message.tool_uses?.length &&
    a.onCrystallize === b.onCrystallize,
);

const UserBubble = memo(function UserBubble({ content }: { content: string }) {
  return (
    <div className="bubble-row user">
      <div className="bubble user-bubble">{content}</div>
    </div>
  );
});

interface AssistantBubbleProps {
  content: string;
  toolCalls: ToolCall[];
  streaming?: boolean;
  onCrystallize?: () => void;
}

function AssistantBubbleImpl({
  content,
  toolCalls,
  streaming,
  onCrystallize,
}: AssistantBubbleProps) {
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

  const copy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
      } else {
        const ta = document.createElement("textarea");
        ta.value = content;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopied(true);
      if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
      copyTimerRef.current = window.setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      pushToast("error", `复制失败：${(err as Error).message}`);
    }
  };

  // 移动端默认折叠工具执行细节，只展示结论；桌面端 CSS 强制展开。
  // 流式过程中默认展开，让用户能看到正在跑的步骤；流式结束后折叠回去。
  const [toolsExpanded, setToolsExpanded] = useState<boolean>(!!streaming);
  useEffect(() => {
    if (!streaming) setToolsExpanded(false);
  }, [streaming]);

  return (
    <div className="bubble-row assistant">
      <div className="agent-avatar">🤖</div>
      <div className="bubble assistant-bubble">
        {content && <MarkdownRenderer content={content} streaming={streaming} />}
        {streaming && content && <span className="cursor" />}
        {toolCalls.length > 0 && (
          <div className={`tool-calls-block ${toolsExpanded ? "expanded" : ""}`}>
            <button
              type="button"
              className="tool-calls-toggle"
              onClick={() => setToolsExpanded((v) => !v)}
              aria-expanded={toolsExpanded}
              title={toolsExpanded ? "折叠工具执行" : "展开工具执行"}
            >
              🔧 {toolCalls.length} 步工具执行 {toolsExpanded ? "▲" : "▼"}
            </button>
            <div className="tool-calls-body">
              {toolCalls.map((tc) => (
                <ToolCallCard key={tc.tool_call_id} call={tc} />
              ))}
            </div>
          </div>
        )}
        {!streaming && content && (
          <div className="msg-actions">
            <button
              className="msg-action-btn"
              onClick={copy}
              title="复制原文到剪贴板"
            >
              {copied ? "✅ 已复制" : "📋 复制"}
            </button>
            {voiceEnabled && <VoicePlayButton text={content} />}
            {onCrystallize && (
              <button
                className="msg-action-btn"
                onClick={onCrystallize}
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

const AssistantBubble = memo(AssistantBubbleImpl);

function TypingDots() {
  return (
    <div className="typing-dots">
      <span /> <span /> <span />
    </div>
  );
}
