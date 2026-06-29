import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import http, { clearTokens, getAccessToken, setTokens } from "@/api/client";
import { useUIStore } from "@/stores/uiStore";
import type { ApiEnvelope, ChatMessage, HitlRequest, ToolCall } from "@/types/api";
import {
  PENDING_QUEUE_MAX,
  RECONNECT_WARNING_THRESHOLD,
  backoffDelay,
  buildWsArgs,
  classifyClose,
  pushPending,
  reconnectWarningVisible,
} from "./wsConnection";

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

/** Explicitly exchange the refresh token for a fresh access token.
 *
 * Unlike `ensureFreshToken`, this never falls back to the stale localStorage
 * token: it returns `true` only when a new access token was actually obtained
 * and stored, and `false` on any failure (missing refresh token, non-zero
 * envelope code, or network error). The 4401 close handler uses the boolean to
 * decide between reconnecting with the refreshed token (Req 5.6, 5.8) and
 * treating the disconnect as fatal (Req 5.9). */
async function refreshAccessToken(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const r = await axios.post<ApiEnvelope<{ access_token: string; refresh_token: string }>>(
      "/api/v1/auth/refresh",
      { refresh_token: refresh },
    );
    if (r.data.code === 0) {
      setTokens(r.data.data.access_token, r.data.data.refresh_token);
      return true;
    }
    return false;
  } catch (_) {
    return false;
  }
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

export interface RunEvent {
  run_id: string;
  stage: string;
  label: string;
  status: "running" | "done" | "error" | "warning" | "waiting" | "aborted";
  detail?: string | null;
  created_at: string;
}

/** 后端 `inflight_status` 事件：当前对话是否正在被某用户的 turn 占用。
 *  WS 连上瞬间会推一次初始状态；之后每次 turn 起止 / 每 10s 心跳都会推。 */
export interface InflightUser {
  id: string;
  name: string;
  started_at: string | null;
}

interface UseChatSocketOpts {
  taskId: string;
  conversationId: string | null;
  onError?: (errorCode: string, message: string) => void;
  onFileCreated?: (file: { id: string; name: string }) => void;
  onTodosUpdated?: (items: TodoItem[], updatedAt: string) => void;
  onHitlRequested?: (request: HitlRequest) => void;
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
  runEvents: RunEvent[];
  toolOverrides: Record<string, Partial<ToolCall>>;
  send: (content: string, opts?: { model?: string }) => void;
  retryToolCall: (call: ToolCall) => void;
  abort: () => void;
  setPlanMode: (enabled: boolean) => void;
  approvePlan: (planId: string) => void;
  rejectPlan: (planId: string) => void;
  clearError: () => void;
  errorCode: string | null;
  /** 上次 onclose 的诊断信息：close code (1000/1006/1011 …) + reason
   *  string。STREAM_INTERRUPTED 时 banner 拼上去，方便区分通道断（1006/1001）
   *  vs 服务端报错（1011）vs 正常关（1000）。 */
  closeInfo: { code: number; reason: string } | null;
  /** 该对话当前被谁的 turn 占用（同一用户在另一标签页/设备发起也算）。
   *  null = 空闲，可发新消息；非 null = 显示锁定 banner、置灰 ChatInput。 */
  inflightUser: InflightUser | null;
}

