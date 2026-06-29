import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { agentApi, conversationApi, fileApi, joinRequestApi, kbApi, scheduledApi, skillApi, sysApi, taskApi } from "@/api/endpoints";
import type { KBArticle, KBSummary, ScheduledTask } from "@/api/endpoints";
import { TopNav } from "@/components/shell/TopNav";
import type { ChatInputRef } from "@/components/chat/ChatInput";
import { CrystallizeModal } from "@/components/chat/CrystallizeModal";
import { VoiceConversationOverlay } from "@/components/chat/VoiceConversationOverlay";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/Skeleton";
import ImportLinkDialog from "@/components/task/ImportLinkDialog";
import { InviteCollaboratorsDialog } from "@/components/task/InviteCollaboratorsDialog";
import PlanApprovalModal from "@/components/chat/PlanApprovalModal";
import { useChatSocket } from "@/hooks/useChatSocket";
import { useFileUpload } from "@/hooks/useFileUpload";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { ShareToggle } from "./components/ShareToggle";
import { WorkspaceSidebar } from "./WorkspaceSidebar";
import { WorkspaceChatArea } from "./WorkspaceChatArea";
import { WorkspaceRightPanel } from "./WorkspaceRightPanel";
import { WorkspaceMobileSegments } from "./WorkspaceMobileSegments";
import type { FileCategory } from "./utils";
import type {
  AgentCard,
  ChatMessage,
  ConversationMessagesPage,
  FileMeta,
  HitlRequest,
  SkillCard,
  TaskDetail,
} from "@/types/api";
import "./Workspace.css";

const HISTORY_PAGE_SIZE = 80;

// task.role 由后端 derive_task_role 派生回传，前端绝不重算——一旦双源各算
// 一份，viewer 拿到编辑态 UI 的漏档 BUG 就会重现。
function readTaskRole(
  task: TaskDetail,
): "owner" | "editor" | "viewer" | "admin" | null {
  return task.role ?? null;
}

