import { KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import { useUIStore } from "@/stores/uiStore";
import "./ChatInput.css";

interface Props {
  paradigm?: string;
  disabled?: boolean;
  isStreaming?: boolean;
  onSend: (text: string) => void;
  onAbort?: () => void;
  /** Open the voice-conversation overlay. If undefined the 🎙 button is
   * not rendered (legacy / non-voice contexts). */
  onVoiceConversation?: () => void;
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

export function ChatInput({
  paradigm = "biz",
  disabled,
  isStreaming,
  onSend,
  onAbort,
  onVoiceConversation,
}: Props) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const voiceEnabled = useUIStore((s) => s.voiceEnabled);
  // IME 组字态。Mac 中文输入法下，用户拼拼音时按 Enter 是"上屏候选词"，
  // 不应触发发送。同时监听 React 合成事件 + nativeEvent.isComposing + keyCode=229，
  // 三者任一命中都视作组字中（不同浏览器/输入法的信号不一致）。
  const composingRef = useRef(false);

  // 自动撑高：内容 ≤ MAX_HEIGHT 时贴合 scrollHeight，超过启用滚动条
  useLayoutEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, el.scrollHeight));
    el.style.height = next + "px";
  }, [value]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
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
  };
  return (
    <div className="chat-input">
      <textarea
        ref={taRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        onCompositionStart={() => {
          composingRef.current = true;
        }}
        onCompositionEnd={() => {
          composingRef.current = false;
        }}
        placeholder={PARADIGM_PLACEHOLDER[paradigm] || "和 Agent 对话…"}
        disabled={disabled}
        rows={1}
      />
      <div className="chat-input-actions">
        <span className="chat-hint">Enter 发送 · Shift+Enter 换行</span>
        {voiceEnabled && onVoiceConversation && (
          <button
            type="button"
            className="btn-voice-conv"
            onClick={onVoiceConversation}
            disabled={disabled}
            title="语音对话：持续聆听、自动朗读 Agent 回答"
            aria-label="进入语音对话"
          >
            🎙 语音
          </button>
        )}
        {isStreaming ? (
          <button className="btn-secondary" onClick={onAbort}>
            ⏸ 暂停生成
          </button>
        ) : (
          <button className="btn-primary" onClick={submit} disabled={disabled || !value.trim()}>
            发送 ↵
          </button>
        )}
      </div>
    </div>
  );
}
