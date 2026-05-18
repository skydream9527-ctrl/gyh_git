import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { clearTokens, getAccessToken, setTokens } from "@/api/client";
import type { ApiEnvelope, ChatMessage, ToolCall } from "@/types/api";

const REFRESH_KEY = "ice-refresh-token";

/** Best-effort: refresh the access token if one is obviously stale; returns the
 * newest token we have (may be null if user has no tokens at all). The WS
 * handshake then uses it. Network/refresh errors fall back to whatever is in
 * localStorage so we don't block connection on transient failures. */
async function ensureFreshToken(): Promise<string | null> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return getAccessToken(); // Aegis cookie mode or logged out
  try {
    const r = await axios.post<ApiEnvelope<{ access_token: string; refresh_token: string }>>(
      "/api/v1/auth/refresh",
      { refresh_token: refresh },
    );
    if (r.data.code === 0) {
      setTokens(r.data.data.access_token, r.data.data.refresh_token);
      return r.data.data.access_token;
    }
  } catch (_) {
    // ignore; caller will try whatever is in localStorage
  }
  return getAccessToken();
}

export type StreamPhase = "idle" | "typing" | "streaming" | "tool" | "done" | "error";

export interface PartialAssistant {
  id: string;
  content: string;
  toolCalls: ToolCall[];
}

export interface TodoItem {
  id: string;
  content: string;
  activeForm: string;
  status: "pending" | "in_progress" | "completed";
}

export interface PlanProposal {
  plan_id: string;
  plan_text: string;
}

interface UseChatSocketOpts {
  taskId: string;
  conversationId: string | null;
  onError?: (errorCode: string, message: string) => void;
  onFileCreated?: (file: { id: string; name: string }) => void;
  onTodosUpdated?: (items: TodoItem[], updatedAt: string) => void;
}

interface SocketState {
  status: "idle" | "connecting" | "open" | "closed";
  phase: StreamPhase;
  partial: PartialAssistant | null;
  finalized: ChatMessage[];
  todos: TodoItem[];
  todosUpdatedAt: string | null;
  planMode: boolean;
  pendingPlan: PlanProposal | null;
  send: (content: string, opts?: { model?: string }) => void;
  abort: () => void;
  setPlanMode: (enabled: boolean) => void;
  approvePlan: (planId: string) => void;
  rejectPlan: (planId: string) => void;
  clearError: () => void;
  errorCode: string | null;
}

