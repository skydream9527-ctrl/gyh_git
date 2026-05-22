import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentApi, fileApi, kbApi, skillApi, taskApi } from "@/api/endpoints";
import type { KBArticle, KBSummary } from "@/api/endpoints";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { TopNav } from "@/components/shell/TopNav";
import { MobileBottomBar } from "@/components/shell/MobileBottomBar";
import { EmptyState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/Skeleton";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import type { AgentCard, FileMeta, SkillCard, TaskSummary } from "@/types/api";
import "./Dashboard.css";

type PublicTab = "tasks" | "agents" | "skills" | "files" | "kb";

const AGENT_ORDER = [
  // 已上线
  "general",
  "data-analysis",
  "ab-experiment",
  "know",
  "gray-release",
  "volcano-abtest",
  // 待上线
  "biz-insight",
  "wave-attribution",
];

function sortAgents(list: AgentCard[]): AgentCard[] {
  return [...list].sort((a, b) => {
    // 已上线在前、待上线在后；同组内按 AGENT_ORDER 排序，未登记的排末尾
    const sa = a.publish_status === "coming_soon" ? 1 : 0;
    const sb = b.publish_status === "coming_soon" ? 1 : 0;
    if (sa !== sb) return sa - sb;
    const ia = AGENT_ORDER.indexOf(a.id);
    const ib = AGENT_ORDER.indexOf(b.id);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

export function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const pushToast = useUIStore((s) => s.pushToast);
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [skills, setSkills] = useState<SkillCard[]>([]);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [publicTasks, setPublicTasks] = useState<TaskSummary[]>([]);
  const [publicFiles, setPublicFiles] = useState<FileMeta[]>([]);
  const [kbs, setKbs] = useState<KBSummary[]>([]);
  const [browseKB, setBrowseKB] = useState<KBSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [publicTab, setPublicTab] = useState<PublicTab>("tasks");
  const [confirmDelete, setConfirmDelete] = useState<TaskSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    Promise.all([
      agentApi.list().then((r) => setAgents(sortAgents(r.items))).catch(() => {}),
      skillApi.list().then((r) => setSkills(r.items)).catch(() => {}),
      taskApi.list().then((r) => setTasks(r.items)).catch(() => {}),
      taskApi.listPublic().then((r) => setPublicTasks(r.items)).catch(() => {}),
      fileApi.listPublic().then((r) => setPublicFiles(r.items)).catch(() => {}),
      kbApi.list().then((r) => setKbs(r.items)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  // 快速开始一键新建任务：
  //  - 点已上线 agent → 打开"起名弹窗"，默认"{agent 名} · MM/DD HH:mm"，用户可改
  //  - 点待上线 agent → toast 提示
  const [starting, setStarting] = useState<string | null>(null);
  const [namePrompt, setNamePrompt] = useState<{ agent: AgentCard; name: string } | null>(null);
  const defaultTaskName = (agent: AgentCard) => {
    const now = new Date();
    const ts = `${now.getMonth() + 1}/${now.getDate()} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    return `${agent.name} · ${ts}`;
  };
  const startWith = (agent: AgentCard) => {
    if (agent.publish_status === "coming_soon") {
      pushToast("info", `${agent.name} 待上线，敬请期待`);
      return;
    }
    setNamePrompt({ agent, name: defaultTaskName(agent) });
  };
  const confirmCreateTask = async () => {
    if (!namePrompt) return;
    const { agent } = namePrompt;
    const name = namePrompt.name.trim();
    if (!name) {
      pushToast("warning", "请输入任务名");
      return;
    }
    if (starting) return;
    setStarting(agent.id);
    try {
      const task = await taskApi.create({
        name,
        paradigm: agent.paradigm,
        agent_id: agent.id,
        visibility: "private",
      });
      setNamePrompt(null);
      navigate(`/workspace/${task.id}`);
    } catch (err) {
      pushToast("error", (err as Error).message || "创建任务失败");
      setStarting(null);
    }
  };

  const openPublicFile = (f: FileMeta) => {
    window.open(`/public-files/${f.id}`, "_blank", "noopener,noreferrer");
  };

  const deleteTask = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      await taskApi.remove(confirmDelete.id);
      setTasks((arr) => arr.filter((x) => x.id !== confirmDelete.id));
      pushToast("success", `已删除 "${confirmDelete.name}"`);
      setConfirmDelete(null);
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  // 公共区 Skills 只展示 skills/ 目录下的真实 SKILL.md（即 category === "agentic"），
  // 内置工具（now/echo/write_file 等）不属于用户视角的 Skill，不暴露在公共区。
  const agenticSkills = skills.filter((s) => s.category === "agentic");

  return (
    <div className="dash">
      <TopNav
        mode="dashboard"
        rightActions={
          <>
            <button className="btn-primary dash-top-extra" onClick={() => navigate("/create-task")}>
              + 新任务
            </button>
            <button className="btn-ghost dash-top-extra" onClick={() => navigate("/scheduled-tasks")}>
              ⏱ 定时
            </button>
            <button className="btn-ghost dash-top-extra" onClick={() => navigate("/guide")}>
              📖 指南
            </button>
            {(user?.auth_role === "admin" || user?.auth_role === "super_admin") && (
              <button className="btn-ghost dash-top-extra" onClick={() => navigate("/admin")}>
                🛡 管理
              </button>
            )}
          </>
        }
      />
      <main className="dash-main has-bottombar">
        <div className="dash-welcome">
          <h1>👋 你好，{user?.name || "同学"}</h1>
          <p>选一个范式开始今天的工作</p>
        </div>

        <section className="dash-section dash-start">
          <div className="start-grid">
            <button
              className="start-card start-blank"
              onClick={() => navigate("/create-task")}
            >
              <div className="sc-icon">📝</div>
              <div className="sc-body">
                <div className="sc-name">新建任务</div>
                <div className="sc-desc">选择范式 / Agent，开启一个新任务</div>
              </div>
            </button>
            <button
              className="start-card start-open"
              onClick={() => navigate("/scheduled-tasks")}
            >
              <div className="sc-icon">⏱</div>
              <div className="sc-body">
                <div className="sc-name">定时任务</div>
                <div className="sc-desc">按周期自动执行的任务列表</div>
              </div>
            </button>
            <button
              className="start-card start-template"
              onClick={() => navigate("/guide")}
            >
              <div className="sc-icon">📖</div>
              <div className="sc-body">
                <div className="sc-name">使用指南</div>
                <div className="sc-desc">上手教程与功能说明</div>
              </div>
            </button>
            <button
              className="start-card start-public"
              onClick={() => {
                setPublicTab("tasks");
                document
                  .getElementById("dash-public-area")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
            >
              <div className="sc-icon">🌐</div>
              <div className="sc-body">
                <div className="sc-name">公共任务</div>
                <div className="sc-desc">参考团队已有任务</div>
              </div>
            </button>
          </div>
        </section>

        <section className="dash-section">
          <h2>⚡ 快速开始</h2>
          {loading ? (
            <div className="paradigm-grid">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="paradigm-card">
                  <Skeleton lines={3} />
                </div>
              ))}
            </div>
          ) : (
            (() => {
              const renderCard = (a: AgentCard) => {
                const comingSoon = a.publish_status === "coming_soon";
                const isStarting = starting === a.id;
                return (
                  <button
                    key={a.id}
                    type="button"
                    className={`paradigm-card${comingSoon ? " paradigm-card-soon" : ""}${isStarting ? " paradigm-card-starting" : ""}`}
                    onClick={() => startWith(a)}
                    aria-busy={isStarting || undefined}
                    style={{ borderTopColor: a.color }}
                    title={comingSoon ? "待上线，敬请期待" : `一键以 ${a.name} 创建任务`}
                  >
                    {comingSoon && <span className="pc-badge-soon">待上线</span>}
                    <div className="pc-icon" style={{ background: `${a.color}22`, color: a.color }}>
                      {a.icon}
                    </div>
                    <div className="pc-name">
                      {a.name}
                      {isStarting && <span className="pc-starting"> 创建中…</span>}
                    </div>
                    <div className="pc-desc">{a.description}</div>
                  </button>
                );
              };
              const published = agents.filter((a) => a.publish_status !== "coming_soon");
              const upcoming = agents.filter((a) => a.publish_status === "coming_soon");
              return (
                <>
                  {published.length > 0 && (
                    <div className="paradigm-grid">{published.map(renderCard)}</div>
                  )}
                  {upcoming.length > 0 && (
                    <div className="paradigm-grid paradigm-grid-upcoming">
                      {upcoming.map(renderCard)}
                    </div>
                  )}
                </>
              );
            })()
          )}
        </section>

        <section className="dash-section">
          <h2>📋 我的任务</h2>
          {loading ? (
            <Skeleton lines={4} />
          ) : tasks.length === 0 ? (
            <EmptyState
              illustration="📋"
              title="还没有任务"
              hint="选择上方一个范式开始你的第一个任务"
            />
          ) : (
            <div className="task-grid">
              {tasks.map((t) => (
                <div
                  key={t.id}
                  className={`task-card ${paradigmClass(t.paradigm)}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/workspace/${t.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      navigate(`/workspace/${t.id}`);
                    }
                  }}
                >
                  {t.role !== "collaborator" && (
                    <button
                      className="tc-delete"
                      title="删除任务"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDelete(t);
                      }}
                    >
                      🗑
                    </button>
                  )}
                  <div className="tc-name">{t.name}</div>
                  <div className="tc-meta">
                    <span className="tc-paradigm">{t.paradigm}</span>
                    {t.role === "collaborator" && <span className="tc-collab">👥 协作</span>}
                  </div>
                  {t.last_message_preview && (
                    <div className="tc-preview">💬 “{t.last_message_preview}”</div>
                  )}
                  <div className="tc-foot">
                    ⏱ {formatTime(t.updated_at)} · 📄 {t.file_count}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="dash-section" id="dash-public-area">
          <h2>🌐 团队公共区</h2>
          <div className="public-tabs">
            {(
              [
                { k: "tasks", label: "📋 公共任务", count: publicTasks.length },
                { k: "agents", label: "🤖 Agents", count: agents.length },
                { k: "skills", label: "🧰 Skills", count: agenticSkills.length },
                { k: "files", label: "📁 公共文件", count: publicFiles.length },
                { k: "kb", label: "📚 知识库", count: kbs.length },
              ] as const
            ).map((t) => (
              <button
                key={t.k}
                className={`public-tab ${publicTab === t.k ? "active" : ""}`}
                onClick={() => setPublicTab(t.k)}
              >
                {t.label}
                <span className="public-tab-count">{t.count}</span>
              </button>
            ))}
          </div>

          {publicTab === "tasks" && (
            <div className="public-grid">
              {publicTasks.length === 0 ? (
                <EmptyState
                  illustration="🌐"
                  title="公共区暂无任务"
                  hint="同事在 Workspace 顶栏点 🔗「任务开放给团队」并通过审核后出现在这里"
                />
              ) : (
                publicTasks.map((t) => (
                  <button
                    key={t.id}
                    className="public-task-card"
                    onClick={() => navigate(`/workspace/${t.id}`)}
                  >
                    <div className="ptc-name">{t.name}</div>
                    <div className="ptc-meta">
                      {t.paradigm} · {t.last_message_preview ? "💬 已展开" : "📭 空"}
                    </div>
                    {t.owner_name && (
                      <div className="ptc-owner" title={`所有者：${t.owner_name}`}>
                        👤 {t.owner_name}
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>
          )}

          {publicTab === "agents" && (
            <div className="public-grid">
              {agents.length === 0 ? (
                <EmptyState illustration="🤖" title="暂无可用 Agent" />
              ) : (
                agents.map((a) => (
                  <button
                    key={a.id}
                    className="public-task-card"
                    onClick={() => navigate(`/agent/${a.id}`)}
                    style={{ borderLeft: `3px solid ${a.color}` }}
                  >
                    <div className="ptc-name">
                      {a.icon} {a.name}
                    </div>
                    <div className="ptc-meta">
                      {a.paradigm} · {a.description?.slice(0, 32) || ""}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}

          {publicTab === "skills" && (
            <div className="public-grid">
              {agenticSkills.length === 0 ? (
                <EmptyState
                  illustration="🧰"
                  title="暂无 Skill"
                  hint="把 SKILL.md 放到仓库根目录的 skills/ 下即可在此展示"
                />
              ) : (
                agenticSkills.map((s) => {
                  const brief = skillBrief(s.description);
                  return (
                    <div
                      key={s.id}
                      className="public-task-card"
                      title={brief.full}
                    >
                      <div className="ptc-name">🧰 {brief.title || s.name}</div>
                      <div className="ptc-meta">{brief.summary || "—"}</div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {publicTab === "files" && (
            <div className="public-grid">
              {publicFiles.length === 0 ? (
                <EmptyState
                  illustration="📁"
                  title="公共文件为空"
                  hint="admin 在 /admin/files 上传后这里可见"
                />
              ) : (
                publicFiles.map((f) => {
                  const kindLabel =
                    f.builtin_kind === "guide"
                      ? "📘 指南"
                      : f.builtin_kind === "agent"
                        ? "🤖 Agent"
                        : f.builtin_kind === "skill"
                          ? "🧰 Skill"
                          : null;
                  return (
                    <button
                      key={f.id}
                      className={`public-task-card${f.builtin ? " public-task-card-builtin" : ""}`}
                      onClick={() => openPublicFile(f)}
                      title={f.builtin ? "平台内置 · 只读" : undefined}
                    >
                      {f.builtin && (
                        <span className="ptc-builtin-badge">🔒 内置</span>
                      )}
                      <div className="ptc-name">
                        {!f.builtin && f.is_pinned && "📌 "}
                        {f.name}
                      </div>
                      <div className="ptc-meta">
                        {kindLabel ? `${kindLabel} · ` : ""}
                        {f.format} · {fmtSize(f.size_bytes || f.size || 0)}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          )}

          {publicTab === "kb" && (
            <div className="public-grid">
              {kbs.length === 0 ? (
                <EmptyState
                  illustration="📚"
                  title="暂无知识库"
                  hint="管理员在 /admin/knowledge-bases 配置并同步后会显示在这里"
                />
              ) : (
                kbs.map((kb) => (
                  <button
                    key={kb.id}
                    className="public-task-card"
                    onClick={() => setBrowseKB(kb)}
                    title="点击浏览文档"
                  >
                    <div className="ptc-name">
                      {kb.source_type === "feishu_wiki" ? "🪶" : "📚"} {kb.name}
                    </div>
                    <div className="ptc-meta">
                      {kb.source_type === "feishu_wiki" ? "飞书 Wiki" : "Mify RAG"} ·{" "}
                      {kb.doc_count} 篇
                      {kb.last_sync_at ? ` · 同步于 ${formatTime(kb.last_sync_at)}` : " · 未同步"}
                    </div>
                    {kb.description && (
                      <div
                        className="ptc-meta"
                        style={{
                          marginTop: 4,
                          color: "var(--text-dim)",
                          fontSize: 11,
                          lineHeight: 1.4,
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {kb.description}
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </section>
      </main>

      {namePrompt && (
        <div
          className="cm-overlay"
          onClick={() => !starting && setNamePrompt(null)}
        >
          <div
            className="cm-card dash-name-prompt"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>
              <span style={{ marginRight: 8 }}>{namePrompt.agent.icon}</span>
              以「{namePrompt.agent.name}」新建任务
            </h3>
            <div className="cm-body">
              <label className="dnp-field">
                <span>任务名</span>
                <input
                  autoFocus
                  value={namePrompt.name}
                  placeholder="给这个任务起个名字"
                  onChange={(e) =>
                    setNamePrompt((p) => (p ? { ...p, name: e.target.value } : null))
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter") confirmCreateTask();
                    if (e.key === "Escape" && !starting) setNamePrompt(null);
                  }}
                />
              </label>
              <div className="dnp-hint">
                {namePrompt.agent.description}
              </div>
            </div>
            <div className="cm-actions">
              <button
                className="btn-secondary"
                onClick={() => setNamePrompt(null)}
                disabled={!!starting}
              >
                取消
              </button>
              <button
                className="btn-primary"
                onClick={confirmCreateTask}
                disabled={!!starting || !namePrompt.name.trim()}
              >
                {starting ? "创建中…" : "创建并进入"}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!confirmDelete}
        title="删除任务？"
        body={
          <>
            确定删除 <b>{confirmDelete?.name}</b>？
            <br />
            该任务的所有对话、文件、经验卡片都会一并删除，无法恢复。
          </>
        }
        confirmText={deleting ? "删除中…" : "删除"}
        danger
        onConfirm={deleteTask}
        onCancel={() => setConfirmDelete(null)}
      />

      {browseKB && (
        <BrowseKBModal kb={browseKB} onClose={() => setBrowseKB(null)} />
      )}

      <button
        type="button"
        className="m-fab"
        aria-label="新建任务"
        onClick={() => navigate("/create-task")}
      >
        {/* SVG 而非字符 + ：中文字体里 + / ＋ 字形 baseline 偏移会让图标
            视觉上偏离圆心；SVG 是几何居中，配合 .m-fab 的 place-items:center
            就稳了。 */}
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
      <MobileBottomBar />
    </div>
  );
}

function BrowseKBModal({ kb, onClose }: { kb: KBSummary; onClose: () => void }) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [articles, setArticles] = useState<KBArticle[] | null>(null);
  const [selected, setSelected] = useState<KBArticle | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    kbApi
      .articles(kb.id)
      .then((r) => setArticles(r.items))
      .catch((e) => {
        pushToast("error", (e as Error).message);
        setArticles([]);
      });
  }, [kb.id, pushToast]);

  const openArticle = async (a: KBArticle) => {
    setSelected(a);
    if (a.content) return;
    setDetailLoading(true);
    try {
      const full = await kbApi.article(kb.id, a.id);
      setSelected(full);
      setArticles((prev) => prev?.map((x) => (x.id === full.id ? full : x)) || prev);
    } catch (e) {
      pushToast("error", (e as Error).message);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="cm-overlay" onClick={onClose}>
      <div
        className="cm-card"
        style={{
          width: "min(1100px, 92vw)",
          height: "min(720px, 85vh)",
          display: "flex",
          flexDirection: "column",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>
          {kb.source_type === "feishu_wiki" ? "🪶" : "📚"} {kb.name}
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 400, marginLeft: 10 }}>
            {articles ? `${articles.length} 篇` : "加载中…"}
          </span>
        </h3>
        <div
          className="cm-body"
          style={{
            display: "grid",
            gridTemplateColumns: "260px 1fr",
            gap: 12,
            flex: 1,
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          <div style={{ overflowY: "auto", borderRight: "1px solid var(--border)", paddingRight: 8 }}>
            {articles === null ? (
              <Skeleton lines={6} />
            ) : articles.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 20, fontSize: 12 }}>
                暂无文档
              </div>
            ) : (
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 2 }}>
                {articles.map((a) => (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => openArticle(a)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "8px 10px",
                        borderRadius: 6,
                        border: "1px solid transparent",
                        background: selected?.id === a.id ? "var(--primary-dim)" : "transparent",
                        color: "var(--text)",
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ fontWeight: 500 }}>{a.title}</div>
                      {a.meta && typeof a.meta === "object" && (a.meta as any).obj_type && (
                        <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
                          {(a.meta as any).obj_type}
                          {(a.meta as any).has_child ? " · 含子节点" : ""}
                        </div>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div style={{ overflowY: "auto", padding: "0 4px" }}>
            {!selected ? (
              <div style={{ color: "var(--text-muted)", padding: 20, fontSize: 12 }}>
                选择左侧一篇文档查看正文。想在任务中引用这篇文档，请到工作空间左侧 📚 知识库面板点「引用」。
              </div>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <h4 style={{ margin: 0, flex: 1 }}>{selected.title}</h4>
                  {selected.url && (
                    <a href={selected.url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
                      在飞书打开 ↗
                    </a>
                  )}
                </div>
                {detailLoading ? (
                  <Skeleton lines={8} />
                ) : selected.content ? (
                  <div
                    style={{
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "12px 16px",
                      fontSize: 13,
                      lineHeight: 1.65,
                    }}
                  >
                    <MarkdownRenderer content={selected.content} />
                  </div>
                ) : (
                  <div style={{ color: "var(--text-muted)", padding: 12, fontSize: 12 }}>
                    (暂无正文)
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        <div className="cm-actions">
          <button className="btn-primary" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function paradigmClass(p: string): string {
  return `tc-${p}`;
}

/**
 * 从 Skill 的 markdown 描述里提取紧凑展示用的三件套：
 * - title：第一个 #/## 标题（如 `# 文章配图生成`）
 * - summary：第一个非标题段落，去掉粗体/代码/引号标记，限制长度
 * - full：整段纯文本（用于悬停 title 提示）
 */
function skillBrief(desc?: string | null): { title: string; summary: string; full: string } {
  const text = (desc || "").trim();
  if (!text) return { title: "", summary: "", full: "" };
  const lines = text.split("\n").map((l) => l.trim());
  let title = "";
  let summary = "";
  for (const l of lines) {
    if (!l) continue;
    if (!title && l.startsWith("#")) {
      title = l.replace(/^#+\s*/, "").trim();
      continue;
    }
    if (!summary) {
      const stripped = l
        .replace(/^[-*]\s+/, "")
        .replace(/\*\*([^*]+)\*\*/g, "$1")
        .replace(/`([^`]+)`/g, "$1")
        .trim();
      if (stripped) {
        summary = stripped.length > 90 ? stripped.slice(0, 90).trim() + "…" : stripped;
        break;
      }
    }
  }
  return { title, summary, full: text.slice(0, 400) };
}

function formatTime(iso?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  return d.toLocaleDateString();
}
