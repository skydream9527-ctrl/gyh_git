import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { TopNav } from "@/components/shell/TopNav";
import { AppSideNav } from "@/components/shell/AppSideNav";
import { MobileBottomBar } from "@/components/shell/MobileBottomBar";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { EmptyState } from "@/components/feedback/ErrorState";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useBackdropClose } from "@/hooks/useBackdropClose";
import { clickIgnoreSelection } from "@/utils/click";
import { ModelSelector } from "@/components/chat/ModelSelector";
import { scheduledApi, taskApi } from "@/api/endpoints";
import type { ScheduledRun, ScheduledRunDetail, ScheduledTask } from "@/api/endpoints";
import type { TaskSummary } from "@/types/api";
import { useUIStore } from "@/stores/uiStore";
import "./Scheduled.css";

export function ScheduledTasksPage() {
  const [params] = useSearchParams();
  const filterTaskId = params.get("taskId") || params.get("task_id");
  const openCreateOnLoad = params.get("create") === "1";
  const detailScheduleId = params.get("scheduleId") || "";
  const detailRunId = params.get("runId") || "";
  const navigate = useNavigate();
  const pushToast = useUIStore((s) => s.pushToast);

  const [items, setItems] = useState<ScheduledTask[]>([]);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEnabled, setFilterEnabled] = useState<"all" | "on" | "off">("all");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ScheduledTask | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ScheduledTask | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Record<string, ScheduledRun[]>>({});
  const [detailItem, setDetailItem] = useState<ScheduledTask | null>(null);
  const [detailRuns, setDetailRuns] = useState<ScheduledRun[]>([]);
  const [detail, setDetail] = useState<ScheduledRunDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [summary, setSummary] = useState<{
    enabled: number;
    paused: number;
    today_runs: number;
    failed_7d: number;
  } | null>(null);

  const reload = async () => {
    setLoading(true);
    try {
      const r = await scheduledApi.listMine();
      setItems(r.items.filter((s) => !filterTaskId || s.task_id === filterTaskId));
      scheduledApi.summary().then(setSummary).catch(() => setSummary(null));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    taskApi.list().then((r) => setTasks(r.items)).catch(() => {});
    if (filterTaskId && openCreateOnLoad) setShowCreate(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterTaskId, openCreateOnLoad]);

  useEffect(() => {
    if (!detailScheduleId) {
      setDetailItem(null);
      setDetailRuns([]);
      setDetail(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      const source = items.find((s) => s.id === detailScheduleId);
      if (!source) return;
      setDetailItem(source);
      setDetailLoading(true);
      try {
        const runsResp = await scheduledApi.listRuns(source.task_id, source.id);
        if (cancelled) return;
        setDetailRuns(runsResp.items);
        const targetRun = detailRunId
          ? runsResp.items.find((r) => r.id === detailRunId)
          : runsResp.items[0];
        if (targetRun) {
          const d = await scheduledApi.getRunDetail(source.task_id, source.id, targetRun.id);
          if (!cancelled) setDetail(d);
        } else if (!cancelled) {
          setDetail(null);
        }
      } catch (err) {
        if (!cancelled) pushToast("error", (err as Error).message);
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    };
    void load();
    const t = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [detailScheduleId, detailRunId, items, pushToast]);

  const filtered = useMemo(
    () =>
      items.filter((s) => {
        if (filterEnabled === "on" && !s.enabled) return false;
        if (filterEnabled === "off" && s.enabled) return false;
        if (search && !`${s.name}${s.task_name || ""}${s.cron}`.includes(search)) return false;
        return true;
      }),
    [items, filterEnabled, search],
  );
  const enabledCount = items.filter((s) => s.enabled).length;
  const pausedCount = items.length - enabledCount;
  const firedToday = items.filter((s) => isToday(s.last_fire_at)).length;

  const toggle = async (s: ScheduledTask) => {
    try {
      await scheduledApi.update(s.task_id, s.id, { enabled: !s.enabled });
      pushToast("success", s.enabled ? "已暂停" : "已恢复");
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const runNow = async (s: ScheduledTask) => {
    try {
      pushToast("info", `正在执行 ${s.name}…`);
      const run = await scheduledApi.runNow(s.task_id, s.id);
      navigate(`/scheduled-tasks?taskId=${encodeURIComponent(s.task_id)}&scheduleId=${encodeURIComponent(s.id)}&runId=${encodeURIComponent(run.id)}`);
      pushToast(
        run.status === "running" ? "info" : run.status === "success" ? "success" : "warning",
        run.status === "running" ? "已开始执行，正在进入详情页" : `执行结束：${run.status}`,
      );
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const expand = async (s: ScheduledTask) => {
    if (expandedRuns[s.id]) {
      const next = { ...expandedRuns };
      delete next[s.id];
      setExpandedRuns(next);
      return;
    }
    try {
      const r = await scheduledApi.listRuns(s.task_id, s.id);
      setExpandedRuns({ ...expandedRuns, [s.id]: r.items });
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const openDetail = async (s: ScheduledTask, runId?: string) => {
    navigate(`/scheduled-tasks?taskId=${encodeURIComponent(s.task_id)}&scheduleId=${encodeURIComponent(s.id)}${runId ? `&runId=${encodeURIComponent(runId)}` : ""}`);
  };

  const remove = async (s: ScheduledTask) => {
    try {
      await scheduledApi.remove(s.task_id, s.id);
      pushToast("success", "已删除");
      setConfirmDelete(null);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  return (
    <div className="sc-page">
      <TopNav mode="workspace" crumb={<span>首页 / <span className="current">定时任务</span></span>} />
      <div className="app-shell">
        <AppSideNav active="scheduled" />
        <main className="sc-main app-shell-main has-bottombar">
        <header className="sc-head sc-v6-head">
          <div>
            <div className="sc-v6-kicker">Cron · Agent-driven</div>
            <h1>定时调度 Tasks</h1>
            <p>每个手动跑通的 Workspace 都可以绑定 cron，转成后台持续执行的工作流。</p>
          </div>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + 创建定时任务
          </button>
        </header>

        <section className="sc-v6-stats" aria-label="定时任务统计">
          <div className="sc-v6-stat">
            <span>运行中任务</span>
            <b>{summary && !filterTaskId ? summary.enabled : enabledCount}</b>
          </div>
          <div className="sc-v6-stat muted">
            <span>已暂停</span>
            <b>{summary && !filterTaskId ? summary.paused : pausedCount}</b>
          </div>
          <div className="sc-v6-stat">
            <span>今日已执行</span>
            <b>{summary && !filterTaskId ? summary.today_runs : firedToday}</b>
          </div>
          <div className="sc-v6-stat danger">
            <span>近7天失败</span>
            <b>{summary && !filterTaskId ? summary.failed_7d : "—"}</b>
          </div>
        </section>

        <div className="sc-filter">
          <div className="sc-chips">
            {(["all", "on", "off"] as const).map((k) => (
              <button
                key={k}
                className={`sc-chip ${filterEnabled === k ? "on" : ""}`}
                onClick={() => setFilterEnabled(k)}
              >
                {k === "all" ? "全部" : k === "on" ? "运行中" : "已暂停"}
              </button>
            ))}
          </div>
          <input
            className="sc-search"
            placeholder="🔍 搜索任务名 / cron"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {loading ? (
          <Skeleton lines={6} />
        ) : filtered.length === 0 ? (
          <EmptyState
            illustration="⏱"
            title="还没有定时任务"
            hint="从已有任务创建一个 cron 触发器，自动跑数 + 推送结果"
            cta={
              <button className="btn-primary" onClick={() => setShowCreate(true)}>
                创建第一个定时任务
              </button>
            }
          />
        ) : (
          <div className="sc-list sc-v6-table">
            <div className="sc-v6-table-head">
              <span>定时任务 / 绑定工作流</span>
              <span>执行频率</span>
              <span>下次执行时间</span>
              <span>最近执行状态</span>
              <span>启停控制</span>
            </div>
            {filtered.map((s) => (
              <div key={s.id} className="sc-card">
                <div className="sc-card-head">
                  <span className={`sc-status ${s.enabled ? "on" : "off"}`}>
                    {s.enabled ? "运行中" : "已暂停"}
                  </span>
                  <div className="sc-card-name">{s.name}</div>
                  <div className="sc-card-actions">
                    <button onClick={() => runNow(s)}>▶ 立即执行</button>
                    <button onClick={() => openDetail(s)}>查看进度</button>
                    <button onClick={() => toggle(s)}>{s.enabled ? "⏸ 暂停" : "▶ 恢复"}</button>
                    <button onClick={() => setEditing(s)}>✏ 编辑</button>
                    <button onClick={() => setConfirmDelete(s)} className="danger">🗑 删除</button>
                  </div>
                </div>
                <div className="sc-card-body">
                  <div>
                    <span className="sc-label">cron</span>
                    <code>{s.cron}</code>
                    <span className="sc-cron-readable">{readableCron(s.cron)}</span>
                  </div>
                  <div>
                    <span className="sc-label">所属任务</span>
                    <a onClick={clickIgnoreSelection(() => navigate(`/workspace/${s.task_id}`))} style={{ cursor: "pointer" }}>
                      {s.task_name || s.task_id.slice(0, 8)}
                    </a>
                  </div>
                  <div>
                    <span className="sc-label">下次</span>
                    {fmt(s.next_fire_at)}
                  </div>
                  <div>
                    <span className="sc-label">上次</span>
                    {fmt(s.last_fire_at)}
                  </div>
                </div>
                {s.prompt && (
                  <details className="sc-prompt">
                    <summary>📜 Prompt</summary>
                    <pre>{s.prompt}</pre>
                  </details>
                )}
                <div className="sc-runs-toggle">
                  <button onClick={() => expand(s)}>
                    {expandedRuns[s.id] ? "收起" : "查看"}执行历史
                  </button>
                  <button onClick={() => openDetail(s)}>进入详情页</button>
                </div>
                {expandedRuns[s.id] && (
                  <div className="sc-runs">
                    {expandedRuns[s.id].length === 0 && (
                      <div className="sc-empty">暂无执行记录</div>
                    )}
                    {expandedRuns[s.id].map((r) => (
                      <details key={r.id} className={`sc-run sc-run-${r.status}`}>
                        <summary>
                          <span className={`sc-run-badge ${r.status}`}>{r.status}</span>
                          <span>{fmt(r.started_at)}</span>
                          <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>
                            {r.trigger}
                          </span>
                          <button
                            type="button"
                            className="sc-run-detail-btn"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              void openDetail(s, r.id);
                            }}
                          >
                            详情
                          </button>
                        </summary>
                        <div className="sc-run-body">
                          <div>
                            <strong>Prompt</strong>
                            <pre>{r.prompt}</pre>
                          </div>
                          {r.output && (
                            <div>
                              <strong>输出</strong>
                              <pre>{r.output}</pre>
                            </div>
                          )}
                          {r.error && (
                            <div>
                              <strong>错误</strong>
                              <pre>
                                [{r.error.code}] {r.error.message}
                              </pre>
                            </div>
                          )}
                          {r.tokens && (
                            <div>
                              <strong>Tokens</strong>
                              <span>
                                input={r.tokens.input}, output={r.tokens.output}
                              </span>
                            </div>
                          )}
                        </div>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {detailScheduleId && (
          <ScheduleRunDetailPanel
            item={detailItem}
            runs={detailRuns}
            detail={detail}
            loading={detailLoading}
            onClose={() => navigate(filterTaskId ? `/scheduled-tasks?taskId=${encodeURIComponent(filterTaskId)}` : "/scheduled-tasks")}
            onSelectRun={(runId) => {
              if (!detailItem) return;
              navigate(`/scheduled-tasks?taskId=${encodeURIComponent(detailItem.task_id)}&scheduleId=${encodeURIComponent(detailItem.id)}&runId=${encodeURIComponent(runId)}`);
            }}
          />
        )}
        </main>
      </div>

      {(showCreate || editing) && (
        <ScheduleEditModal
          tasks={tasks}
          existing={editing}
          initialTaskId={filterTaskId}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
          onSaved={async () => {
            setShowCreate(false);
            setEditing(null);
            await reload();
          }}
        />
      )}
      <ConfirmModal
        open={!!confirmDelete}
        title={`确认删除“${confirmDelete?.name}”？`}
        body="删除后历史执行记录仍保留在文件系统中。"
        danger
        onConfirm={() => confirmDelete && remove(confirmDelete)}
        onCancel={() => setConfirmDelete(null)}
      />
      <MobileBottomBar />
    </div>
  );
}

function ScheduleRunDetailPanel({
  item,
  runs,
  detail,
  loading,
  onClose,
  onSelectRun,
}: {
  item: ScheduledTask | null;
  runs: ScheduledRun[];
  detail: ScheduledRunDetail | null;
  loading: boolean;
  onClose: () => void;
  onSelectRun: (runId: string) => void;
}) {
  const run = detail?.run;
  const toolEvents = detail?.transcript.filter((e) => e.event === "tool_call") || [];
  const assistantEvents = detail?.transcript.filter((e) => e.event === "assistant") || [];
  return (
    <aside className="sc-detail" aria-label="定时任务执行详情">
      <div className="sc-detail-head">
        <div>
          <span className="sc-detail-kicker">Execution Detail</span>
          <h2>{item?.name || "执行详情"}</h2>
          <p>{item ? `${item.task_name || item.task_id.slice(0, 8)} · ${item.cron}` : "正在加载定时任务"}</p>
        </div>
        <button type="button" onClick={onClose}>关闭</button>
      </div>

      <div className="sc-detail-grid">
        <section>
          <h3>执行记录</h3>
          <div className="sc-detail-runs">
            {runs.length === 0 && <div className="sc-empty">暂无执行记录</div>}
            {runs.map((r) => (
              <button
                key={r.id}
                type="button"
                className={`sc-detail-run ${run?.id === r.id ? "active" : ""}`}
                onClick={() => onSelectRun(r.id)}
              >
                <span className={`sc-run-badge ${r.status}`}>{r.status}</span>
                <span>{fmt(r.started_at)}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="sc-detail-main">
          <h3>进度</h3>
          {loading && <div className="sc-empty">正在刷新执行详情...</div>}
          {!loading && !run && <div className="sc-empty">请选择一条执行记录</div>}
          {run && (
            <>
              <div className="sc-detail-summary">
                <span className={`sc-run-badge ${run.status}`}>{run.status}</span>
                <span>开始：{fmt(run.started_at)}</span>
                <span>结束：{fmt(run.ended_at)}</span>
                {run.rounds != null && <span>轮次：{run.rounds}</span>}
              </div>
              {run.error && (
                <div className="sc-detail-error">
                  <strong>[{run.error.code}]</strong> {run.error.message}
                </div>
              )}
              {toolEvents.length > 0 && (
                <div className="sc-detail-tools">
                  <h4>工具调用</h4>
                  {toolEvents.map((e, i) => (
                    <details key={i} className={`sc-detail-tool ${e.success ? "ok" : "bad"}`}>
                      <summary>
                        <span>{String(e.name || "tool")}</span>
                        <b>{e.success ? "成功" : "失败"}</b>
                      </summary>
                      <pre>{JSON.stringify(e, null, 2)}</pre>
                    </details>
                  ))}
                </div>
              )}
              {assistantEvents.length > 0 && (
                <div className="sc-detail-tools">
                  <h4>Agent 回合</h4>
                  {assistantEvents.slice(-8).map((e, i) => (
                    <details key={i} className="sc-detail-tool">
                      <summary>
                        <span>Round {String(e.round ?? i)}</span>
                        <b>{String(e.stop_reason || "")}</b>
                      </summary>
                      <pre>{JSON.stringify(e, null, 2)}</pre>
                    </details>
                  ))}
                </div>
              )}
              {run.output && (
                <div className="sc-detail-output">
                  <h4>最终输出</h4>
                  <pre>{run.output}</pre>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </aside>
  );
}

function fmt(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString();
}

function isToday(iso: string | null): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}

function readableCron(expr: string): string {
  const p = expr.split(/\s+/);
  if (p.length !== 5) return "";
  const [m, h, dom, mo, dow] = p;
  if (m === "0" && h === "*" && dom === "*" && mo === "*" && dow === "*") return "每小时整点";
  if (m === "0" && /^\d+$/.test(h) && dom === "*" && mo === "*" && dow === "*")
    return `每天 ${h.padStart(2, "0")}:00`;
  if (m === "0" && /^\d+$/.test(h) && dom === "*" && mo === "*" && dow === "1-5")
    return `工作日 ${h.padStart(2, "0")}:00`;
  return "";
}

interface ModalProps {
  tasks: TaskSummary[];
  existing: ScheduledTask | null;
  initialTaskId?: string | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

function ScheduleEditModal({ tasks, existing, initialTaskId, onClose, onSaved }: ModalProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [form, setForm] = useState({
    task_id: existing?.task_id || initialTaskId || tasks[0]?.id || "",
    name: existing?.name || "",
    cron: existing?.cron || "0 9 * * *",
    prompt: existing?.prompt || "",
    enabled: existing?.enabled ?? true,
    model: existing?.model || "ppio/pa/claude-opus-4-7",
    todo_list: (existing?.todo_list as string[] | undefined) || [],
  });
  const [saving, setSaving] = useState(false);
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    if (existing || form.task_id || tasks.length === 0) return;
    setForm((cur) => ({ ...cur, task_id: initialTaskId || tasks[0]?.id || "" }));
  }, [existing, form.task_id, initialTaskId, tasks]);

  const plan = async () => {
    const p = form.prompt.trim();
    if (!p) return pushToast("warning", "请先填写任务提示，再让 AI 规划");
    setPlanning(true);
    try {
      const r = await scheduledApi.plan({ prompt: p, model: form.model });
      setForm((f) => ({ ...f, cron: r.cron, todo_list: r.todo_list }));
      pushToast("success", `已按提示生成 cron 与 todo（${r.todo_list.length} 条）`);
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setPlanning(false);
    }
  };

  const save = async () => {
    if (!form.task_id) return pushToast("warning", "请选择所属任务");
    if (!form.name.trim()) return pushToast("warning", "请填写名称");
    setSaving(true);
    try {
      if (existing) {
        await scheduledApi.update(existing.task_id, existing.id, form);
      } else {
        await scheduledApi.create(form.task_id, form);
      }
      pushToast("success", "已保存");
      await onSaved();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const backdrop = useBackdropClose(onClose);
  return (
    <div className="cm-overlay" {...backdrop}>
      <div className="cm-card sc-modal">
        <h3>{existing ? "编辑定时任务" : "新建定时任务"}</h3>
        <div className="cm-body">
          <div className="sc-form">
            <label className="sc-field">
              <span className="sc-field-label">所属任务</span>
              <select
                value={form.task_id}
                onChange={(e) => setForm({ ...form, task_id: e.target.value })}
                disabled={!!existing}
              >
                {initialTaskId && !tasks.some((t) => t.id === initialTaskId) && (
                  <option value={initialTaskId}>当前任务（{initialTaskId.slice(0, 8)}）</option>
                )}
                {tasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="sc-field">
              <span className="sc-field-label">AI 模型</span>
              <ModelSelector
                value={form.model}
                onChange={(m) => setForm({ ...form, model: m })}
              />
            </label>

            <label className="sc-field">
              <span className="sc-field-label">名称</span>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="例如 每日 DAU 监控"
              />
            </label>

            <label className="sc-field">
              <span className="sc-field-label">任务提示</span>
              <textarea
                rows={4}
                value={form.prompt}
                onChange={(e) => setForm({ ...form, prompt: e.target.value })}
                placeholder="用自然语言描述要做什么 + 节奏。例：每天上午 9 点拉昨日 DAU，与前日对比，异常自动高亮并推送到飞书。"
              />
              <button
                type="button"
                className="btn-secondary sc-plan-btn"
                disabled={planning || !form.prompt.trim()}
                onClick={plan}
              >
                {planning ? "AI 规划中…" : "✨ 根据提示智能生成 cron + todo"}
              </button>
            </label>

            <label className="sc-field">
              <span className="sc-field-label">cron 表达式</span>
              <input
                value={form.cron}
                onChange={(e) => setForm({ ...form, cron: e.target.value })}
                placeholder="分 时 日 月 周，例：0 9 * * *"
              />
              <span className="sc-field-hint">{readableCron(form.cron) || "自定义 cron 或点上方按钮让 AI 建议"}</span>
            </label>

            {form.todo_list.length > 0 && (
              <div className="sc-field sc-todo-field">
                <span className="sc-field-label">执行 Todo List</span>
                <ol className="sc-todo-list">
                  {form.todo_list.map((t, i) => (
                    <li key={i}>
                      <input
                        value={t}
                        onChange={(e) => {
                          const next = [...form.todo_list];
                          next[i] = e.target.value;
                          setForm({ ...form, todo_list: next });
                        }}
                      />
                      <button
                        type="button"
                        className="sc-todo-del"
                        title="删除"
                        onClick={() =>
                          setForm({
                            ...form,
                            todo_list: form.todo_list.filter((_, j) => j !== i),
                          })
                        }
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ol>
                <button
                  type="button"
                  className="sc-todo-add"
                  onClick={() =>
                    setForm({ ...form, todo_list: [...form.todo_list, ""] })
                  }
                >
                  + 新增一条
                </button>
              </div>
            )}

            <label className="sc-toggle">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
              />
              <span>启用（保存后立即按 cron 运行）</span>
            </label>
          </div>
        </div>
        <div className="cm-actions">
          <button className="btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn-primary" disabled={saving} onClick={save}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
