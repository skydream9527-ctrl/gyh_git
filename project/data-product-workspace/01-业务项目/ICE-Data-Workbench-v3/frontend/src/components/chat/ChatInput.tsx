import {
  KeyboardEvent,
  forwardRef,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useUIStore } from "@/stores/uiStore";
import "./ChatInput.css";

export interface ChatInputRef {
  /** 在当前光标位置插入一段文本（不带前后空格处理，调用方按需自带）。 */
  insertText: (text: string) => void;
  focus: () => void;
}

export interface FileMention {
  id: string;
  name: string;
}

interface Props {
  paradigm?: string;
  disabled?: boolean;
  isStreaming?: boolean;
  onSend: (text: string) => void;
  onAbort?: () => void;
  /** Open the voice-conversation overlay. If undefined the 🎙 button is
   * not rendered (legacy / non-voice contexts). */
  onVoiceConversation?: () => void;
  /** 工作区文件列表，用于 @ 提及自动补全。空/undefined 关闭功能。 */
  files?: FileMention[];
  /** 只读视角：textarea 与 OK/发送 全部置灰；改为展示「申请编辑权限」按钮 */
  viewerMode?: boolean;
  /** viewer 点「申请编辑权限」时调用 */
  onRequestEditAccess?: () => void;
  /** viewer 已经提交过 join request 的状态，按钮显示 pending */
  editAccessRequested?: boolean;
}

const PARADIGM_PLACEHOLDER: Record<string, string> = {
  biz: "描述你的经营分析问题，比如：上周 DAU 下滑的原因…",
  ab: "描述你的实验，比如：v2.3 新版的留存影响…",
  wave: "描述指标异常，比如：周末转化率突然下降…",
  data: "用自然语言描述查询，比如：本月各渠道的 ARPU…",
  gray: "描述灰度版本对比，比如：v1.5 vs v1.4 的留存差异…",
};

const MIN_HEIGHT = 70;
const MAX_HEIGHT = 240;

