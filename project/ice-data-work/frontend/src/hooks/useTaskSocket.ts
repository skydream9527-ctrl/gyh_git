import { useCallback, useEffect, useRef, useState } from "react";

export interface Speaker {
  type: "user" | "twin" | "agent";
  id: string;
}

export interface ChatTurn {
  id: string;
  speaker: Speaker;
  content: string;
  streaming?: boolean;
  tool_calls?: { tool: string; args: unknown; result?: unknown }[];
}

interface WsEvent {
  type: "turn_start" | "text" | "tool_use" | "turn_done" | "error" | "pong";
  speaker?: Speaker;
  delta?: string;
  content?: string;
  message?: string;
  tool?: string;
  args?: unknown;
  result?: unknown;
}

// 管理与某任务的 WebSocket 流式对话连接。
export function useTaskSocket(taskId: string, initialTurns: ChatTurn[] = []) {
  const [turns, setTurns] = useState<ChatTurn[]>(initialTurns);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingIdRef = useRef<string | null>(null);

  useEffect(() => {
    setTurns(initialTurns);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    const token = localStorage.getItem("idw_token") || "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/api/v1/ws/tasks/${taskId}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      const evt: WsEvent = JSON.parse(e.data);
      if (evt.type === "turn_start" && evt.speaker) {
        const id = `streaming_${Date.now()}`;
        streamingIdRef.current = id;
        setThinking(true);
        setTurns((prev) => [...prev, { id, speaker: evt.speaker!, content: "", streaming: true }]);
      } else if (evt.type === "text" && evt.delta) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === streamingIdRef.current ? { ...t, content: t.content + evt.delta } : t
          )
        );
      } else if (evt.type === "tool_use") {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === streamingIdRef.current
              ? { ...t, tool_calls: [...(t.tool_calls || []), { tool: evt.tool!, args: evt.args, result: evt.result }] }
              : t
          )
        );
      } else if (evt.type === "turn_done") {
        setTurns((prev) =>
          prev.map((t) => (t.id === streamingIdRef.current ? { ...t, streaming: false } : t))
        );
        streamingIdRef.current = null;
        setThinking(false);
      } else if (evt.type === "error") {
        setTurns((prev) => [
          ...prev,
          { id: `err_${Date.now()}`, speaker: { type: "agent", id: "system" }, content: `⚠️ ${evt.message}` },
        ]);
        setThinking(false);
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  const send = useCallback((content: string, mentioned?: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    // 先本地追加用户消息
    setTurns((prev) => [
      ...prev,
      { id: `user_${Date.now()}`, speaker: { type: "user", id: "me" }, content },
    ]);
    ws.send(JSON.stringify({ type: "message", content, mentioned }));
  }, []);

  return { turns, connected, thinking, send };
}
