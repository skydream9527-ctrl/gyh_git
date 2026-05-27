import { useCallback, useEffect, useRef, useState } from "react";
import { voiceApi } from "@/api/endpoints";
import { playTTS, stopActiveAudio } from "@/lib/voiceAudio";
import type { ApiError } from "@/api/client";
import type { ChatMessage } from "@/types/api";
import type { StreamPhase } from "@/hooks/useChatSocket";
import "./VoiceConversationOverlay.css";

interface Props {
  open: boolean;
  onClose: () => void;
  onSend: (text: string) => void;
  phase: StreamPhase;
  finalized: ChatMessage[];
  defaultVoice?: string;
}

type Mode = "listening" | "processing" | "speaking" | "error";

// VAD knobs. Tuned by ear on a quiet room with a laptop mic. Browser audio
// can vary wildly so all three numbers below are intentionally generous —
// rather miss a too-soft whisper than cut someone off mid-sentence.
const SILENCE_TIMEOUT_MS = 1500; // 静音多久后视为说完
const MIN_TOTAL_MS = 350; // 录音至少要这么久才考虑发送（防误触）
const MAX_RECORD_MS = 30_000; // 单轮硬上限
const VAD_THRESHOLD = 0.045; // 振幅阈值，0-1（128 中心点的偏离比例）

function pickMime(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const m of [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
    "",
  ]) {
    if (m === "" || MediaRecorder.isTypeSupported(m)) return m;
  }
  return "";
}

/**
 * ChatGPT/Gemini-style continuous voice conversation.
 *
 * State machine: listening → processing → (waiting for agent) → speaking → listening …
 *
 * The component owns:
 *   - one MediaStream + MediaRecorder per listening turn
 *   - one AudioContext + AnalyserNode for VAD endpointing
 *   - playback handed off to lib/voiceAudio so the per-message 朗读 button
 *     can't double-play with us
 *
 * It does NOT own the chat socket — `onSend` calls back into the parent,
 * and we observe `phase` / `finalized` to know when the agent has finished
 * so we can read the new message out loud.
 */
