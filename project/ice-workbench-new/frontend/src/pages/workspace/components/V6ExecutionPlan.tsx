/**
 * Execution plan panel — shows agent TodoList progress or a static workflow preview.
 * Extracted from WorkspacePage.tsx for maintainability.
 */

interface TodoItem {
  id: string;
  content: string;
  activeForm?: string;
  status: "pending" | "in_progress" | "completed";
}

interface Props {
  todos: TodoItem[];
  runEvents: Array<{ status: "running" | "done" | "error" | "warning" | "waiting" | "aborted" }>;
  phase: string;
  pendingPlan: boolean;
  inflightName: string | null;
  scheduledCount: number;
  agentName: string;
}

export function findWaitingTodo(
  todos: Array<{ content: string; activeForm?: string; status: "pending" | "in_progress" | "completed" }>,
) {
  return todos.find((todo) => {
    if (todo.status !== "in_progress") return false;
    const text = `${todo.activeForm || ""} ${todo.content || ""}`;
    return /等待|确认|审批|人工|补充|输入|选择|配置/.test(text);
  }) ?? null;
}

export function V6ExecutionPlan({
  todos,
  runEvents,
  phase,
  pendingPlan,
  inflightName,
  scheduledCount,
  agentName,
}: Props) {
  const active = ["typing", "streaming", "tool"].includes(phase);
  const latestEvent = runEvents[runEvents.length - 1] ?? null;
  const waitingTodo = findWaitingTodo(todos);
  const panelStatus =
    pendingPlan || latestEvent?.status === "waiting" || waitingTodo
      ? "waiting"
      : latestEvent?.status === "error" || phase === "error" || latestEvent?.status === "aborted"
        ? "error"
        : latestEvent?.status === "warning"
          ? "warning"
          : active || latestEvent?.status === "running"
            ? "running"
            : latestEvent?.status === "done"
              ? "done"
              : "idle";
  const summaryBadgeClass =
    panelStatus === "waiting" || panelStatus === "warning"
      ? "v6-badge v6-badge-warning"
      : panelStatus === "error"
        ? "v6-badge v6-badge-error"
        : panelStatus === "done"
          ? "v6-badge v6-badge-success"
          : panelStatus === "running"
            ? "v6-badge v6-badge-running"
            : "v6-badge";
  const summaryLabel =
    panelStatus === "waiting"
      ? "等待确认"
      : panelStatus === "warning"
        ? "有警告"
        : panelStatus === "error"
          ? "执行异常"
          : panelStatus === "done"
            ? "本轮完成"
            : panelStatus === "running"
              ? "执行中"
              : "就绪";

  type NodeStatus = "completed" | "running" | "waiting" | "error" | "pending";
  const fallbackNodes: Array<{ id: string; title: string; meta: string; status: NodeStatus }> = [
    { id: "intent", title: "理解意图与拆解计划", meta: agentName, status: active || pendingPlan ? "completed" : "pending" },
    { id: "execute", title: "数据提取与工具调用", meta: inflightName ? `${inflightName} 占用中` : active ? "执行中" : "等待指令", status: active ? "running" : "pending" },
    { id: "report", title: "归因分析与报告生成", meta: "报告节点 · 等待中", status: "pending" },
    { id: "deliver", title: "结果交付与定时化", meta: scheduledCount > 0 ? `${scheduledCount} 个 Cron 已绑定` : "可转为 Cron", status: scheduledCount > 0 ? "completed" : "pending" },
  ];
  const nodes =
    todos.length > 0
      ? todos.map((t) => ({
          id: t.id,
          title: t.status === "in_progress" ? t.activeForm || t.content : t.content,
          meta:
            t.status === "completed"
              ? "已完成"
              : t.status === "in_progress"
                ? findWaitingTodo([t])
                  ? "等待用户确认"
                  : `${agentName} · 执行中`
                : "等待中",
          status:
            t.status === "completed"
              ? "completed"
              : t.status === "in_progress"
                ? findWaitingTodo([t])
                  ? "waiting"
                  : "running"
                : "pending",
        }))
      : fallbackNodes;

  return (
    <div className="v6-exec-panel">
      <div className="v6-exec-summary">
        <span className={summaryBadgeClass}>{summaryLabel}</span>
        <small>{todos.length > 0 ? "来自 Agent Todo" : "工作流预览"}</small>
      </div>
      <div className="v6-exec-tree">
        <div className="v6-exec-line" />
        {nodes.map((n) => (
          <div key={n.id} className="v6-exec-node">
            <div className={`v6-exec-dot ${n.status}`}>
              {n.status === "completed" ? "✓" : n.status === "running" || n.status === "waiting" ? <span className="v6-pulse" /> : n.status === "error" ? "!" : null}
            </div>
            <div className="v6-exec-content">
              <div className="v6-exec-title">{n.title}</div>
              <div className={`v6-exec-meta ${n.status}`}>{n.meta}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