export function WorkspacePage() {
  const { taskId = "" } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const pushToast = useUIStore((s) => s.pushToast);
  const voiceEnabled = useUIStore((s) => s.voiceEnabled);
  const setVoiceEnabled = useUIStore((s) => s.setVoiceEnabled);
  const currentUser = useAuthStore((s) => s.user);
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [agent, setAgent] = useState<AgentCard | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyNextBefore, setHistoryNextBefore] = useState<number | null>(null);
  const [historyLoadingOlder, setHistoryLoadingOlder] = useState(false);
  const [files, setFiles] = useState<FileMeta[]>([]);
  // 文件区分组折叠状态——key 是 category, value 是是否展开。默认全开。
  const [fileGroupCollapsed, setFileGroupCollapsed] = useState<Record<FileCategory, boolean>>({
    sql: false,
    data: false,
    other: false,
  });
  const chatInputRef = useRef<ChatInputRef>(null);
  // 对话列表刷新键
  const [convListReloadKey, setConvListReloadKey] = useState(0);
  // 当前对话是否还在后台跑
  const [convInflightMap, setConvInflightMap] = useState<Record<string, boolean>>({});
  // 本任务创建时绑定的 skills
  const [allSkills, setAllSkills] = useState<SkillCard[]>([]);
  // Agent 目录下的所有文件 + 当前预览
  const [agentFiles, setAgentFiles] = useState<
    { path: string; name: string; size: number; dir: string; text: boolean; ext: string }[]
  >([]);
  const [agentFilePreview, setAgentFilePreview] = useState<
    { path: string; name: string; content: string | null; binary: boolean; truncated?: boolean } | null
  >(null);
  const [agentFileLoading, setAgentFileLoading] = useState(false);
  // Skill 添加/删除
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [skillBusy, setSkillBusy] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<
    "execution" | "conv" | "scheduled" | "skill" | "agent"
  >("execution");
  const [kbs, setKbs] = useState<KBSummary[]>([]);
  const [expandedKbId, setExpandedKbId] = useState<string | null>(null);
  const [kbArticles, setKbArticles] = useState<Record<string, KBArticle[]>>({});
  const [kbBusy, setKbBusy] = useState<string | null>(null);
  const [scheduledItems, setScheduledItems] = useState<ScheduledTask[]>([]);
  const [hitlRequests, setHitlRequests] = useState<HitlRequest[]>([]);
  const [hitlBusy, setHitlBusy] = useState(false);
  const [activeFile, setActiveFile] = useState<FileMeta | null>(null);
  const [activeContent, setActiveContent] = useState<string | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [crystallizeFor, setCrystallizeFor] = useState<ChatMessage | null>(null);
  const [mobileActionsOpen, setMobileActionsOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<"files" | "chat" | "right">("chat");
  const [model, setModel] = useState<string>("");
  const [importOpen, setImportOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [voiceConvOpen, setVoiceConvOpen] = useState(false);
  const [editAccessRequested, setEditAccessRequested] = useState(false);
  const taskNeedsHuman =
    hitlRequests.length > 0 || /paused|pending|approval|error/i.test(String(task?.status || ""));

  // ---- 左右栏可拖拽宽度（localStorage 持久化）----
  const LS_LEFT = "ws-left-w";
  const LS_RIGHT = "ws-right-w";
  const MIN_LEFT = 180;
  const MAX_LEFT = 520;
  const MIN_RIGHT = 240;
  const MAX_RIGHT = 600;
  const readW = (key: string, def: number) => {
    const raw = typeof window !== "undefined" ? localStorage.getItem(key) : null;
    const n = raw ? parseInt(raw, 10) : NaN;
    return Number.isFinite(n) ? n : def;
  };
  const [leftW, setLeftW] = useState(() => readW(LS_LEFT, 280));
  const [rightW, setRightW] = useState(() => readW(LS_RIGHT, 320));
  const startResize = (
    which: "left" | "right",
    e: React.MouseEvent,
  ) => {
    e.preventDefault();
    const startX = e.clientX;
    const startLeft = leftW;
    const startRight = rightW;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    let lastLeft = startLeft;
    let lastRight = startRight;
    const onMove = (me: MouseEvent) => {
      const dx = me.clientX - startX;
      if (which === "left") {
        lastLeft = Math.min(MAX_LEFT, Math.max(MIN_LEFT, startLeft + dx));
        setLeftW(lastLeft);
      } else {
        lastRight = Math.min(MAX_RIGHT, Math.max(MIN_RIGHT, startRight - dx));
        setRightW(lastRight);
      }
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      localStorage.setItem(LS_LEFT, String(lastLeft));
      localStorage.setItem(LS_RIGHT, String(lastRight));
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const socket = useChatSocket({
    taskId,
    conversationId,
    onError: (code, msg) => pushToast("error", `${msg}（${code}）`),
    onFileCreated: () => {
      fileApi
        .listTask(taskId)
        .then((r) => setFiles(r.items))
        .catch(() => {});
    },
    onHitlRequested: (request) => {
      setHitlRequests((arr) => {
        if (arr.some((it) => it.id === request.id)) return arr;
        return [request, ...arr];
      });
      pushToast("info", request.title || "任务等待人工确认");
    },
  });

  const applyHistoryPage = useCallback(
    (page: ConversationMessagesPage, mode: "replace" | "prepend" = "replace") => {
      setHistory((cur) => (mode === "prepend" ? [...page.messages, ...cur] : page.messages));
      setHistoryHasMore(Boolean(page.has_more));
      setHistoryNextBefore(page.next_before ?? null);
    },
    [],
  );

  const upload = useFileUpload({
    taskId,
    onSuccess: (m) => {
      setFiles((arr) => [m, ...arr]);
      pushToast("success", `${m.name} 已上传`);
    },
  });

  // 一次性拉 voice_enabled
  useEffect(() => {
    if (voiceEnabled !== null) return;
    sysApi
      .toggles()
      .then((t) => setVoiceEnabled(Boolean(t.voice_enabled)))
      .catch(() => setVoiceEnabled(false));
  }, [voiceEnabled, setVoiceEnabled]);

  useEffect(() => {
    let cancelled = false;
    setLoadErr(null);
    Promise.all([
      taskApi.detail(taskId),
      taskApi.conversation(taskId, { limit: HISTORY_PAGE_SIZE }),
      fileApi.listTask(taskId),
      taskApi.listHitl(taskId).catch(() => ({ items: [] as HitlRequest[] })),
      skillApi.list().catch(() => ({ items: [] as SkillCard[] })),
    ])
      .then(async ([t, conv, fs, hitl, skills]) => {
        if (cancelled) return;
        setTask(t);
        setConversationId(conv.conversation_id);
        applyHistoryPage(conv);
        setFiles(fs.items);
        setHitlRequests(hitl.items);
        setAllSkills(skills.items);
        if (t.workspace?.model) setModel(t.workspace.model);
        if (t.agent_id) {
          try {
            const a = await agentApi.get(t.agent_id);
            setAgent(a);
          } catch {
            /* ignore */
          }
          try {
            const af = await agentApi.listFiles(t.agent_id);
            setAgentFiles(af.items);
          } catch {
            setAgentFiles([]);
          }
        }
      })
      .catch((e) => setLoadErr(e.message));
    return () => {
      cancelled = true;
    };
  }, [applyHistoryPage, taskId]);

  // 加载可用的知识库
  useEffect(() => {
    kbApi
      .list()
      .then((r) => setKbs(r.items))
      .catch(() => {});
  }, []);

  // 加载本任务的定时任务
  const reloadScheduled = async () => {
    try {
      const r = await scheduledApi.listByTask(taskId);
      setScheduledItems(r.items);
    } catch {
      setScheduledItems([]);
    }
  };
  useEffect(() => {
    reloadScheduled();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);
  useEffect(() => {
    if (activeRightTab === "scheduled") void reloadScheduled();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRightTab, taskId]);

  const reloadHitl = async () => {
    try {
      const r = await taskApi.listHitl(taskId);
      setHitlRequests(r.items);
    } catch {
      setHitlRequests([]);
    }
  };

  const loadKbArticles = async (kb: KBSummary) => {
    if (kbArticles[kb.id]) return;
    setKbBusy(kb.id);
    try {
      const r = await kbApi.articles(kb.id);
      setKbArticles((m) => ({ ...m, [kb.id]: r.items }));
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setKbBusy(null);
    }
  };

  const toggleKb = async (kb: KBSummary) => {
    if (expandedKbId === kb.id) {
      setExpandedKbId(null);
      return;
    }
    setExpandedKbId(kb.id);
    await loadKbArticles(kb);
  };

  const referenceKbArticle = async (kb: KBSummary, a: KBArticle) => {
    setKbBusy(`${kb.id}:${a.id}`);
    try {
      const meta = await fileApi.import_(
        taskId,
        "kb_article",
        a.url || `kb://${kb.id}/${a.id}`,
        { kb_id: kb.id, article_id: a.id },
      );
      pushToast("success", `已引用「${a.title}」到任务文件`);
      setFiles((arr) => [...arr, meta as unknown as FileMeta]);
    } catch (err) {
      const e = err as { errorCode?: string; message: string };
      if (e.errorCode === "IMPORT_DUPLICATE") {
        pushToast("info", "该文档已引用过");
      } else {
        pushToast("error", e.message);
      }
    } finally {
      setKbBusy(null);
    }
  };

  const downloadFile = async (f: FileMeta) => {
    try {
      const { blob, filename } = await fileApi.download(taskId, f.file_id ?? f.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || f.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      pushToast("error", `下载失败：${(err as Error).message}`);
    }
  };

  const openFile = async (f: FileMeta) => {
    setActiveFile(f);
    setActiveContent(null);
    try {
      const r = await fileApi.read(taskId, f.id);
      setActiveContent(r.binary ? "[二进制文件，无法预览]" : r.content || "");
    } catch (err) {
      setActiveContent(`加载失败：${(err as Error).message}`);
    }
  };

  const removeFile = async (f: FileMeta) => {
    try {
      await fileApi.remove(taskId, f.id);
      setFiles((arr) => arr.filter((x) => x.id !== f.id));
      if (activeFile?.id === f.id) {
        setActiveFile(null);
        setActiveContent(null);
      }
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const refreshFile = async (f: FileMeta) => {
    try {
      await fileApi.refresh(taskId, f.file_id ?? f.id);
      const r = await fileApi.listTask(taskId);
      setFiles(r.items);
      pushToast("success", `${f.name} 已刷新`);
    } catch (err) {
      pushToast("error", `刷新失败：${(err as Error).message}`);
    }
  };

  const refreshTaskData = async () => {
    try {
      const t = await taskApi.detail(taskId);
      const fs = await fileApi.listTask(taskId);
      const hitl = await taskApi.listHitl(taskId).catch(() => ({ items: [] as HitlRequest[] }));
      setTask(t);
      setFiles(fs.items);
      setHitlRequests(hitl.items);
      if (conversationId) {
        const conv = await conversationApi.get(taskId, conversationId, { limit: HISTORY_PAGE_SIZE });
        applyHistoryPage(conv);
      } else {
        const conv = await taskApi.conversation(taskId, { limit: HISTORY_PAGE_SIZE });
        setConversationId(conv.conversation_id);
        applyHistoryPage(conv);
      }
      pushToast("success", "已刷新");
      setConvListReloadKey((k) => k + 1);
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  // ConversationTab 重拉触发器
  useEffect(() => {
    setConvListReloadKey((k) => k + 1);
  }, [socket.finalized.length, conversationId]);

  useEffect(() => {
    if (socket.phase !== "done") return;
    taskApi
      .detail(taskId)
      .then((t) => setTask(t))
      .catch(() => {});
    reloadHitl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socket.phase, taskId]);

  // 当前对话从「后台还在跑」转为「跑完了」时，自动拉一次最新历史
  const prevInflightRef = useRef<{ convId: string | null; inflight: boolean }>({
    convId: null,
    inflight: false,
  });
  useEffect(() => {
    if (!conversationId) return;
    const cur = !!convInflightMap[conversationId];
    const prev = prevInflightRef.current;
    const sameConv = prev.convId === conversationId;
    const transitionedDone = sameConv && prev.inflight === true && cur === false;
    if (transitionedDone && socket.finalized.length === 0) {
      conversationApi
        .get(taskId, conversationId, { limit: HISTORY_PAGE_SIZE })
        .then((data) => applyHistoryPage(data))
        .catch(() => {});
    }
    prevInflightRef.current = { convId: conversationId, inflight: cur };
  }, [applyHistoryPage, convInflightMap, conversationId, taskId, socket.finalized.length]);

  const loadMessagesForBulkAction = useCallback(async (): Promise<ChatMessage[]> => {
    if (!conversationId || !historyHasMore || historyNextBefore == null) {
      return [...history, ...socket.finalized];
    }
    const older: ChatMessage[] = [];
    let before: number | null = historyNextBefore;
    for (let guard = 0; before != null && guard < 50; guard += 1) {
      const page = await conversationApi.get(taskId, conversationId, {
        limit: 200,
        before,
      });
      older.unshift(...page.messages);
      before = page.next_before ?? null;
      if (!page.has_more) break;
    }
    return [...older, ...history, ...socket.finalized];
  }, [
    conversationId,
    history,
    historyHasMore,
    historyNextBefore,
    socket.finalized,
    taskId,
  ]);

  const exportConversation = async () => {
    try {
      const messages = await loadMessagesForBulkAction();
      const lines: string[] = [];
      lines.push(`# ${task?.name || "对话导出"}`);
      lines.push("");
      lines.push(`- Agent：${agent?.name || task?.agent_id || "-"}`);
      lines.push(`- 任务 ID：${taskId}`);
      lines.push(`- 导出时间：${new Date().toLocaleString()}`);
      lines.push(`- 消息条数：${messages.length}`);
      lines.push("");
      lines.push("---");
      lines.push("");

      for (const m of messages) {
        const role = m.role === "user" ? "👤 用户" : m.role === "assistant" ? "🤖 Agent" : m.role;
        const ts = m.created_at ? new Date(m.created_at).toLocaleString() : "";
        lines.push(`## ${role}${ts ? ` · ${ts}` : ""}`);
        lines.push("");
        if (m.content) {
          lines.push(m.content);
          lines.push("");
        }
        const tools = m.tool_uses || [];
        if (tools.length > 0) {
          lines.push("**🛠 工具调用**");
          lines.push("");
          for (const tu of tools) {
            const argStr = (() => {
              try {
                return "```json\n" + JSON.stringify(tu.input ?? {}, null, 2) + "\n```";
              } catch {
                return String(tu.input ?? "");
              }
            })();
            lines.push(`- \`${tu.name}\``);
            lines.push(argStr);
          }
          lines.push("");
        }
        lines.push("---");
        lines.push("");
      }

      const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const safeName = (task?.name || "conversation").replace(/[\\/:*?"<>|]/g, "_");
      const stamp = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 16);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeName}-${stamp}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      pushToast("success", "对话已导出为 Markdown");
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const allMessages: ChatMessage[] = useMemo(
    () => [...history, ...socket.finalized],
    [history, socket.finalized],
  );
  const kbImportedFiles = useMemo(
    () => files.filter((f) => f.source_type === "kb_article"),
    [files],
  );
  const kbReferenced = useMemo(() => {
    const set = new Set<string>();
    for (const f of kbImportedFiles) {
      const ref = f.source_ref;
      if (ref?.kb_id && ref.article_id) set.add(`${ref.kb_id}:${ref.article_id}`);
    }
    return set;
  }, [kbImportedFiles]);
  const handleCrystallize = useCallback(
    (m: ChatMessage) => setCrystallizeFor(m),
    [],
  );
  const handleSend = useCallback(
    (text: string) => socket.send(text, { model }),
    [socket, model],
  );

  const loadOlderHistory = useCallback(async () => {
    if (!conversationId || historyLoadingOlder || historyNextBefore == null) return;
    setHistoryLoadingOlder(true);
    try {
      const page = await conversationApi.get(taskId, conversationId, {
        limit: HISTORY_PAGE_SIZE,
        before: historyNextBefore,
      });
      applyHistoryPage(page, "prepend");
    } catch (err) {
      pushToast("error", `加载更早消息失败：${(err as Error).message}`);
    } finally {
      setHistoryLoadingOlder(false);
    }
  }, [
    applyHistoryPage,
    conversationId,
    historyLoadingOlder,
    historyNextBefore,
    pushToast,
    taskId,
  ]);

  const requestEditAccess = useCallback(async () => {
    try {
      await joinRequestApi.submit(taskId, "申请将只读权限升级为编辑");
      setEditAccessRequested(true);
      pushToast("success", "已发送申请，等待任务所有者审批");
    } catch (err: any) {
      const code = err?.response?.data?.error_code as string | undefined;
      if (code === "JOIN_ALREADY_PENDING") {
        setEditAccessRequested(true);
        pushToast("info", "已有待审批申请，请等待任务所有者处理");
      } else if (code === "JOIN_ALREADY_MEMBER") {
        pushToast("info", "你已是该任务成员，正在刷新…");
        try {
          const t = await taskApi.detail(taskId);
          setTask(t);
        } catch {/* ignore */}
      } else {
        pushToast("error", `申请失败：${err?.response?.data?.message ?? (err as Error).message}`);
      }
    }
  }, [taskId, pushToast]);

  // ---- Skill update handler ----
  const updateSkills = useCallback(async (next: string[]) => {
    if (!taskId || skillBusy) return;
    setSkillBusy(true);
    try {
      await taskApi.updateSkills(taskId, next);
      const t = await taskApi.detail(taskId);
      setTask(t);
      pushToast("success", "已更新 skill");
    } catch (err) {
      pushToast("error", (err as Error).message || "更新 skill 失败");
    } finally {
      setSkillBusy(false);
    }
  }, [taskId, skillBusy, pushToast]);

  // ---- Agent file click handler ----
  const handleAgentFileClick = useCallback(async (path: string) => {
    if (!agent) return;
    setAgentFileLoading(true);
    try {
      const r = await agentApi.readFile(agent.id, path);
      setAgentFilePreview(r);
    } catch (err) {
      pushToast("error", (err as Error).message || "读取失败");
    } finally {
      setAgentFileLoading(false);
    }
  }, [agent, pushToast]);

  // ---- Conversation select handler ----
  const handleConvSelect = useCallback(async (cid: string) => {
    if (cid === conversationId) return;
    setHistory([]);
    setHistoryHasMore(false);
    setHistoryNextBefore(null);
    setConversationId(cid);
    try {
      const data = await conversationApi.get(taskId, cid, { limit: HISTORY_PAGE_SIZE });
      applyHistoryPage(data);
    } catch (err: any) {
      pushToast(
        "error",
        "加载对话历史失败：" + (err?.response?.data?.message ?? String(err)),
      );
    }
  }, [applyHistoryPage, conversationId, pushToast, taskId]);

  // ---- Abort conversation handler ----
  const handleAbortConversation = useCallback(async () => {
    if (!conversationId) return;
    try {
      const r = await conversationApi.abort(taskId, conversationId);
      pushToast(
        r.cancelled ? "success" : "info",
        r.cancelled
          ? "已通知后台终止当前回合"
          : "后台没有进行中的回合（可能已结束）",
      );
      socket.clearError();
    } catch (err) {
      pushToast("error", `终止失败：${(err as Error).message}`);
    }
  }, [conversationId, pushToast, socket, taskId]);

  // ---- HITL resolve handler ----
  const handleResolveHitl = useCallback(async (
    payload: Record<string, unknown>,
    decision: string,
    note?: string,
  ) => {
    const req = hitlRequests[0];
    if (!req) {
      pushToast("info", "当前没有待处理的人工干预请求");
      return;
    }
    setHitlBusy(true);
    try {
      await taskApi.resolveHitl(taskId, req.id, { decision, payload, note });
      await reloadHitl();
      const t = await taskApi.detail(taskId);
      setTask(t);
      pushToast("success", "已记录人工处理结果，正在继续执行");
      socket.send("请基于刚才的人工修正继续执行。", { model });
    } catch (err) {
      pushToast("error", `处理失败：${(err as Error).message}`);
    } finally {
      setHitlBusy(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hitlRequests, model, pushToast, socket, taskId]);

  if (loadErr) {
    return (
      <div className="ws">
        <TopNav mode="workspace" />
        <div className="ws-error">
          <ErrorState icon="🚫" title="任务加载失败" description={loadErr} errorCode="TASK_LOAD_FAILED" />
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="ws">
        <TopNav mode="workspace" />
        <div className="ws-loading">
          <Skeleton lines={6} />
        </div>
      </div>
    );
  }

  const wsErrCode = socket.errorCode;
  const wsCloseInfo = socket.closeInfo;
  const isStreaming = ["streaming", "tool", "typing"].includes(socket.phase);
  const role = readTaskRole(task);
  const canWrite = role === "editor" || role === "owner" || role === "admin";
  const isOwnerLike = role === "owner" || role === "admin";
  const isViewer = role === "viewer";

  const inflight = socket.inflightUser;
  const lockedByOther = !!inflight && inflight.id !== currentUser?.id;
  const lockedBySelfElsewhere =
    !!inflight && inflight.id === currentUser?.id && !isStreaming;
  const conversationLocked = lockedByOther || lockedBySelfElsewhere;

  const handleNewConvFromLock = async () => {
    try {
      const conv = await conversationApi.create(taskId);
      setConversationId(conv.id);
      setHistory([]);
      setHistoryHasMore(false);
      setHistoryNextBefore(null);
      setConvListReloadKey((k) => k + 1);
    } catch (err) {
      pushToast("error", `新建对话失败：${(err as Error).message}`);
    }
  };

  const renameTask = async () => {
    const next = window.prompt("新的任务名称", task.name);
    const name = (next || "").trim();
    if (!name || name === task.name) return;
    try {
      const updated = await taskApi.update(taskId, { name });
      setTask(updated);
      pushToast("success", "任务已重命名");
    } catch (err) {
      pushToast("error", `重命名失败：${(err as Error).message}`);
    }
  };

  return (
    <div className="ws v6-workspace">
      <TopNav
        mode="workspace"
        crumb={
          <span className="ws-crumb">
            <button
              type="button"
              className="ws-back-home"
              onClick={() => navigate("/dashboard")}
              title="返回首页"
              aria-label="返回首页"
            >
              ← 首页
            </button>
            <span className="ws-crumb-sep">/</span>
            <details className="ws-task-menu">
              <summary className="current">
                <span>{task.name}</span>
                <span className="ws-task-menu-caret">▾</span>
              </summary>
              <div className="ws-task-menu-pop">
                <div className="ws-task-menu-title">任务操作</div>
                <button type="button" onClick={renameTask} disabled={!canWrite} title={canWrite ? "修改任务名称" : "当前身份无权修改"}>
                  重命名任务
                </button>
                <button type="button" onClick={() => navigate(`/scheduled-tasks?taskId=${encodeURIComponent(taskId)}&create=1`)}>
                  配置定时调度
                  <small>{scheduledItems.length > 0 ? `${scheduledItems.length} 个` : "Off"}</small>
                </button>
                <button type="button" onClick={exportConversation}>导出结果文件</button>
                <button type="button" className="danger" onClick={() => navigate("/dashboard")}>返回仪表盘</button>
              </div>
            </details>
            {taskNeedsHuman && (
              <span className="ws-v6-status-pill">
                <span className="v6-pulse" />
                等待处理
              </span>
            )}
          </span>
        }
        agentChip={
          agent ? (
            <span>
              {agent.icon} {agent.name} · <span style={{ color: "var(--text-muted)" }}>{agent.paradigm}</span>
            </span>
          ) : null
        }
        rightActions={
          <>
            <div className="ws-actions-desktop">
              {isOwnerLike && (
                <ShareToggle
                  taskId={taskId}
                  visibility={task.visibility}
                  publishStatus={(task as any).publish_status}
                  onChanged={async () => {
                    const t = await taskApi.detail(taskId);
                    setTask(t);
                  }}
                />
              )}
              {isOwnerLike && (
                <button
                  className="btn-ghost"
                  onClick={() => setInviteOpen(true)}
                  title="邀请其他用户协作此任务"
                >
                  👥 邀请协作
                </button>
              )}
            </div>
            <div className="ws-actions-mobile">
              <button
                className="ws-actions-more"
                onClick={() => setMobileActionsOpen((v) => !v)}
                aria-label="更多操作"
                aria-expanded={mobileActionsOpen}
              >
                ⋯
              </button>
              {mobileActionsOpen && (
                <>
                  <div
                    className="ws-sec-more-mask"
                    onClick={() => setMobileActionsOpen(false)}
                  />
                  <div className="ws-sec-more-menu ws-actions-mobile-menu" role="menu">
                    {isOwnerLike && (
                      <div onClick={() => setMobileActionsOpen(false)} role="presentation">
                        <ShareToggle
                          taskId={taskId}
                          visibility={task.visibility}
                          publishStatus={(task as any).publish_status}
                          onChanged={async () => {
                            const t = await taskApi.detail(taskId);
                            setTask(t);
                          }}
                        />
                      </div>
                    )}
                    {isOwnerLike && (
                      <button
                        onClick={() => {
                          setMobileActionsOpen(false);
                          setInviteOpen(true);
                        }}
                      >
                        👥 邀请协作
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setMobileActionsOpen(false);
                        exportConversation();
                      }}
                    >
                      💾 导出对话
                    </button>
                    <button
                      onClick={() => {
                        setMobileActionsOpen(false);
                        refreshTaskData();
                      }}
                    >
                      🔁 重新加载
                    </button>
                    <button
                      onClick={() => {
                        setMobileActionsOpen(false);
                        if (conversationId) socket.setPlanMode(!socket.planMode);
                      }}
                      disabled={!conversationId}
                      title="计划模式：agent 先出方案，你批准后再执行"
                    >
                      🧭 {socket.planMode ? "Plan Mode 已开" : "进入 Plan Mode"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </>
        }
      />

      <div
        className="ws-body"
        data-mobile-tab={mobileTab}
        style={{
          gridTemplateColumns: `${leftW}px 6px 1fr 6px ${rightW}px`,
        }}
      >
        <WorkspaceSidebar
          taskId={taskId}
          files={files}
          upload={upload}
          fileGroupCollapsed={fileGroupCollapsed}
          onFileGroupToggle={(key) =>
            setFileGroupCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))
          }
          kbs={kbs}
          expandedKbId={expandedKbId}
          kbArticles={kbArticles}
          kbBusy={kbBusy}
          kbReferenced={kbReferenced}
          activeFile={activeFile}
          activeContent={activeContent}
          agent={agent}
          canWrite={canWrite}
          isOwnerLike={isOwnerLike}
          chatInputRef={chatInputRef}
          onOpenFile={openFile}
          onDownloadFile={downloadFile}
          onRemoveFile={removeFile}
          onRefreshFile={refreshFile}
          onToggleKb={toggleKb}
          onReferenceKbArticle={referenceKbArticle}
          onCloseFilePreview={() => {
            setActiveFile(null);
            setActiveContent(null);
          }}
          onOpenImport={() => setImportOpen(true)}
          pushToast={pushToast}
        />

        <div
          className="ws-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整左侧宽度"
          onMouseDown={(e) => startResize("left", e)}
          onDoubleClick={() => setLeftW(280)}
          title="拖动调整宽度 · 双击恢复默认"
        />

        <WorkspaceChatArea
          task={task}
          taskId={taskId}
          agent={agent}
          role={role}
          canWrite={canWrite}
          isViewer={isViewer}
          chatHeadProps={{
            model,
            onModelChange: setModel,
            onExport: exportConversation,
            onReload: refreshTaskData,
            loadMessagesForBulkAction,
            pushToast,
          }}
          allMessages={allMessages}
          partial={socket.partial}
          phase={socket.phase}
          wsErrCode={wsErrCode}
          wsCloseInfo={wsCloseInfo}
          isStreaming={isStreaming}
          planMode={socket.planMode}
          pendingPlan={socket.pendingPlan}
          toolOverrides={socket.toolOverrides}
          conversationId={conversationId}
          conversationLocked={conversationLocked}
          lockedByOther={lockedByOther}
          lockedBySelfElsewhere={lockedBySelfElsewhere}
          inflight={inflight}
          hitlRequests={hitlRequests}
          hitlBusy={hitlBusy}
          taskNeedsHuman={taskNeedsHuman}
          kbImportedFiles={kbImportedFiles}
          files={files}
          chatInputRef={chatInputRef}
          voiceEnabled={voiceEnabled}
          editAccessRequested={editAccessRequested}
          historyHasMore={historyHasMore}
          historyLoadingOlder={historyLoadingOlder}
          backgroundInflight={
            !!conversationId &&
            !!convInflightMap[conversationId] &&
            !["streaming", "tool", "typing"].includes(socket.phase)
          }
          onSend={handleSend}
          onAbort={socket.abort}
          onRetryToolCall={socket.retryToolCall as any}
          onCrystallize={handleCrystallize}
          onLoadOlderHistory={loadOlderHistory}
          onSetPlanMode={socket.setPlanMode}
          onNewConvFromLock={handleNewConvFromLock}
          onRequestEditAccess={requestEditAccess}
          onSetActiveRightTab={(tab) => setActiveRightTab(tab as any)}
          onResolveHitl={handleResolveHitl}
          onTaskUpdated={async () => {
            const t = await taskApi.detail(taskId);
            setTask(t);
          }}
          onAbortConversation={handleAbortConversation}
          onRefreshTaskData={refreshTaskData}
          onClearError={socket.clearError}
          onRemoveFile={removeFile}
          onVoiceConvOpen={() => setVoiceConvOpen(true)}
          model={model}
          pushToast={pushToast}
        />

        <div
          className="ws-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整右侧宽度"
          onMouseDown={(e) => startResize("right", e)}
          onDoubleClick={() => setRightW(320)}
          title="拖动调整宽度 · 双击恢复默认"
        />

        <WorkspaceRightPanel
          task={task}
          taskId={taskId}
          agent={agent}
          phase={socket.phase}
          status={socket.status}
          todos={socket.todos}
          todosUpdatedAt={socket.todosUpdatedAt}
          runEvents={socket.runEvents}
          planMode={socket.planMode}
          pendingPlan={socket.pendingPlan}
          inflightUser={socket.inflightUser}
          activeRightTab={activeRightTab}
          onSetActiveRightTab={setActiveRightTab}
          currentUserId={currentUser?.id}
          scheduledItems={scheduledItems}
          canWrite={canWrite}
          onTogglePlanMode={() => {
            if (conversationId) socket.setPlanMode(!socket.planMode);
          }}
          onApprovePlan={(pid) => socket.approvePlan(pid)}
          onRejectPlan={(pid) => socket.rejectPlan(pid)}
          onOpenScheduled={() => setActiveRightTab("scheduled")}
          conversationId={conversationId}
          convListReloadKey={convListReloadKey}
          onConvItemsLoaded={(items) => {
            const map: Record<string, boolean> = {};
            for (const c of items) {
              if (c.inflight) map[c.id] = true;
            }
            setConvInflightMap(map);
          }}
          onConvSelect={handleConvSelect}
          onReloadScheduled={reloadScheduled}
          allSkills={allSkills}
          skillPickerOpen={skillPickerOpen}
          onSkillPickerToggle={() => setSkillPickerOpen((v) => !v)}
          skillBusy={skillBusy}
          onUpdateSkills={updateSkills}
          agentFiles={agentFiles}
          agentFilePreview={agentFilePreview}
          agentFileLoading={agentFileLoading}
          onAgentFileClick={handleAgentFileClick}
          onAgentFilePreviewClose={() => setAgentFilePreview(null)}
          pushToast={pushToast}
        />
      </div>

      <CrystallizeModal
        open={!!crystallizeFor}
        taskId={taskId}
        sourceMessage={crystallizeFor && { id: crystallizeFor.id, content: crystallizeFor.content }}
        onClose={() => setCrystallizeFor(null)}
      />

      <ImportLinkDialog
        open={importOpen}
        taskId={taskId}
        onClose={() => setImportOpen(false)}
        onImported={async () => {
          try {
            const f = await fileApi.listTask(taskId);
            setFiles(f.items);
          } catch (err) {
            pushToast("error", (err as Error).message);
          }
        }}
      />

      <InviteCollaboratorsDialog
        open={inviteOpen}
        taskId={taskId}
        taskName={task.name}
        onClose={() => setInviteOpen(false)}
      />

      {socket.pendingPlan && (
        <PlanApprovalModal
          proposal={socket.pendingPlan}
          onApprove={(pid) => socket.approvePlan(pid)}
          onReject={(pid) => socket.rejectPlan(pid)}
        />
      )}
      <VoiceConversationOverlay
        open={voiceConvOpen}
        onClose={() => setVoiceConvOpen(false)}
        onSend={handleSend}
        phase={socket.phase}
        finalized={allMessages}
      />
      <WorkspaceMobileSegments mobileTab={mobileTab} onTabChange={setMobileTab} />
    </div>
  );
}