export const ChatInput = forwardRef<ChatInputRef, Props>(function ChatInput(
  {
    paradigm = "biz",
    disabled,
    isStreaming,
    onSend,
    onAbort,
    onVoiceConversation,
    files,
    viewerMode,
    onRequestEditAccess,
    editAccessRequested,
  },
  ref,
) {
  // viewer 视角：textarea 强制 disabled，发送按钮置灰，改为申请权限按钮
  const effectiveDisabled = !!disabled || !!viewerMode;
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const voiceEnabled = useUIStore((s) => s.voiceEnabled);
  // IME 组字态。Mac 中文输入法下，用户拼拼音时按 Enter 是"上屏候选词"，
  // 不应触发发送。同时监听 React 合成事件 + nativeEvent.isComposing + keyCode=229，
  // 三者任一命中都视作组字中（不同浏览器/输入法的信号不一致）。
  const composingRef = useRef(false);

  // @ 提及浮层状态
  const [mentionQuery, setMentionQuery] = useState<string | null>(null); // null = 关闭
  const [mentionStart, setMentionStart] = useState<number>(-1); // @ 在 textarea 中的位置
  const [mentionIdx, setMentionIdx] = useState<number>(0);

  // 自动撑高：内容 ≤ MAX_HEIGHT 时贴合 scrollHeight，超过启用滚动条
  useLayoutEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, el.scrollHeight));
    el.style.height = next + "px";
  }, [value]);

  useImperativeHandle(
    ref,
    () => ({
      insertText: (text: string) => {
        const el = taRef.current;
        if (!el) {
          setValue((v) => v + text);
          return;
        }
        const start = el.selectionStart ?? value.length;
        const end = el.selectionEnd ?? value.length;
        const next = value.slice(0, start) + text + value.slice(end);
        setValue(next);
        // 光标移到插入文本后
        requestAnimationFrame(() => {
          el.focus();
          const cursor = start + text.length;
          el.setSelectionRange(cursor, cursor);
        });
      },
      focus: () => taRef.current?.focus(),
    }),
    [value],
  );

  const filteredMentions = useMemo(() => {
    if (mentionQuery == null || !files || files.length === 0) return [];
    const q = mentionQuery.trim().toLowerCase();
    if (!q) return files.slice(0, 8);
    return files
      .filter((f) => f.name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [mentionQuery, files]);

  const updateMentionState = (next: string, cursor: number) => {
    if (!files || files.length === 0) {
      setMentionQuery(null);
      return;
    }
    // 向左找最近的 @；@ 前必须是空白或起始位置；@ 与光标之间不允许空格/换行
    let i = cursor - 1;
    while (i >= 0) {
      const ch = next[i];
      if (ch === "@") break;
      if (ch === " " || ch === "\n" || ch === "\t") {
        setMentionQuery(null);
        return;
      }
      i--;
    }
    if (i < 0) {
      setMentionQuery(null);
      return;
    }
    const before = i === 0 ? "" : next[i - 1];
    if (before && !/\s/.test(before)) {
      // 邮箱、@username 等情况不触发
      setMentionQuery(null);
      return;
    }
    const q = next.slice(i + 1, cursor);
    setMentionQuery(q);
    setMentionStart(i);
    setMentionIdx(0);
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const next = e.target.value;
    setValue(next);
    const cursor = e.target.selectionStart ?? next.length;
    updateMentionState(next, cursor);
  };

  const insertMention = (file: FileMention) => {
    const el = taRef.current;
    if (!el || mentionStart < 0) return;
    const cursor = el.selectionStart ?? value.length;
    const before = value.slice(0, mentionStart);
    const after = value.slice(cursor);
    const insert = `@${file.name} `;
    const next = before + insert + after;
    setValue(next);
    setMentionQuery(null);
    requestAnimationFrame(() => {
      el.focus();
      const pos = before.length + insert.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 浮层按键优先
    if (mentionQuery != null && filteredMentions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setMentionIdx((i) => (i + 1) % filteredMentions.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setMentionIdx((i) => (i - 1 + filteredMentions.length) % filteredMentions.length);
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        const ne = e.nativeEvent as unknown as { isComposing?: boolean; keyCode?: number };
        if (composingRef.current || ne.isComposing || ne.keyCode === 229) return;
        e.preventDefault();
        insertMention(filteredMentions[mentionIdx]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setMentionQuery(null);
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        insertMention(filteredMentions[mentionIdx]);
        return;
      }
    }
    if (e.key !== "Enter" || e.shiftKey) return;
    const ne = e.nativeEvent as unknown as { isComposing?: boolean; keyCode?: number };
    if (composingRef.current || ne.isComposing || ne.keyCode === 229) return;
    e.preventDefault();
    submit();
  };

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue("");
    setMentionQuery(null);
  };

  return (
    <div className="chat-input">
      <div className="chat-input-textarea-wrap">
        <textarea
          ref={taRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKey}
          onSelect={(e) => {
            const cursor = (e.target as HTMLTextAreaElement).selectionStart ?? 0;
            updateMentionState(value, cursor);
          }}
          onCompositionStart={() => {
            composingRef.current = true;
          }}
          onCompositionEnd={() => {
            composingRef.current = false;
          }}
          placeholder={
            viewerMode
              ? "您仅有查看权限，如需对话请申请编辑权限"
              : PARADIGM_PLACEHOLDER[paradigm] || "和 Agent 对话…（输入 @ 引用工作区文件）"
          }
          disabled={effectiveDisabled}
          rows={1}
        />
        {mentionQuery != null && filteredMentions.length > 0 && (
          <div className="mention-menu" role="listbox" aria-label="引用工作区文件">
            {filteredMentions.map((f, i) => (
              <button
                type="button"
                key={f.id}
                className={`mention-item${i === mentionIdx ? " active" : ""}`}
                onMouseDown={(e) => {
                  e.preventDefault(); // 别让 textarea 失焦
                  insertMention(f);
                }}
                onMouseEnter={() => setMentionIdx(i)}
              >
                <span className="mention-icon">📎</span>
                <span className="mention-name">{f.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="chat-input-actions">
        <span className="chat-hint">
          {viewerMode
            ? "🔒 只读视角"
            : "Enter 发送 · Shift+Enter 换行 · @ 引用文件"}
        </span>
        {viewerMode ? (
          <button
            type="button"
            className="btn-primary"
            onClick={() => onRequestEditAccess?.()}
            disabled={!!editAccessRequested || !onRequestEditAccess}
            title={
              editAccessRequested
                ? "已申请，等待任务所有者审批"
                : "向任务所有者申请编辑权限"
            }
          >
            {editAccessRequested ? "🕓 已申请编辑权限" : "✋ 申请编辑权限"}
          </button>
        ) : isStreaming ? (
          <>
            {voiceEnabled && onVoiceConversation && (
              <button
                type="button"
                className="btn-voice-conv"
                onClick={onVoiceConversation}
                disabled={effectiveDisabled}
                title="语音对话：持续聆听、自动朗读 Agent 回答"
                aria-label="进入语音对话"
              >
                🎙 语音
              </button>
            )}
            <button className="btn-secondary" onClick={onAbort}>
              ⏸ 暂停生成
            </button>
          </>
        ) : (
          <>
            {voiceEnabled && onVoiceConversation && (
              <button
                type="button"
                className="btn-voice-conv"
                onClick={onVoiceConversation}
                disabled={effectiveDisabled}
                title="语音对话：持续聆听、自动朗读 Agent 回答"
                aria-label="进入语音对话"
              >
                🎙 语音
              </button>
            )}
            <button
              type="button"
              className="btn-ok"
              onClick={() => onSend("OK")}
              disabled={effectiveDisabled}
              title="一键发送 OK，常用于让 Agent 继续 / 确认"
              aria-label="一键发送 OK"
            >
              OK
            </button>
            <button
              className="btn-primary"
              onClick={submit}
              disabled={effectiveDisabled || !value.trim()}
            >
              发送 ↵
            </button>
          </>
        )}
      </div>
    </div>
  );
});