export function useChatSocket({ taskId, conversationId, onError, onFileCreated, onTodosUpdated }: UseChatSocketOpts): SocketState {
  const [status, setStatus] = useState<SocketState["status"]>("idle");
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [partial, setPartial] = useState<PartialAssistant | null>(null);
  const [finalized, setFinalized] = useState<ChatMessage[]>([]);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [todosUpdatedAt, setTodosUpdatedAt] = useState<string | null>(null);
  const [planMode, setPlanModeState] = useState<boolean>(false);
  const [pendingPlan, setPendingPlan] = useState<PlanProposal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const retryTimerRef = useRef<number | null>(null);
  // 刚打开 Workspace 到 WS 握手成功之间大约 50–300ms，用户点发送就落这段空窗。
  // 不 show WS_DISCONNECTED 横幅，把消息排队，onopen 时一次性 flush。
  const pendingQueueRef = useRef<string[]>([]);

  // 镜像 partial 到 ref，让事件处理器读到的是最新值。
  // 不能在 setPartial 的 updater 里嵌套调 setFinalized——React 18 StrictMode 在
  // dev 模式会双调 updater 验证纯函数性,导致 finalize 一条消息追加两遍。
  const partialRef = useRef<PartialAssistant | null>(null);
  useEffect(() => {
    partialRef.current = partial;
  }, [partial]);
  // ws.onclose 是 connect() 闭包内创建的，里面读 phase 拿到的是首次创建时
  // 那一帧的值。要在断连时判断「此刻」是否在流式态，必须走 ref。
  const phaseRef = useRef<StreamPhase>("idle");
  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  const connect = useCallback(() => {
    if (!conversationId) return;
    setStatus("connecting");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/api/v1/ws/conversations/${conversationId}?task_id=${encodeURIComponent(taskId)}`;
    // 认证三选一（ws.py 按序尝试）：
    //  ① 米盾代理：代理注入 X-Proxy-UserDetail，浏览器什么都不用带
    //  ② Bearer subprotocol：`["bearer", "<jwt>"]`（浏览器 WebSocket 唯一能塞 header 的通道）
    //  ③ `?token=<jwt>` 查询参数（兜底）
    // 账号密码登录后 localStorage 里就有 access token，走 ② 即可。
    //
    // 为什么要先 ensureFreshToken：页面留到 token 过期后，WS 握手会被后端 4401 拒掉，
    // 纯靠 onclose 重连会卡在死循环。先用 refresh_token 换一张新 access token 再连。
    (async () => {
      const token = await ensureFreshToken();
      const ws = token
        ? new WebSocket(url, ["bearer", token])
        : new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("open");
        retryRef.current = 0;
        // 连上立刻清掉之前的 WS_DISCONNECTED 提示，别让 banner 赖着不走
        setErrorCode((cur) => (cur === "WS_DISCONNECTED" ? null : cur));
        // flush 等待队列：连上的瞬间把空窗期用户发的消息补送上去
        const queued = pendingQueueRef.current;
        pendingQueueRef.current = [];
        for (const payload of queued) {
          try {
            ws.send(payload);
          } catch {
            // drop — if send fails here the close handler will re-fire and retry
          }
        }
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          handleEvent(data);
        } catch {
          /* ignore */
        }
      };
      ws.onclose = (ev) => {
        setStatus("closed");
        // 流到一半 WS 断了：phase 还卡在 streaming/tool/typing，UI 会一直显示
        // 「暂停生成」按钮把发送框锁住。把已经流出来的 partial 落地保留，phase
        // 切成 error 让按钮恢复成「发送」。后端 task 仍在跑（见 ws.py 的 detach
        // 逻辑），完整结果会在用户重新加载或刷新时从 JSONL 拉到。
        const stuckPhase = ["streaming", "tool", "typing"].includes(phaseRef.current);
        if (stuckPhase) {
          const cur = partialRef.current;
          if (cur && (cur.content || cur.toolCalls.length > 0)) {
            setFinalized((arr) => {
              if (arr.some((m) => m.id === cur.id)) return arr;
              return [
                ...arr,
                {
                  id: cur.id,
                  role: "assistant",
                  content: cur.content,
                  tool_uses: cur.toolCalls.map((t) => ({
                    id: t.tool_call_id,
                    name: t.tool_name,
                    input: t.arguments,
                  })),
                  created_at: new Date().toISOString(),
                },
              ];
            });
          }
          setPartial(null);
          setPhase("error");
          setErrorCode("STREAM_INTERRUPTED");
        }
        // 后端用 4401（身份失效）/ 4403（无权限）做语义化关闭。
        // 4401 可能是 token 过期但 refresh_token 还活着 → 重试前 ensureFreshToken 会自动换新
        // 4403 是这个用户就是没权访问这个 task，再重连多少次都没用，直接让用户看见错误
        if (ev.code === 4403) {
          setErrorCode("PERMISSION_DENIED");
          setPhase("error");
          return;
        }
        if (ev.code === 4401) {
          // 没有 refresh_token 就是已登出，踢回登录页
          if (!localStorage.getItem(REFRESH_KEY)) {
            clearTokens();
            if (location.pathname !== "/login") location.href = "/login";
            return;
          }
        }
        // exponential backoff: 1,2,4,8,16,30 max
        const delays = [1000, 2000, 4000, 8000, 16000, 30000];
        const delay = delays[Math.min(retryRef.current, delays.length - 1)];
        retryRef.current += 1;
        retryTimerRef.current = window.setTimeout(connect, delay);
      };
      ws.onerror = () => {
        // close handler will trigger reconnect
      };
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, taskId]);

  const handleEvent = (ev: any) => {
    switch (ev.type) {
      case "user_message_ack":
        // user message already pushed locally on send; nothing to do
        break;
      case "agent_typing":
        setPhase(ev.status === "start" ? "typing" : "idle");
        break;
      case "agent_message":
        setPhase("streaming");
        setPartial((cur) => {
          if (!cur) {
            return {
              id: ev.message_id,
              content: ev.content,
              toolCalls: [],
            };
          }
          if (cur.id !== ev.message_id) {
            // new round; flush previous
            return {
              id: ev.message_id,
              content: ev.content,
              toolCalls: cur.toolCalls,
            };
          }
          return { ...cur, content: cur.content + ev.content };
        });
        break;
      case "tool_call_start":
        setPhase("tool");
        setPartial((cur) => {
          const base = cur ?? { id: "tmp", content: "", toolCalls: [] };
          return {
            ...base,
            toolCalls: [
              ...base.toolCalls,
              {
                tool_call_id: ev.tool_call_id,
                tool_name: ev.tool_name,
                display_name: ev.display_name,
                arguments: ev.arguments || {},
                status: "executing",
              },
            ],
          };
        });
        break;
      case "tool_call_done":
        setPartial((cur) => {
          if (!cur) return cur;
          return {
            ...cur,
            toolCalls: cur.toolCalls.map((tc) =>
              tc.tool_call_id === ev.tool_call_id
                ? {
                    ...tc,
                    status: ev.status,
                    result: ev.result,
                    error: ev.error,
                  }
                : tc,
            ),
          };
        });
        break;
      case "agent_message_done": {
        const cur = partialRef.current;
        if (cur) {
          setFinalized((arr) => {
            // 防御性去重：万一同一 message_id 已落库，不再追加。
            if (arr.some((m) => m.id === cur.id)) return arr;
            return [
              ...arr,
              {
                id: cur.id,
                role: "assistant",
                content: cur.content,
                tool_uses: cur.toolCalls.map((t) => ({
                  id: t.tool_call_id,
                  name: t.tool_name,
                  input: t.arguments,
                })),
                created_at: new Date().toISOString(),
              },
            ];
          });
        }
        setPartial(null);
        setPhase("done");
        break;
      }
      case "file_created":
        if (ev.file?.id && ev.file?.name) {
          onFileCreated?.({ id: ev.file.id, name: ev.file.name });
        }
        break;
      case "todos_updated":
        if (Array.isArray(ev.items)) {
          setTodos(ev.items as TodoItem[]);
          setTodosUpdatedAt(ev.updated_at || new Date().toISOString());
          onTodosUpdated?.(ev.items as TodoItem[], ev.updated_at || "");
        }
        break;
      case "plan_mode_changed":
        setPlanModeState(Boolean(ev.enabled));
        if (!ev.enabled) setPendingPlan(null);
        break;
      case "plan_proposed":
        if (ev.plan_id && typeof ev.plan_text === "string") {
          setPendingPlan({ plan_id: ev.plan_id, plan_text: ev.plan_text });
        }
        break;
      case "plan_resolved":
        setPendingPlan(null);
        break;
      case "error":
        setErrorCode(ev.error_code || "ERROR");
        setPhase("error");
        onError?.(ev.error_code || "ERROR", ev.message || "");
        break;
    }
  };

  // 切换到另一条对话时，必须先把上一次对话的增量状态清空，否则
   // WorkspacePage 里 `[...history, ...socket.finalized]` 会把旧对话的消息
   // 拼到新对话前面——表现就是"新建空白对话，点进去还能看到历史"。
  // 这里只重置本 hook 维护的增量流（partial/finalized/todos/plan 等），
  // history 由 WorkspacePage 自己根据 conversationApi.get 的结果负责。
  useEffect(() => {
    setFinalized([]);
    setPartial(null);
    setPhase("idle");
    setErrorCode(null);
    setTodos([]);
    setTodosUpdatedAt(null);
    setPlanModeState(false);
    setPendingPlan(null);
    pendingQueueRef.current = [];
    partialRef.current = null;
  }, [conversationId]);

  useEffect(() => {
    connect();
    return () => {
      if (retryTimerRef.current) window.clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = (content: string, opts?: { model?: string }) => {
    setErrorCode(null);
    setFinalized((arr) => [
      ...arr,
      {
        id: `local-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      },
    ]);
    setPhase("typing");
    const payload: Record<string, unknown> = { type: "user_message", content };
    if (opts?.model) payload.model = opts.model;
    const payloadStr = JSON.stringify(payload);
    const rs = wsRef.current?.readyState;
    if (rs === WebSocket.OPEN) {
      wsRef.current!.send(payloadStr);
      return;
    }
    if (rs === WebSocket.CONNECTING) {
      // 握手空窗期：排队，onopen 会 flush。Banner 不弹。
      pendingQueueRef.current.push(payloadStr);
      return;
    }
    // CLOSED / CLOSING：WS 没在路上；先塞队列，再触发一次 connect() 确保重连
    pendingQueueRef.current.push(payloadStr);
    setErrorCode("WS_DISCONNECTED");
    setPhase("error");
  };

  const abort = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "abort" }));
    }
    // 乐观回滚 phase：后端要等 LLM stream 下一拍才看 cancel_event，几秒里
    // UI 仍显示「⏸ 暂停生成」会让用户以为按钮坏了。立刻把已流出的 partial
    // 落到 finalized，phase 切成 done。后端真送来 agent_message_done 时
    // 那段 if-already-in-finalized 会防御去重。
    const cur = partialRef.current;
    if (cur && (cur.content || cur.toolCalls.length > 0)) {
      setFinalized((arr) => {
        if (arr.some((m) => m.id === cur.id)) return arr;
        return [
          ...arr,
          {
            id: cur.id,
            role: "assistant",
            content: cur.content,
            tool_uses: cur.toolCalls.map((t) => ({
              id: t.tool_call_id,
              name: t.tool_name,
              input: t.arguments,
            })),
            created_at: new Date().toISOString(),
          },
        ];
      });
    }
    setPartial(null);
    setPhase("done");
  };

  const sendControl = (payload: Record<string, unknown>) => {
    const rs = wsRef.current?.readyState;
    const body = JSON.stringify(payload);
    if (rs === WebSocket.OPEN) {
      wsRef.current!.send(body);
    } else if (rs === WebSocket.CONNECTING) {
      pendingQueueRef.current.push(body);
    } else {
      pendingQueueRef.current.push(body);
    }
  };

  const setPlanMode = (enabled: boolean) => {
    // Optimistic UI update; authoritative value comes back via plan_mode_changed.
    setPlanModeState(enabled);
    if (!enabled) setPendingPlan(null);
    sendControl({ type: "set_plan_mode", enabled });
  };

  const approvePlan = (planId: string) => {
    setPendingPlan(null);
    sendControl({ type: "approve_plan", plan_id: planId });
  };

  const rejectPlan = (planId: string) => {
    setPendingPlan(null);
    sendControl({ type: "reject_plan", plan_id: planId });
  };

  return {
    status,
    phase,
    partial,
    finalized,
    todos,
    todosUpdatedAt,
    planMode,
    pendingPlan,
    send,
    abort,
    setPlanMode,
    approvePlan,
    rejectPlan,
    errorCode,
    clearError: () => setErrorCode(null),
  };
}
