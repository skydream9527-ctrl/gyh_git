import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { agentApi, conversationApi, fileApi, joinRequestApi, kbApi, scheduledApi, shareApi, skillApi, sysApi, taskApi } from "@/api/endpoints";
import type { KBArticle, KBSummary, ScheduledTask } from "@/api/endpoints";
import { TopNav } from "@/components/shell/TopNav";
import { ChatInput } from "@/components/chat/ChatInput";
import type { ChatInputRef } from "@/components/chat/ChatInput";
import { CrystallizeModal } from "@/components/chat/CrystallizeModal";
import { MessageList } from "@/components/chat/MessageList";
import { ModelSelector } from "@/components/chat/ModelSelector";
import { VoiceConversationOverlay } from "@/components/chat/VoiceConversationOverlay";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/Skeleton";
import AgentUpdateBanner from "@/components/task/AgentUpdateBanner";
import ConversationTab from "@/components/task/ConversationTab";
import ImportLinkDialog from "@/components/task/ImportLinkDialog";
import { InviteCollaboratorsDialog } from "@/components/task/InviteCollaboratorsDialog";
import PlanApprovalModal from "@/components/chat/PlanApprovalModal";
import { useChatSocket } from "@/hooks/useChatSocket";
import { useFileUpload } from "@/hooks/useFileUpload";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import type {
  AgentCard,
  ChatMessage,
  FileMeta,
  SkillCard,
  TaskDetail,
} from "@/types/api";
import "./Workspace.css";

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
  const [files, setFiles] = useState<FileMeta[]>([]);
  // 文件区分组折叠状态——key 是 category, value 是是否展开。默认全开。
  // 不持久化：每次进入工作台都从展开状态开始，符合"有文件默认展开"的需求。
  const [fileGroupCollapsed, setFileGroupCollapsed] = useState<Record<FileCategory, boolean>>({
    sql: false,
    data: false,
    other: false,
  });
  const chatInputRef = useRef<ChatInputRef>(null);
  // 对话列表刷新键：finalized 长度变化（一轮消息落地）/ 切对话 / 手动重新加载，
  // 都触发 ConversationTab 重拉一次。否则后端已 bump message_count，UI 仍是 0。
  const [convListReloadKey, setConvListReloadKey] = useState(0);
  // 当前对话是否还在后台跑（即使本 WS 已断流）。用来在切走又切回时
  // 仍然展示「思考中…」横幅，告诉用户"任务没停"。
  const [convInflightMap, setConvInflightMap] = useState<Record<string, boolean>>({});
  // 本任务创建时绑定的 skills — Agent 右栏展示用。只读一次 skillApi.list，按 skill_ids 过滤出本任务的子集。
  const [allSkills, setAllSkills] = useState<SkillCard[]>([]);
  // Agent 目录下的所有文件 + 当前预览
  const [agentFiles, setAgentFiles] = useState<
    { path: string; name: string; size: number; dir: string; text: boolean; ext: string }[]
  >([]);
  const [agentFilePreview, setAgentFilePreview] = useState<
    { path: string; name: string; content: string | null; binary: boolean; truncated?: boolean } | null
  >(null);
  const [agentFileLoading, setAgentFileLoading] = useState(false);
  // Skill 添加/删除：picker 展开态 + 正在提交态
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [skillBusy, setSkillBusy] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<
    "conv" | "skill" | "agent" | "scheduled"
  >("conv");
  const [kbs, setKbs] = useState<KBSummary[]>([]);
  const [expandedKbId, setExpandedKbId] = useState<string | null>(null);
  const [kbArticles, setKbArticles] = useState<Record<string, KBArticle[]>>({});
  const [kbBusy, setKbBusy] = useState<string | null>(null);
  const [scheduledItems, setScheduledItems] = useState<ScheduledTask[]>([]);
  const [activeFile, setActiveFile] = useState<FileMeta | null>(null);
  const [activeContent, setActiveContent] = useState<string | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [crystallizeFor, setCrystallizeFor] = useState<ChatMessage | null>(null);
  const [mobileActionsOpen, setMobileActionsOpen] = useState(false);
  // mobile-only 3-segment switch: files / chat / right
  const [mobileTab, setMobileTab] = useState<"files" | "chat" | "right">("chat");
  const [model, setModel] = useState<string>("");
  const [importOpen, setImportOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [voiceConvOpen, setVoiceConvOpen] = useState(false);
  // viewer 是否已经申请编辑权限（提交成功 / 后端返回已 pending 都视为已申请）
  const [editAccessRequested, setEditAccessRequested] = useState(false);

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
      // 只在 mouseup 时 persist 一次；避免每像素 localStorage 写入
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
  });

  const upload = useFileUpload({
    taskId,
    onSuccess: (m) => {
      setFiles((arr) => [m, ...arr]);
      pushToast("success", `${m.name} 已上传`);
    },
  });

  // 一次性拉 voice_enabled（手机端 PTT / 朗读按钮可见性的唯一开关）。
  // 只在 store 还是 null（未加载）时拉取，避免每次切任务都打一次。
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
      taskApi.conversation(taskId),
      fileApi.listTask(taskId),
      skillApi.list().catch(() => ({ items: [] as SkillCard[] })),
    ])
      .then(async ([t, conv, fs, skills]) => {
        if (cancelled) return;
        setTask(t);
        setConversationId(conv.conversation_id);
        setHistory(conv.messages);
        setFiles(fs.items);
        setAllSkills(skills.items);
        if (t.workspace?.model) setModel(t.workspace.model);
        if (t.agent_id) {
          try {
            const a = await agentApi.get(t.agent_id);
            setAgent(a);
          } catch {
            /* ignore */
          }
          // 拉 agent 目录下所有文件（失败静默 — Agent 详情仍可用）
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
  }, [taskId]);

  // 加载可用的知识库（失败静默：KB 是增量能力）
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
    // 文件预览现在展示在左侧栏文件列表的下方（不再占用右栏 tab）
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

  // 重新拉取任务/对话/文件（不做 location.reload，避免断 WS 与丢未保存状态）。
  // 关键：必须用当前对话 id 拉，否则切到非默认对话再刷新会跳回默认对话，
  // 用户感知到的是"刷新了但内容不对"。
  const refreshTaskData = async () => {
    try {
      const t = await taskApi.detail(taskId);
      const fs = await fileApi.listTask(taskId);
      setTask(t);
      setFiles(fs.items);
      if (conversationId) {
        const conv = await conversationApi.get(taskId, conversationId);
        setHistory(conv.messages);
      } else {
        // 首次进入或 conv 丢失，回退到默认对话
        const conv = await taskApi.conversation(taskId);
        setConversationId(conv.conversation_id);
        setHistory(conv.messages);
      }
      pushToast("success", "已刷新");
      setConvListReloadKey((k) => k + 1);
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  // ConversationTab 重拉触发器：每次本对话有新消息落地（finalized 增长）
  // 或切换对话，都 bump 一次 reloadKey。
  useEffect(() => {
    setConvListReloadKey((k) => k + 1);
  }, [socket.finalized.length, conversationId]);

  // 当前对话从「后台还在跑」转为「跑完了」时，自动拉一次最新历史。
  // 关键：仅在本地 finalized 为空时拉——说明用户不在场（切走又切回的场景）。
  // 否则用户在场刚跑完，finalized 已经有 user+assistant，再从 JSONL 拉一份
  // 回填到 history 会和 finalized 加起来翻倍出现。
  // 用对象 ref 而不是布尔，避免切对话时 prev/cur 错位触发误拉。
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
        .get(taskId, conversationId)
        .then((data) => setHistory(data.messages))
        .catch(() => {});
    }
    prevInflightRef.current = { convId: conversationId, inflight: cur };
  }, [convInflightMap, conversationId, taskId, socket.finalized.length]);

  // 把当前对话（含工具调用摘要）导出为 Markdown 并触发浏览器下载。
  const exportConversation = () => {
    try {
      const messages: ChatMessage[] = [...history, ...socket.finalized];
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

  // 关键性能点：每个 token 流过 useChatSocket 都会让 partial 引用变化，进而让
  // WorkspacePage 重渲染。把 finalized 列表 useMemo 起来，传给 MessageList 内部
  // 的 memo 化 FinalizedList，历史 bubble 就不会随每个 token 重渲染。
  // 注意：所有 hooks 必须在任何 early-return 之前调用，否则首屏 task=null 走早返、
  // 第二次 task 加载完后跑 hooks，会触发 React "Rendered more hooks than during
  // the previous render" 白屏。
  const allMessages: ChatMessage[] = useMemo(
    () => [...history, ...socket.finalized],
    [history, socket.finalized],
  );
  const handleCrystallize = useCallback(
    (m: ChatMessage) => setCrystallizeFor(m),
    [],
  );
  const handleSend = useCallback(
    (text: string) => socket.send(text, { model }),
    [socket, model],
  );

  const requestEditAccess = useCallback(async () => {
    try {
      await joinRequestApi.submit(taskId, "申请将只读权限升级为编辑");
      setEditAccessRequested(true);
      pushToast("success", "已发送申请，等待任务所有者审批");
    } catch (err: any) {
      const code = err?.response?.data?.error_code as string | undefined;
      if (code === "JOIN_ALREADY_PENDING") {
        // 之前提交过，按钮即时反映为「已申请」
        setEditAccessRequested(true);
        pushToast("info", "已有待审批申请，请等待任务所有者处理");
      } else if (code === "JOIN_ALREADY_MEMBER") {
        // 后端判定已是 editor/owner——可能本地 task 缓存陈旧；刷新让 deriveRole 重新判定
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
  // owner/admin 才看到 ShareToggle 与 邀请协作 / 申请审批 等高权限按钮
  const isOwnerLike = role === "owner" || role === "admin";
  const isViewer = role === "viewer";

  // 同一会话同时只能一个用户在跑 turn。后端通过 inflight_status 事件告诉每个 WS
  // 当前是谁占着；占用者 == 我自己且本 tab 在 streaming 时正常展示 ⏸ 暂停按钮，
  // 其他情况都置灰发送框：
  //   • 别人在跑 → 红色 banner 提示用户名，给「新建对话」按钮
  //   • 我自己在另一个 tab 跑 → 灰色 banner 提示，发送也禁用避免两端互冲
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
      setConvListReloadKey((k) => k + 1);
    } catch (err) {
      pushToast("error", `新建对话失败：${(err as Error).message}`);
    }
  };

  return (
    <div className="ws">
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
            <span className="current">{task.name}</span>
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
        <aside className="ws-sidebar">
          <div className="ws-sb-section">
            <div className="ws-sb-head">
              <span>📂 工作文件</span>
              {canWrite && (
                <label className="ws-upload">
                  + 上传
                  <input
                    type="file"
                    multiple
                    onChange={(e) => {
                      if (e.target.files) upload.upload(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </label>
              )}
              {canWrite && (
                <button
                  className="btn-ghost ws-import-btn"
                  onClick={() => setImportOpen(true)}
                  title="从飞书文档 / 知识库链接导入文件"
                >
                  🔗 导入链接
                </button>
              )}
            </div>
            {files.length === 0 && upload.items.length === 0 ? (
              <div className="ws-empty">还没有文件，拖拽或点击上传</div>
            ) : (
              <div className="ws-file-groups">
                {FILE_CATEGORY_DEFS.map((def) => {
                  const groupFiles = files.filter((f) => categorizeFile(f) === def.key);
                  if (groupFiles.length === 0) return null;
                  const collapsed = fileGroupCollapsed[def.key];
                  return (
                    <div
                      key={def.key}
                      className={`ws-file-group${collapsed ? " is-collapsed" : ""}`}
                    >
                      <button
                        type="button"
                        className="ws-file-group-head"
                        onClick={() =>
                          setFileGroupCollapsed((prev) => ({ ...prev, [def.key]: !prev[def.key] }))
                        }
                        aria-expanded={!collapsed}
                      >
                        <span className="ws-fg-caret">{collapsed ? "▸" : "▾"}</span>
                        <span className="ws-fg-icon">{def.icon}</span>
                        <span className="ws-fg-label">{def.label}</span>
                        <span className="ws-fg-count">{groupFiles.length}</span>
                      </button>
                      {!collapsed && (
                        <ul className="ws-file-list">
                          {groupFiles.map((f) => {
                            const isImported = f.scope === "imported";
                            return (
                              <li key={f.id} onClick={() => openFile(f)}>
                                <span
                                  className="fl-icon"
                                  title={isImported ? "已导入链接" : undefined}
                                >
                                  {isImported ? "🔗" : fmtIcon(f.format)}
                                </span>
                                <span
                                  className="fl-name"
                                  title={isImported && f.source_url ? f.source_url : f.name}
                                >
                                  {f.name}
                                </span>
                                <span className="fl-size">{fmtSize(f.size_bytes)}</span>
                                {isImported && (
                                  <button
                                    className="fl-refresh"
                                    onClick={async (e) => {
                                      e.stopPropagation();
                                      try {
                                        await fileApi.refresh(taskId, f.file_id ?? f.id);
                                        const r = await fileApi.listTask(taskId);
                                        setFiles(r.items);
                                        pushToast("success", `${f.name} 已刷新`);
                                      } catch (err) {
                                        pushToast(
                                          "error",
                                          `刷新失败：${(err as Error).message}`,
                                        );
                                      }
                                    }}
                                    title="重新抓取最新内容"
                                  >
                                    ↻
                                  </button>
                                )}
                                <button
                                  className="fl-cite"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    chatInputRef.current?.insertText(`@${f.name} `);
                                    chatInputRef.current?.focus();
                                  }}
                                  title="引用到对话输入框"
                                >
                                  📎
                                </button>
                                <button
                                  className="fl-download"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    downloadFile(f);
                                  }}
                                  title="下载到本地"
                                >
                                  ⬇
                                </button>
                                {isOwnerLike && (
                                  <button
                                    className="fl-del"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      removeFile(f);
                                    }}
                                    title="删除"
                                  >
                                    ×
                                  </button>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  );
                })}
                {upload.items.filter((u) => u.status !== "done").length > 0 && (
                  <ul className="ws-file-list ws-upload-list">
                    {upload.items
                      .filter((u) => u.status !== "done")
                      .map((u, i) => (
                        <li key={`u${i}`} className="ws-upload-row">
                          <span className="fl-icon">⏳</span>
                          <span className="fl-name">{u.name}</span>
                          <span className="fl-size">
                            {u.status === "uploading" ? `${u.percent}%` : u.message || "失败"}
                          </span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* 知识库：展开可引用文档到任务文件 */}
          <div className="ws-sb-section ws-sb-kb">
            <div className="ws-sb-head">
              <span>📚 知识库</span>
              <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
                {kbs.length} 个
              </span>
            </div>
            {kbs.length === 0 ? (
              <div className="ws-empty">暂无可用知识库</div>
            ) : (
              <ul className="ws-kb-list">
                {kbs.map((kb) => {
                  const expanded = expandedKbId === kb.id;
                  const arts = kbArticles[kb.id];
                  const loading = kbBusy === kb.id;
                  return (
                    <li key={kb.id} className="ws-kb-item">
                      <button
                        type="button"
                        className="ws-kb-row"
                        onClick={() => toggleKb(kb)}
                        title={kb.description || kb.name}
                      >
                        <span className="ws-kb-caret">{expanded ? "▾" : "▸"}</span>
                        <span className="ws-kb-icon">
                          {kb.source_type === "feishu_wiki" ? "🪶" : "📚"}
                        </span>
                        <span className="ws-kb-name">{kb.name}</span>
                        <span className="ws-kb-count">{kb.doc_count}</span>
                      </button>
                      {expanded && (
                        <div className="ws-kb-articles">
                          {loading && !arts ? (
                            <Skeleton lines={3} />
                          ) : !arts || arts.length === 0 ? (
                            <div className="ws-empty" style={{ padding: "6px 10px" }}>
                              暂无文档
                            </div>
                          ) : (
                            <ul>
                              {arts.map((a) => {
                                const busy = kbBusy === `${kb.id}:${a.id}`;
                                return (
                                  <li key={a.id} className="ws-kb-article">
                                    <span
                                      className="ws-kb-article-title"
                                      title={a.title}
                                    >
                                      {a.title}
                                    </span>
                                    {canWrite && (
                                      <button
                                        type="button"
                                        className="ws-kb-refbtn"
                                        disabled={busy}
                                        onClick={() => referenceKbArticle(kb, a)}
                                        title="引用到任务文件"
                                      >
                                        {busy ? "…" : "引用"}
                                      </button>
                                    )}
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* 文件预览：点击左侧列表后在这里显示内容 */}
          {activeFile && (
            <div className="ws-sb-section ws-sb-filepreview">
              <div className="ws-sb-head">
                <span className="ws-file-name" title={activeFile.name}>
                  {fmtIcon(activeFile.format)} {activeFile.name}
                </span>
                <button
                  className="btn-ghost ws-sb-filepreview-close"
                  onClick={() => {
                    setActiveFile(null);
                    setActiveContent(null);
                  }}
                  title="关闭预览"
                >
                  ×
                </button>
              </div>
              {activeContent === null ? (
                <Skeleton lines={5} />
              ) : (
                <pre className="ws-file-pre">{activeContent}</pre>
              )}
            </div>
          )}
        </aside>

        <div
          className="ws-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整左侧宽度"
          onMouseDown={(e) => startResize("left", e)}
          onDoubleClick={() => setLeftW(280)}
          title="拖动调整宽度 · 双击恢复默认"
        />

        <main className="ws-main">
          <div className="ws-chat-head">
            <span className="model">
              📦 <ModelSelector value={model} onChange={setModel} compact />
            </span>
            <button
              className="btn-ghost ws-sec-action"
              onClick={exportConversation}
              title="把当前对话（含工具调用）导出为 Markdown 下载"
            >
              💾 导出对话
            </button>
            <button
              className="btn-ghost ws-sec-action"
              onClick={async () => {
                try {
                  const messages: ChatMessage[] = [...history, ...socket.finalized];
                  const text = messages
                    .map((m) => {
                      const role =
                        m.role === "user" ? "👤 用户" : m.role === "assistant" ? "🤖 Agent" : m.role;
                      return `## ${role}\n\n${m.content || ""}`;
                    })
                    .join("\n\n---\n\n");
                  if (navigator.clipboard?.writeText) {
                    await navigator.clipboard.writeText(text);
                  } else {
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    ta.style.position = "fixed";
                    ta.style.opacity = "0";
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                  }
                  pushToast("success", `已复制 ${messages.length} 条对话到剪贴板`);
                } catch (err) {
                  pushToast("error", `复制失败：${(err as Error).message}`);
                }
              }}
              title="把整个对话（用户 + Agent 回复）复制到剪贴板"
            >
              📋 复制对话
            </button>
            <button
              className="btn-ghost ws-sec-action"
              onClick={refreshTaskData}
              title="重新拉取任务详情 / 对话历史 / 文件（保持 WS 连接）"
            >
              🔁 重新加载
            </button>
            {/* 移动端 ⋯ 菜单已搬到 TopNav 右上角，统一一处管所有任务级动作 */}
          </div>
          <AgentUpdateBanner
            task={task}
            isOwnerOrAdmin={role === "owner" || role === "admin"}
            onUpdated={async () => {
              const t = await taskApi.detail(taskId);
              setTask(t);
            }}
          />
          {wsErrCode && (
            <div className="ws-banner">
              <ErrorState
                icon="⚠"
                title="对话异常"
                description={
                  wsErrCode === "LLM_KEY_MISSING"
                    ? "LLM API Key 未配置，请在 .env 填入 ANTHROPIC_API_KEY 后重启后端"
                    : wsErrCode === "WS_DISCONNECTED"
                      ? "WebSocket 已断开，正在尝试重连…"
                      : wsErrCode === "STREAM_INTERRUPTED"
                        ? `回复期间连接中断${
                            wsCloseInfo
                              ? `（close=${wsCloseInfo.code}${
                                  wsCloseInfo.reason ? ` "${wsCloseInfo.reason}"` : ""
                                }）`
                              : ""
                          }；后台任务可能仍在继续。可点「⏹ 终止后台任务」停止，或「🔁 重新加载」拉取最新结果`
                        : wsErrCode === "CONVERSATION_INFLIGHT"
                          ? "上一轮回复仍在后台进行中；点「⏹ 终止后台任务」中断后才能发新消息"
                          : "请稍后重试"
                }
                errorCode={wsErrCode}
                actions={
                  <>
                    {(wsErrCode === "STREAM_INTERRUPTED" ||
                      wsErrCode === "CONVERSATION_INFLIGHT") &&
                      conversationId && (
                        <button
                          className="btn-secondary"
                          onClick={async () => {
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
                          }}
                          title="HTTP 通道终止后台正在跑的 LLM 回合"
                        >
                          ⏹ 终止后台任务
                        </button>
                      )}
                    <button className="btn-secondary" onClick={refreshTaskData}>
                      🔁 重新加载
                    </button>
                    <button className="btn-secondary" onClick={socket.clearError}>
                      我知道了
                    </button>
                  </>
                }
              />
            </div>
          )}
          <MessageList
            finalized={allMessages}
            partial={socket.partial}
            phase={socket.phase}
            onCrystallize={handleCrystallize}
            backgroundInflight={
              !!conversationId &&
              !!convInflightMap[conversationId] &&
              !["streaming", "tool", "typing"].includes(socket.phase)
            }
          />
          {socket.planMode && !socket.pendingPlan && (
            <div className="plan-mode-banner">
              <span>🧭 当前处于 Plan Mode：agent 只能只读调研，调 exit_plan_mode 后等你批准</span>
              <button
                className="plan-mode-banner__exit"
                onClick={() => socket.setPlanMode(false)}
              >
                退出 Plan Mode
              </button>
            </div>
          )}
          {lockedByOther && inflight && (
            <div className="conv-locked-banner conv-locked-banner--other" role="alert">
              <span>
                🔒 用户 <b>{inflight.name}</b> 正在对话中，请新建对话或联系 TA 结束任务
              </span>
              <button
                type="button"
                className="conv-locked-banner__action"
                onClick={handleNewConvFromLock}
                title="为本任务新开一条独立对话，与对方互不干扰"
              >
                ＋ 新建对话
              </button>
            </div>
          )}
          {lockedBySelfElsewhere && (
            <div className="conv-locked-banner conv-locked-banner--self" role="status">
              <span>🔒 你的另一个标签页或设备正在该对话中，等当前回合结束再发新消息</span>
            </div>
          )}
          <ChatInput
            ref={chatInputRef}
            paradigm={task.paradigm}
            disabled={
              !conversationId ||
              Boolean(socket.pendingPlan) ||
              conversationLocked
            }
            isStreaming={isStreaming}
            onSend={handleSend}
            onAbort={socket.abort}
            onVoiceConversation={
              voiceEnabled && conversationId
                ? () => setVoiceConvOpen(true)
                : undefined
            }
            files={files.map((f) => ({ id: f.file_id ?? f.id, name: f.name }))}
            viewerMode={isViewer}
            onRequestEditAccess={requestEditAccess}
            editAccessRequested={editAccessRequested}
          />
          {canWrite && (
            <div className="plan-toggle-row" style={{ display: "flex", gap: 8, padding: "0 16px 12px", alignItems: "center" }}>
              <button
                onClick={() => socket.setPlanMode(!socket.planMode)}
                className={socket.planMode ? "plan-toggle active" : "plan-toggle"}
                style={{
                  padding: "4px 10px",
                  fontSize: 12,
                  borderRadius: 6,
                  border: "1px solid " + (socket.planMode ? "#f59e0b" : "#cbd5e1"),
                  background: socket.planMode ? "#fde68a" : "#ffffff",
                  color: socket.planMode ? "#92400e" : "#475569",
                  cursor: "pointer",
                }}
                disabled={!conversationId}
                title="计划模式：agent 先出方案，你批准后再执行"
              >
                🧭 {socket.planMode ? "Plan Mode ON" : "进入 Plan Mode"}
              </button>
            </div>
          )}
        </main>

        <div
          className="ws-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整右侧宽度"
          onMouseDown={(e) => startResize("right", e)}
          onDoubleClick={() => setRightW(320)}
          title="拖动调整宽度 · 双击恢复默认"
        />

        <aside className="ws-right">
          <div className="ws-right-tabs">
            {(
              [
                { k: "conv", label: "💬 对话" },
                { k: "scheduled", label: "⏱ 定时任务" },
                { k: "skill", label: "🧰 Skill" },
                { k: "agent", label: "🤖 Agent" },
              ] as const
            ).map((t) => (
              <button
                key={t.k}
                className={activeRightTab === t.k ? "active" : ""}
                onClick={() => setActiveRightTab(t.k)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="ws-right-body">
            {activeRightTab === "agent" && (
              <div className="ws-agent-tab">
                {agent ? (
                  <>
                    <div className="ws-agent-head">
                      <span style={{ fontSize: 28 }}>{agent.icon}</span>
                      <div>
                        <div className="ws-agent-name">{agent.name}</div>
                        <div className="ws-agent-paradigm">{agent.paradigm}</div>
                      </div>
                    </div>
                    <p className="ws-agent-desc">{agent.description}</p>
                  </>
                ) : (
                  <div className="ws-empty">未绑定 Agent</div>
                )}

                {/* Agent 目录下的全部文件 */}
                {agent && (
                  <div className="ws-agent-files-section">
                    <div className="ws-skill-head">
                      📂 Agent 文件（<code>agents/{agent.id}/</code>）
                    </div>
                    {agentFiles.length === 0 ? (
                      <div className="ws-empty">暂无文件</div>
                    ) : (
                      <ul className="ws-agent-files">
                        {agentFiles.map((f) => {
                          const isActive = agentFilePreview?.path === f.path;
                          return (
                            <li key={f.path}>
                              <button
                                type="button"
                                className={`ws-agent-file-btn${isActive ? " is-active" : ""}${f.text ? "" : " is-binary"}`}
                                title={f.path + (f.text ? "" : " · 二进制，仅展示")}
                                onClick={async () => {
                                  setAgentFileLoading(true);
                                  try {
                                    const r = await agentApi.readFile(agent.id, f.path);
                                    setAgentFilePreview(r);
                                  } catch (err) {
                                    pushToast("error", (err as Error).message || "读取失败");
                                  } finally {
                                    setAgentFileLoading(false);
                                  }
                                }}
                              >
                                <span className="ws-af-icon">
                                  {f.ext === "json" ? "🔧" : f.ext === "md" ? "📄" : f.ext === "py" ? "🐍" : f.text ? "📝" : "📦"}
                                </span>
                                <span className="ws-af-path">{f.path}</span>
                                <span className="ws-af-size">{f.size} B</span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                    {agentFilePreview && (
                      <div className="ws-agent-file-preview">
                        <div className="ws-agent-file-preview-head">
                          <span>{agentFilePreview.name}</span>
                          <button
                            type="button"
                            className="ws-af-close"
                            onClick={() => setAgentFilePreview(null)}
                            title="关闭"
                          >
                            ×
                          </button>
                        </div>
                        {agentFileLoading ? (
                          <Skeleton lines={4} />
                        ) : agentFilePreview.binary ? (
                          <div className="ws-empty">二进制文件，无法预览</div>
                        ) : (
                          <pre className="ws-af-pre">{agentFilePreview.content}</pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            {activeRightTab === "skill" && (
              <div className="ws-skill-tab">
                <div className="ws-skill-section">
                  <div className="ws-skill-head-row">
                    <span className="ws-skill-head">🧰 本任务 Skills</span>
                    {canWrite && (
                      <button
                        type="button"
                        className="ws-skill-add-btn"
                        disabled={skillBusy}
                        onClick={() => setSkillPickerOpen((v) => !v)}
                        title="添加 / 管理 skill"
                      >
                        {skillPickerOpen ? "收起" : "＋ 添加"}
                      </button>
                    )}
                  </div>
                  {(() => {
                    const ids = task?.skill_ids ?? [];
                    const skillsById = new Map(allSkills.map((s) => [s.id, s]));
                    const updateSkills = async (next: string[]) => {
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
                    };
                    const removeSkill = (sid: string) =>
                      updateSkills(ids.filter((x) => x !== sid));
                    const addSkill = (sid: string) => {
                      if (ids.includes(sid)) return;
                      updateSkills([...ids, sid]);
                    };
                    return (
                      <>
                        {ids.length === 0 ? (
                          <div className="ws-empty">未绑定任何 skill</div>
                        ) : (
                          <ul className="ws-skill-list">
                            {ids.map((sid) => {
                              const s = skillsById.get(sid);
                              const label = s?.name ?? sid;
                              const desc = s?.description_zh || s?.description || "";
                              const cat = s?.category ?? "unknown";
                              return (
                                <li key={sid} className="ws-skill-item" title={desc}>
                                  <div className="ws-skill-row">
                                    <span className={`ws-skill-badge ws-skill-badge-${cat}`}>
                                      {cat === "builtin" ? "内置" : cat === "agentic" ? "agentic" : cat}
                                    </span>
                                    <span className="ws-skill-name">{label}</span>
                                    {canWrite && (
                                      <button
                                        type="button"
                                        className="ws-skill-remove"
                                        disabled={skillBusy}
                                        title="从任务中移除"
                                        onClick={() => removeSkill(sid)}
                                      >
                                        ×
                                      </button>
                                    )}
                                  </div>
                                  {desc && <div className="ws-skill-desc">{shortDesc(desc)}</div>}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                        {skillPickerOpen && canWrite && (
                          <div className="ws-skill-picker">
                            <div className="ws-skill-picker-head">选择要添加的 skill</div>
                            {(() => {
                              const candidates = allSkills.filter(
                                (s) => !ids.includes(s.id),
                              );
                              if (candidates.length === 0) {
                                return <div className="ws-empty">没有更多可添加的 skill</div>;
                              }
                              return (
                                <ul className="ws-skill-list ws-skill-picker-list">
                                  {candidates.map((s) => {
                                    const cat = s.category ?? "unknown";
                                    const desc = s.description_zh || s.description || "";
                                    return (
                                      <li key={s.id} className="ws-skill-item">
                                        <div className="ws-skill-row">
                                          <span className={`ws-skill-badge ws-skill-badge-${cat}`}>
                                            {cat === "builtin" ? "内置" : cat === "agentic" ? "agentic" : cat}
                                          </span>
                                          <span className="ws-skill-name">{s.name}</span>
                                          <button
                                            type="button"
                                            className="ws-skill-add-inline"
                                            disabled={skillBusy}
                                            onClick={() => addSkill(s.id)}
                                          >
                                            ＋
                                          </button>
                                        </div>
                                        {desc && <div className="ws-skill-desc">{shortDesc(desc)}</div>}
                                      </li>
                                    );
                                  })}
                                </ul>
                              );
                            })()}
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
            {activeRightTab === "conv" && (
              <div className="ws-conv-tab">
                <ConversationTab
                  taskId={taskId}
                  currentConvId={conversationId}
                  canWrite={canWrite}
                  reloadKey={convListReloadKey}
                  onItemsLoaded={(items) => {
                    const map: Record<string, boolean> = {};
                    for (const c of items) {
                      if (c.inflight) map[c.id] = true;
                    }
                    setConvInflightMap(map);
                  }}
                  onSelect={async (cid) => {
                    if (cid === conversationId) return;
                    // 先立刻清空旧历史，避免 fetch 返回前这一帧把旧对话的消息
                    // 拼进新对话（useChatSocket 内部会同步重置自己的 finalized）。
                    setHistory([]);
                    setConversationId(cid);
                    try {
                      const data = await conversationApi.get(taskId, cid);
                      setHistory(data.messages);
                    } catch (err: any) {
                      pushToast(
                        "error",
                        "加载对话历史失败：" + (err?.response?.data?.message ?? String(err)),
                      );
                    }
                  }}
                />
              </div>
            )}
            {activeRightTab === "scheduled" && (
              <div className="ws-scheduled-tab" style={{ padding: "12px 14px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 10,
                  }}
                >
                  <span style={{ fontSize: 12, color: "var(--text-dim)", flex: 1 }}>
                    本任务的定时执行（{scheduledItems.length}）
                  </span>
                  <button
                    className="btn-ghost"
                    style={{ fontSize: 11, padding: "2px 8px" }}
                    onClick={() =>
                      navigate(`/scheduled-tasks?task_id=${encodeURIComponent(taskId)}`)
                    }
                    title="去定时任务全页管理"
                  >
                    管理 →
                  </button>
                </div>
                {scheduledItems.length === 0 ? (
                  <div className="ws-empty">
                    本任务暂无定时。点「管理 →」新建。
                  </div>
                ) : (
                  <ul
                    style={{
                      listStyle: "none",
                      padding: 0,
                      margin: 0,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    {scheduledItems.map((s) => (
                      <li
                        key={s.id}
                        style={{
                          background: "var(--surface-2)",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "8px 10px",
                          fontSize: 12,
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            marginBottom: 4,
                          }}
                        >
                          <span
                            style={{
                              fontSize: 10,
                              padding: "1px 6px",
                              borderRadius: 3,
                              background: s.enabled
                                ? "var(--success-dim)"
                                : "var(--surface-3)",
                              color: s.enabled
                                ? "var(--success)"
                                : "var(--text-muted)",
                            }}
                          >
                            {s.enabled ? "启用" : "停用"}
                          </span>
                          <span style={{ fontWeight: 500, flex: 1 }}>{s.name}</span>
                          <button
                            className="btn-ghost"
                            style={{ fontSize: 10, padding: "2px 6px" }}
                            disabled={!canWrite}
                            onClick={async () => {
                              try {
                                const r = await scheduledApi.runNow(s.task_id, s.id);
                                pushToast(
                                  r.status === "failed" ? "error" : "success",
                                  r.status === "failed"
                                    ? `执行失败：${r.error?.message || "未知"}`
                                    : "已立即执行",
                                );
                                await reloadScheduled();
                              } catch (err) {
                                pushToast("error", (err as Error).message);
                              }
                            }}
                            title="立即执行一次"
                          >
                            ▶ 立即执行
                          </button>
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 11,
                            color: "var(--text-muted)",
                          }}
                        >
                          {s.cron}
                        </div>
                        {s.prompt && (
                          <div
                            style={{
                              fontSize: 11,
                              color: "var(--text-dim)",
                              marginTop: 4,
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                              overflow: "hidden",
                            }}
                          >
                            {s.prompt}
                          </div>
                        )}
                        {s.next_fire_at && (
                          <div
                            style={{
                              fontSize: 10,
                              color: "var(--text-muted)",
                              marginTop: 4,
                            }}
                          >
                            下次：{new Date(s.next_fire_at).toLocaleString()}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </aside>
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
      {/* 移动端面板切换：文件 / 对话 / 详情。原本在 TopNav 下方，
          现挪到 .ws 最末，让用户单手就能切换；同时本页不再渲染全局
          MobileBottomBar（任务/定时/指南/管理）—— 在 agent 对话场景下
          那 4 个全局入口属于干扰，且会遮挡 ChatInput 的发送按钮。 */}
      <div className="ws-mobile-segs" role="tablist" aria-label="工作区面板">
        <button
          role="tab"
          aria-selected={mobileTab === "files"}
          className={mobileTab === "files" ? "active" : ""}
          onClick={() => setMobileTab("files")}
        >
          📂 文件
        </button>
        <button
          role="tab"
          aria-selected={mobileTab === "chat"}
          className={mobileTab === "chat" ? "active" : ""}
          onClick={() => setMobileTab("chat")}
        >
          💬 对话
        </button>
        <button
          role="tab"
          aria-selected={mobileTab === "right"}
          className={mobileTab === "right" ? "active" : ""}
          onClick={() => setMobileTab("right")}
        >
          🤖 详情
        </button>
      </div>
    </div>
  );
}

function ShareToggle({
  taskId,
  visibility,
  publishStatus,
  onChanged,
}: {
  taskId: string;
  visibility: string;
  publishStatus?: string;
  onChanged: () => void | Promise<void>;
}) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [busy, setBusy] = useState(false);
  const isPublic = visibility === "public";
  const isPending = publishStatus === "pending";
  const isRejected = publishStatus === "rejected";
  const click = async () => {
    setBusy(true);
    try {
      if (isPublic) {
        await shareApi.unshare(taskId);
        pushToast("success", "已撤回到私有");
      } else {
        const r = await shareApi.share(taskId);
        pushToast(
          r.publish_status === "pending" ? "info" : "success",
          r.publish_status === "pending" ? "已提交审核，admin 通过后才会展示" : "已发布到公共区",
        );
      }
      await onChanged();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      className="btn-ghost"
      onClick={click}
      disabled={busy}
      title={isPending ? "审核中" : isRejected ? "审核未通过，可重新开放给团队" : isPublic ? "撤回到私有" : "任务开放给团队"}
    >
      {isPending ? "🕓 审核中" : isRejected ? "🚫 已驳回" : isPublic ? "🔗 已开放给团队" : "🔗 任务开放给团队"}
    </button>
  );
}

type FileCategory = "sql" | "data" | "other";

const FILE_CATEGORY_DEFS: { key: FileCategory; label: string; icon: string }[] = [
  { key: "sql", label: "SQL", icon: "🗃" },
  { key: "data", label: "数据", icon: "📊" },
  { key: "other", label: "其他文档", icon: "📄" },
];

const DATA_FORMATS = new Set(["csv", "tsv", "json", "parquet", "xlsx", "xls"]);

function categorizeFile(f: FileMeta): FileCategory {
  const fmt = (f.format || "").toLowerCase();
  if (fmt === "sql") return "sql";
  if (DATA_FORMATS.has(fmt)) return "data";
  return "other";
}

function fmtIcon(fmt?: string | null): string {
  switch ((fmt || "").toLowerCase()) {
    case "md":
    case "txt":
      return "📝";
    case "csv":
    case "tsv":
      return "📊";
    case "json":
      return "🧾";
    case "py":
      return "🐍";
    case "sql":
      return "🗃";
    case "png":
    case "jpg":
    case "jpeg":
      return "🖼";
    default:
      return "📄";
  }
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Skill 描述右栏展示只保留极短的 10 汉字概述。英文单词按约 2 字符=1 汉字折算；
 * 完整描述通过父级 li 的 title 属性在悬停时仍可看到。
 */
function shortDesc(s: string): string {
  const clean = s
    .replace(/\r?\n/g, " ")
    .replace(/[*_`]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  // 粗略：中文字符数 + 英文长度/2
  let weight = 0;
  let out = "";
  for (const ch of clean) {
    const isCJK = /[一-鿿]/.test(ch);
    const w = isCJK ? 1 : 0.5;
    if (weight + w > 10) {
      out += "…";
      break;
    }
    weight += w;
    out += ch;
  }
  return out;
}
