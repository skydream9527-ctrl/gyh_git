import { useEffect, useRef, useState } from "react";
import { useUIStore } from "@/stores/uiStore";
import {
  getActiveAudio,
  playTTS,
  setActiveAudio,
  subscribeActiveAudio,
} from "@/lib/voiceAudio";
import type { ApiError } from "@/api/client";

interface Props {
  text: string;
  className?: string;
}

const MAX_TTS_CHARS = 2000;

/**
 * Per-message 🔊 朗读 button. Hands off playback to the shared voice-audio
 * singleton so a fresh play (here or from the conversation overlay) always
 * pauses the previous one.
 */
export function VoicePlayButton({ text, className }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const pushToast = useUIStore((s) => s.pushToast);

  // Reset back to idle when the global active audio changes away from ours
  // (e.g. another button stole playback, or the overlay started speaking).
  useEffect(() => {
    return subscribeActiveAudio(() => {
      if (audioRef.current && getActiveAudio() !== audioRef.current) {
        setState("idle");
      }
    });
  }, []);

  useEffect(
    () => () => {
      if (audioRef.current && getActiveAudio() === audioRef.current) {
        setActiveAudio(null);
      }
    },
    [],
  );

  const stop = () => {
    if (audioRef.current && getActiveAudio() === audioRef.current) {
      setActiveAudio(null);
    }
    setState("idle");
  };

  const play = async () => {
    if (state === "loading") return;
    if (state === "playing") {
      stop();
      return;
    }
    const trimmed = text.trim().slice(0, MAX_TTS_CHARS);
    if (!trimmed) return;
    if (text.length > MAX_TTS_CHARS) {
      pushToast("info", `内容较长，仅朗读前 ${MAX_TTS_CHARS} 字`);
    }
    setState("loading");
    try {
      const audio = await playTTS(trimmed);
      audioRef.current = audio;
      audio.addEventListener("ended", () => setState("idle"), { once: true });
      audio.addEventListener("error", () => setState("idle"), { once: true });
      setState("playing");
    } catch (err) {
      setState("idle");
      const e = err as ApiError;
      pushToast("error", `语音合成失败：${e.message || "未知错误"}`);
    }
  };

  let label: string;
  if (state === "loading") label = "⏳";
  else if (state === "playing") label = "⏸ 停止";
  else label = "🔊 朗读";

  return (
    <button
      type="button"
      className={className || "msg-action-btn voice-play-btn"}
      onClick={play}
      disabled={state === "loading"}
      title={state === "playing" ? "点击停止" : "点击朗读"}
    >
      {label}
    </button>
  );
}
