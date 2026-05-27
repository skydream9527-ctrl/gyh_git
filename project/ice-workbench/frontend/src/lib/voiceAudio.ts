/**
 * Shared TTS playback singleton.
 *
 * Both the per-message 🔊 朗读 button and the 语音对话 overlay play TTS
 * through this module so they cooperatively own the same `<audio>` element —
 * starting a new playback (or recording, in the overlay) automatically
 * pauses whatever is already playing.
 */
import { voiceApi } from "@/api/endpoints";

type Listener = () => void;

let activeAudio: HTMLAudioElement | null = null;
let activeBlobUrl: string | null = null;
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function getActiveAudio(): HTMLAudioElement | null {
  return activeAudio;
}

export function subscribeActiveAudio(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Set the currently-playing audio. Pauses the previous one if different. */
export function setActiveAudio(a: HTMLAudioElement | null): void {
  if (activeAudio && activeAudio !== a) {
    try {
      activeAudio.pause();
    } catch {
      /* ignore */
    }
  }
  activeAudio = a;
  notify();
}

/** Stop whatever is playing right now. Safe to call when nothing plays. */
export function stopActiveAudio(): void {
  setActiveAudio(null);
}

function revokeActiveBlobUrl() {
  if (activeBlobUrl) {
    URL.revokeObjectURL(activeBlobUrl);
    activeBlobUrl = null;
  }
}

/**
 * Fetch + play TTS for `text`. Stops any current audio first. Resolves with
 * the new <audio> element so callers can attach `ended` / `error` listeners
 * (used by the conversation overlay to chain back into listening mode).
 */
export async function playTTS(text: string, voice?: string): Promise<HTMLAudioElement> {
  const blob = await voiceApi.tts(text, voice);
  revokeActiveBlobUrl();
  const url = URL.createObjectURL(blob);
  activeBlobUrl = url;
  const audio = new Audio(url);
  setActiveAudio(audio);
  const cleanup = () => {
    if (activeAudio === audio) setActiveAudio(null);
  };
  audio.addEventListener("ended", cleanup);
  audio.addEventListener("error", cleanup);
  await audio.play();
  return audio;
}