export function VoiceConversationOverlay({
  open,
  onClose,
  onSend,
  phase,
  finalized,
  defaultVoice,
}: Props) {
  const [mode, setMode] = useState<Mode>("listening");
  const [level, setLevel] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [agentText, setAgentText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Per-listening-turn refs. Re-allocated each time we (re)start listening.
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadRafRef = useRef<number | null>(null);
  const hardStopTimerRef = useRef<number | null>(null);
  // Re-entry guard: endRecording() may be called twice in a row (silence
  // timer + max-record timeout), and rec.stop() is async — without this flag
  // we'd start a second stop while the first is in-flight.
  const endingRef = useRef(false);
  const speechDetectedRef = useRef(false);
  const lastSpeechAtRef = useRef(0);
  const startedAtRef = useRef(0);

  // Tie agent responses to OUR sends only:
  //   - awaitingMarker = assistant-message count at the moment we sent
  //   - lastSpokenId tracks which message we've already played, in case the
  //     phase=done effect fires multiple times for the same message
  const awaitingMarkerRef = useRef<number | null>(null);
  const lastSpokenIdRef = useRef<string | null>(null);

  // Mirror the open prop into a ref so async callbacks (recorder.onstop, etc)
  // see the up-to-date value rather than a stale closure capture.
  const openRef = useRef(open);
  useEffect(() => {
    openRef.current = open;
  }, [open]);

  const cleanupSession = useCallback(() => {
    if (vadRafRef.current) {
      cancelAnimationFrame(vadRafRef.current);
      vadRafRef.current = null;
    }
    if (hardStopTimerRef.current) {
      window.clearTimeout(hardStopTimerRef.current);
      hardStopTimerRef.current = null;
    }
    if (analyserRef.current) {
      try {
        analyserRef.current.disconnect();
      } catch {
        /* ignore */
      }
      analyserRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        void audioCtxRef.current.close();
      } catch {
        /* ignore */
      }
      audioCtxRef.current = null;
    }
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    recorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    chunksRef.current = [];
  }, []);

  const processBlob = useCallback(
    async (blob: Blob, mime: string) => {
      try {
        const { text } = await voiceApi.asr(blob, mime);
        const t = (text || "").trim();
        if (!t) {
          // ASR heard nothing meaningful — silently restart listening so the
          // user can try again without the conversation feeling "stuck".
          if (openRef.current) void startListening();
          return;
        }
        setTranscript(t);
        // Mark the response we'll wait on. Counting JUST the assistant
        // messages avoids miscounting when intermediate user messages land.
        awaitingMarkerRef.current = finalized.filter(
          (m) => m.role === "assistant",
        ).length;
        onSend(t);
        // Stay in "processing" — the phase=done effect below will move us
        // into "speaking" once the agent reply lands in `finalized`.
      } catch (err) {
        const e = err as ApiError;
        setError(`识别失败：${e.message || "未知错误"}`);
        setMode("error");
      }
    },
    // startListening is defined below; eslint can't see the cycle but the
    // mutual recursion is intentional and bounded by the open flag.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [finalized, onSend],
  );

  const startListening = useCallback(async () => {
    if (!openRef.current) return;
    cleanupSession();
    endingRef.current = false;
    speechDetectedRef.current = false;
    lastSpeechAtRef.current = 0;
    startedAtRef.current = performance.now();
    setMode("listening");
    setLevel(0);
    setError(null);
    // We're starting fresh — make sure any leftover TTS from a prior turn
    // is silenced. (The speaking→listening handoff already does this, but
    // the user may also click the orb to interrupt.)
    stopActiveAudio();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = pickMime();
      const rec = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      recorderRef.current = rec;
      chunksRef.current = [];
      rec.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      rec.onstop = () => {
        const actualMime = rec.mimeType || mime || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: actualMime });
        // Free the mic now — if we end up restarting we'll grab a new stream.
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        if (!speechDetectedRef.current || blob.size < 800) {
          // No actual speech — just go back to listening without bothering ASR.
          if (openRef.current) void startListening();
          return;
        }
        setMode("processing");
        void processBlob(blob, actualMime);
      };
      rec.start();

      // VAD on a parallel AnalyserNode. Reading the time-domain (rather than
      // frequency) buffer keeps the threshold meaningful across mic gain
      // differences — we just want "is the waveform deviating from silence".
      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      src.connect(analyser);
      analyserRef.current = analyser;
      const buf = new Uint8Array(analyser.fftSize);

      const tick = () => {
        if (endingRef.current || !analyserRef.current || !openRef.current) return;
        analyserRef.current.getByteTimeDomainData(buf);
        let peak = 0;
        for (let i = 0; i < buf.length; i++) {
          const v = Math.abs(buf[i] - 128) / 128;
          if (v > peak) peak = v;
        }
        setLevel(peak);
        const now = performance.now();
        if (peak > VAD_THRESHOLD) {
          speechDetectedRef.current = true;
          lastSpeechAtRef.current = now;
        }
        const elapsedTotal = now - startedAtRef.current;
        const silentFor = now - lastSpeechAtRef.current;
        const endpointed =
          speechDetectedRef.current &&
          silentFor > SILENCE_TIMEOUT_MS &&
          elapsedTotal > MIN_TOTAL_MS;
        if (endpointed || elapsedTotal > MAX_RECORD_MS) {
          endRecording();
          return;
        }
        vadRafRef.current = requestAnimationFrame(tick);
      };
      vadRafRef.current = requestAnimationFrame(tick);
      // Belt-and-suspenders against a hung VAD loop or a tab that was
      // backgrounded mid-utterance: force-stop a touch after MAX_RECORD_MS.
      hardStopTimerRef.current = window.setTimeout(() => {
        endRecording();
      }, MAX_RECORD_MS + 1000);
    } catch (err) {
      const e = err as Error;
      const msg =
        e.name === "NotAllowedError"
          ? "麦克风权限被拒绝，无法开始语音对话"
          : `无法访问麦克风：${e.message}`;
      setError(msg);
      setMode("error");
    }
  }, [cleanupSession, processBlob]);

  const endRecording = useCallback(() => {
    if (endingRef.current) return;
    endingRef.current = true;
    if (vadRafRef.current) {
      cancelAnimationFrame(vadRafRef.current);
      vadRafRef.current = null;
    }
    if (hardStopTimerRef.current) {
      window.clearTimeout(hardStopTimerRef.current);
      hardStopTimerRef.current = null;
    }
    setLevel(0);
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      try {
        rec.stop();
      } catch {
        /* ignore — onstop will still fire if the stop succeeded */
      }
    }
  }, []);

  // phase=done watcher: when the agent finishes a turn that we initiated,
  // grab the latest assistant message and read it out loud, then chain back
  // into listening so the user can reply.
  useEffect(() => {
    if (!open) return;
    if (phase !== "done") return;
    if (awaitingMarkerRef.current === null) return;
    const assistantMsgs = finalized.filter((m) => m.role === "assistant");
    if (assistantMsgs.length <= awaitingMarkerRef.current) return;
    const latest = assistantMsgs[assistantMsgs.length - 1];
    if (!latest.content || !latest.content.trim()) {
      // Empty message body (e.g. tool-only turn) — skip TTS, resume listening.
      awaitingMarkerRef.current = null;
      lastSpokenIdRef.current = latest.id;
      void startListening();
      return;
    }
    if (latest.id === lastSpokenIdRef.current) return;
    awaitingMarkerRef.current = null;
    lastSpokenIdRef.current = latest.id;
    setAgentText(latest.content);
    setMode("speaking");
    playTTS(latest.content.slice(0, 2000), defaultVoice)
      .then((audio) => {
        const onEnd = () => {
          if (openRef.current) void startListening();
        };
        audio.addEventListener("ended", onEnd, { once: true });
        audio.addEventListener("error", onEnd, { once: true });
      })
      .catch((err) => {
        const e = err as ApiError;
        setError(`朗读失败：${e.message || "未知错误"}`);
        // Still loop back so the conversation isn't dead-ended.
        if (openRef.current) void startListening();
      });
  }, [phase, finalized, open, defaultVoice, startListening]);

  // Open / close lifecycle.
  useEffect(() => {
    if (open) {
      setTranscript("");
      setAgentText("");
      setError(null);
      awaitingMarkerRef.current = null;
      lastSpokenIdRef.current = null;
      void startListening();
    }
    return () => {
      cleanupSession();
      stopActiveAudio();
    };
  }, [open, startListening, cleanupSession]);

  const handleInterrupt = () => {
    if (mode === "speaking") {
      stopActiveAudio();
      void startListening();
    } else if (mode === "error") {
      void startListening();
    }
  };

  if (!open) return null;

  let label: string;
  switch (mode) {
    case "listening":
      label = speechDetectedRef.current ? "正在听你说…" : "请讲，我在听…";
      break;
    case "processing":
      label = "识别中…";
      break;
    case "speaking":
      label = "Agent 正在回答（点圆圈打断）";
      break;
    case "error":
      label = error || "出错了";
      break;
  }

  const orbIcon =
    mode === "listening"
      ? "🎙"
      : mode === "processing"
        ? "⋯"
        : mode === "speaking"
          ? "🔊"
          : "⚠";

  return (
    <div className="vc-overlay" role="dialog" aria-label="语音对话">
      <button
        className="vc-close"
        onClick={onClose}
        aria-label="关闭语音对话"
        title="关闭"
      >
        ×
      </button>
      <div className="vc-stage">
        <div
          className={`vc-orb vc-orb--${mode}`}
          style={{ "--lvl": level } as React.CSSProperties}
          onClick={handleInterrupt}
          role="button"
          tabIndex={0}
          aria-label={
            mode === "speaking" ? "点击打断 Agent 回答并重新聆听" : "状态指示"
          }
          onKeyDown={(e) => {
            if (e.key === " " || e.key === "Enter") {
              e.preventDefault();
              handleInterrupt();
            }
          }}
        >
          <span className="vc-orb-icon">{orbIcon}</span>
        </div>
        <div className="vc-label">{label}</div>
        {transcript && (
          <div className="vc-line vc-line--user">你：{transcript}</div>
        )}
        {agentText && mode !== "listening" && (
          <div className="vc-line vc-line--agent">
            Agent：
            {agentText.length > 220
              ? agentText.slice(0, 220) + "…"
              : agentText}
          </div>
        )}
      </div>
      <div className="vc-actions">
        {mode === "speaking" && (
          <button
            className="vc-btn vc-btn--ghost"
            onClick={handleInterrupt}
          >
            ⏸ 打断 / 我来说
          </button>
        )}
        {mode === "error" && (
          <button className="vc-btn" onClick={() => void startListening()}>
            重试
          </button>
        )}
        <button className="vc-btn vc-btn--ghost" onClick={onClose}>
          结束语音对话
        </button>
      </div>
    </div>
  );
}