export function useChatSocket({ taskId, conversationId, onError, onFileCreated, onTodosUpdated, onHitlRequested }: UseChatSocketOpts): SocketState {
  const pushToast = useUIStore((s) => s.pushToast);
  const [status, setStatus] = useState<SocketState["status"]>("idle");
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [partial, setPartial] = useState<PartialAssistant | null>(null);
  const [finalized, setFinalized] = useState<ChatMessage[]>([]);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [closeInfo, setCloseInfo] = useState<{ code: number; reason: string } | null>(null);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [todosUpdatedAt, setTodosUpdatedAt] = useState<string | null>(null);
  const [planMode, setPlanModeState] = useState<boolean>(false);
  const [pendingPlan, setPendingPlan] = useState<PlanProposal | null>(null);
  const [runEvents, setRunEvents] = useState<RunEvent[]>([]);
  const [toolOverrides, setToolOverrides] = useState<Record<string, Partial<ToolCall>>>({});
  const [inflightUser, setInflightUser] = useState<InflightUser | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onErrorRef = useRef(onError);
  const connectSeqRef = useRef(0);
  const retryRef = useRef<number>(0);
  const retryTimerRef = useRef<number | null>(null);
  const hadDisconnectRef = useRef(false);
  const warnedReconnectRef = useRef(false);
  // 刚打开 Workspace 到 WS 握手成功之间大约 50–300ms，用户点发送就落这段空窗。
  // 不 show WS_DISCONNECTED 横幅，把消息排队，onopen 时一次性 flush。
  const pendingQueueRef = useRef<string[]>([]);
  const streamBufferRef = useRef<{ messageId: string; content: string } | null>(null);
  const streamFlushRafRef = useRef<number | null>(null);

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
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const commitPartial = useCallback((updater: (cur: PartialAssistant | null) => PartialAssistant | null) => {
    const next = updater(partialRef.current);
    partialRef.current = next;
    setPartial(next);
  }, []);

  const clearStreamFlush = useCallback(() => {
    if (streamFlushRafRef.current !== null) {
      window.cancelAnimationFrame(streamFlushRafRef.current);
      streamFlushRafRef.current = null;
    }
  }, []);

  const flushStreamBuffer = useCallback(() => {
    clearStreamFlush();
    const buffered = streamBufferRef.current;
    if (!buffered || !buffered.content) return;
    streamBufferRef.current = null;
    commitPartial((cur) => {
      if (!cur || cur.id !== buffered.messageId) {
        return {
          id: buffered.messageId,
          content: buffered.content,
          toolCalls: cur?.toolCalls ?? [],
        };
      }
      return { ...cur, content: cur.content + buffered.content };
    });
  }, [clearStreamFlush, commitPartial]);

  const enqueueStreamChunk = useCallback((messageId: string, content: string) => {
    if (!messageId || !content) return;
    const buffered = streamBufferRef.current;
    if (buffered && buffered.messageId !== messageId) {
      flushStreamBuffer();
    }
    const next = streamBufferRef.current;
    streamBufferRef.current = next
      ? { messageId, content: next.content + content }
      : { messageId, content };
    if (streamFlushRafRef.current === null) {
      streamFlushRafRef.current = window.requestAnimationFrame(flushStreamBuffer);
    }
  }, [flushStreamBuffer]);

  const enqueuePending = useCallback((payload: string) => {
    pendingQueueRef.current = pushPending(pendingQueueRef.current, payload, PENDING_QUEUE_MAX);
  }, []);

  const connect = useCallback(() => {
    if (!conversationId) return;
    const seq = ++connectSeqRef.current;
    if (retryTimerRef.current) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
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
      if (seq !== connectSeqRef.current) return;
      const { url: wsUrl, subprotocols } = buildWsArgs(url, token);
      const ws = subprotocols
        ? new WebSocket(wsUrl, subprotocols)
        : new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        // 切换对话/重连导致 wsRef.current 已指向新 ws，旧 ws 的 onopen 回调不要污染状态
        if (wsRef.current !== ws) {
          try { ws.close(); } catch {/* ignore */}
          return;
        }
        setStatus("open");
        if (hadDisconnectRef.current) {
          // Req 5.4 + 5.7: 重连成功提示「连接已恢复」，并在 5s 后自动消失。
          pushToast("success", "连接已恢复", 5000);
        }
        hadDisconnectRef.current = false;
        warnedReconnectRef.current = false;
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
        // 切换对话后旧 ws 收到滞后的消息，不应再注入新对话的 UI
        if (wsRef.current !== ws) return;
        try {
          const data = JSON.parse(ev.data);
          handleEvent(data);
        } catch {
          /* ignore */
        }
      };
      ws.onclose = (ev) => {
        // 切换对话/重连导致 wsRef.current 已指向新 ws：旧 ws 的 close 是
        // useEffect cleanup 主动关的，此时不应触发 STREAM_INTERRUPTED 也不应再排重连。
        if (wsRef.current !== ws) return;
        setStatus("closed");
        // 记录 close code/reason：1006 = 异常断（反代/网络/server crash）、
        // 1011 = 服务端报错、1000 = 正常、4401/4403 = 认证。让 banner 把
        // code 显示出来，下次再断时一眼就知道排查哪块。
        setCloseInfo({ code: ev.code, reason: ev.reason || "" });
        hadDisconnectRef.current = ev.code !== 1000;
        // 流到一半 WS 断了：phase 还卡在 streaming/tool/typing，UI 会一直显示
        // 「暂停生成」按钮把发送框锁住。把已经流出来的 partial 落地保留，phase
        // 切成 error 让按钮恢复成「发送」。后端 task 仍在跑（见 ws.py 的 detach
        // 逻辑），完整结果会在用户重新加载或刷新时从 JSONL 拉到。
        const stuckPhase = ["streaming", "tool", "typing"].includes(phaseRef.current);
        if (stuckPhase) {
          flushStreamBuffer();
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
          commitPartial(() => null);
          setPhase("error");
          setErrorCode("STREAM_INTERRUPTED");
        }
        // 后端用 4401（身份失效）/ 4403（无权限）做语义化关闭。
        // 4401 可能是 token 过期但 refresh_token 还活着 → 显式换新 access token 再重连
        // 4403 是这个用户就是没权访问这个 task，再重连多少次都没用，直接让用户看见错误
        //
        // classifyClose 把 close code 映射成 recoverable/fatal + action，作为
        // 单一事实来源（与 wsConnection 的属性测试一致）。
        const hasRefresh = !!localStorage.getItem(REFRESH_KEY);
        const classification = classifyClose(ev.code, hasRefresh);

        // 按 backoff 排下一次重连，并在累计失败到阈值时弹一次持久重连告警。
        // refresh-then-reconnect 成功路径和普通 recoverable 路径共用这段逻辑。
        const scheduleReconnect = () => {
          const delay = backoffDelay(retryRef.current);
          retryRef.current += 1;
          if (
            reconnectWarningVisible(retryRef.current, RECONNECT_WARNING_THRESHOLD) &&
            !warnedReconnectRef.current
          ) {
            warnedReconnectRef.current = true;
            onErrorRef.current?.(
              "WS_RECONNECTING",
              `连接仍在重试（close=${ev.code || "unknown"}），你可以继续停留在当前页等待恢复`,
            );
          }
          retryTimerRef.current = window.setTimeout(connect, delay);
        };

        if (classification.action.type === "permission_denied") {
          setErrorCode("PERMISSION_DENIED");
          setPhase("error");
          return;
        }
        if (classification.action.type === "clear_and_redirect") {
          // 没有 refresh_token 就是已登出，清掉本地 token 并踢回登录页（2s 内，
          // 这里是同步跳转）。(Req 6.2)
          clearTokens();
          if (location.pathname !== "/login") location.href = "/login";
          return;
        }
        if (classification.action.type === "refresh_and_reconnect") {
          // 4401 且 refresh_token 还在：在排下一次重连「之前」显式换一张新的
          // access token，成功后再用新 token 重连（Req 5.6, 5.8）。刷新失败则
          // 升级为 Fatal_Disconnect——弹出鉴权错误并停止后续重连（Req 5.9）。
          if (!stuckPhase) {
            setErrorCode("WS_DISCONNECTED");
          }
          (async () => {
            const ok = await refreshAccessToken();
            // 刷新期间组件卸载 / 切了对话：connectSeq 已自增，丢弃这次续作，
            // 不要再排重连。
            if (seq !== connectSeqRef.current) return;
            if (!ok) {
              setErrorCode("AUTH_FAILED");
              setPhase("error");
              onErrorRef.current?.("AUTH_FAILED", "登录状态已失效，请重新登录后重试");
              return;
            }
            scheduleReconnect();
          })();
          return;
        }
        // recoverable（reconnect）：按 backoff 排重连。
        if (!stuckPhase && ev.code !== 1000) {
          setErrorCode("WS_DISCONNECTED");
        }
        scheduleReconnect();
      };
      ws.onerror = () => {
        // close handler will trigger reconnect
      };
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, taskId, commitPartial, flushStreamBuffer, pushToast]);

  const handleEvent = (ev: any) => {
    switch (ev.type) {
      case "user_message_ack":
        // user message already pushed locally on send; nothing to do
        break;
      case "run_event":
        if (ev.run_id && ev.label && ev.status) {
          setRunEvents((arr) => [
            ...arr,
            {
              run_id: ev.run_id,
              stage: ev.stage || "run",
              label: ev.label,
              status: ev.status,
              detail: ev.detail || null,
              created_at: ev.created_at || new Date().toISOString(),
            },
          ].slice(-40));
        }
        break;
      case "agent_typing":
        setPhase(ev.status === "start" ? "typing" : "idle");
        break;
      case "agent_message":
        setPhase("streaming");
        enqueueStreamChunk(ev.message_id, ev.content || "");
        break;
      case "tool_call_start":
        setPhase("tool");
        setToolOverrides((cur) => ({
          ...cur,
          [ev.tool_call_id]: {
            tool_call_id: ev.tool_call_id,
            tool_name: ev.tool_name,
            display_name: ev.display_name,
            arguments: ev.arguments || {},
            status: "executing",
            progress_hint: ev.progress_hint,
            estimated_sec: ev.estimated_sec,
          },
        }));
        if (ev.retry) break;
        flushStreamBuffer();
        commitPartial((cur) => {
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
                progress_hint: ev.progress_hint,
                estimated_sec: ev.estimated_sec,
              },
            ],
          };
        });
        break;
      case "tool_call_done":
        setToolOverrides((cur) => ({
          ...cur,
          [ev.tool_call_id]: {
            status: ev.status,
            result: ev.result,
            error: ev.error,
          },
        }));
        if (ev.retry) {
          setPhase("done");
          break;
        }
        flushStreamBuffer();
        commitPartial((cur) => {
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
        flushStreamBuffer();
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
        commitPartial(() => null);
        if (ev.plan_proposed?.plan_id && typeof ev.plan_proposed.plan_text === "string") {
          setPendingPlan({
            plan_id: ev.plan_proposed.plan_id,
            plan_text: ev.plan_proposed.plan_text,
          });
        }
        if (ev.human_intervention?.request?.id) {
          onHitlRequested?.(ev.human_intervention.request as HitlRequest);
          if (!onHitlRequested) {
            pushToast("info", ev.human_intervention.request.title || "任务等待人工确认");
          }
        }
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
      case "hitl_requested":
        if (ev.request?.id) {
          onHitlRequested?.(ev.request as HitlRequest);
          if (!onHitlRequested) {
            pushToast("info", ev.request.title || "任务等待人工确认");
          }
        }
        break;
      case "plan_resolved":
        setPendingPlan(null);
        break;
      case "inflight_status":
        if (ev.busy && ev.user?.id) {
          setInflightUser({
            id: ev.user.id,
            name: ev.user.name || "用户",
            started_at: ev.started_at || null,
          });
        } else {
          setInflightUser(null);
        }
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
    setCloseInfo(null);
    setTodos([]);
    setTodosUpdatedAt(null);
    setPlanModeState(false);
    setPendingPlan(null);
    setRunEvents([]);
    setToolOverrides({});
    setInflightUser(null);
    pendingQueueRef.current = [];
    streamBufferRef.current = null;
    clearStreamFlush();
    partialRef.current = null;

    if (taskId && conversationId) {
      http
        .get<ApiEnvelope<{ items: RunEvent[] }>>(`/tasks/${taskId}/run-events`, {
          params: { conv_id: conversationId, limit: 40 },
        })
        .then((r) => {
          if (r.data.code === 0 && Array.isArray(r.data.data.items)) {
            setRunEvents(r.data.data.items);
          }
        })
        .catch(() => {});
    }
  }, [clearStreamFlush, conversationId, taskId]);

  useEffect(() => {
    connect();
    return () => {
      if (retryTimerRef.current) window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
      clearStreamFlush();
      streamBufferRef.current = null;
      // Invalidate any in-flight ensureFreshToken() continuation and detach
      // the current socket before close(). Otherwise the old onclose handler
      // can observe wsRef.current === ws after unmount and schedule a fresh
      // reconnect loop in the background.
      connectSeqRef.current += 1;
      const ws = wsRef.current;
      wsRef.current = null;
      ws?.close();
    };
  }, [clearStreamFlush, connect]);

  const send = (content: string, opts?: { model?: string }) => {
    setErrorCode(null);
    setRunEvents([]);
    setToolOverrides({});
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
      enqueuePending(payloadStr);
      return;
    }
    // CLOSED / CLOSING：WS 没在路上；先塞队列，再触发一次 connect() 确保重连
    enqueuePending(payloadStr);
    setErrorCode("WS_DISCONNECTED");
    setPhase("error");
    connect();
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

  const retryToolCall = (call: ToolCall) => {
    setErrorCode(null);
    sendControl({ type: "retry_tool_call", tool_call_id: call.tool_call_id });
  };

  const sendControl = (payload: Record<string, unknown>) => {
    const rs = wsRef.current?.readyState;
    const body = JSON.stringify(payload);
    if (rs === WebSocket.OPEN) {
      wsRef.current!.send(body);
    } else if (rs === WebSocket.CONNECTING) {
      enqueuePending(body);
    } else {
      enqueuePending(body);
      connect();
    }
  };

  const setPlanMode = (enabled: boolean) => {
    // Optimistic UI update; authoritative value comes back via plan_mode_changed.
    setPlanModeState(enabled);
    if (!enabled) setPendingPlan(null);
    sendControl({ type: "set_plan_mode", enabled });
  };

  const approvePlan = (planId: string, approvedSteps?: number[]) => {
    setPendingPlan(null);
    const payload: Record<string, unknown> = { type: "approve_plan", plan_id: planId };
    if (approvedSteps && approvedSteps.length > 0) {
      payload.approved_steps = approvedSteps;
    }
    sendControl(payload);
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
    runEvents,
    toolOverrides,
    send,
    retryToolCall,
    abort,
    setPlanMode,
    approvePlan,
    rejectPlan,
    errorCode,
    closeInfo,
    inflightUser,
    clearError: () => setErrorCode(null),
  };
}
