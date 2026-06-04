import type { ScheduledTask } from "@/api/endpoints";
import type { AgentCard, TaskDetail } from "@/types/api";
import type { InflightUser, PlanProposal, RunEvent, StreamPhase, TodoItem } from "@/hooks/useChatSocket";
import "./ExecutionCockpit.css";

interface Props {
  task: TaskDetail;
  agent: AgentCard | null;
  phase: StreamPhase;
  status: "idle" | "connecting" | "open" | "closed";
  runEvents: RunEvent[];
  todos: TodoItem[];
  todosUpdatedAt: string | null;
  planMode: boolean;
  pendingPlan: PlanProposal | null;
  inflightUser: InflightUser | null;
  currentUserId?: string | null;
  scheduledItems: ScheduledTask[];
  canWrite: boolean;
  onTogglePlanMode: () => void;
  onApprovePlan: (planId: string) => void;
  onRejectPlan: (planId: string) => void;
  onOpenScheduled: () => void;
}

type CockpitStatus = "idle" | "running" | "waiting" | "done" | "warning" | "error" | "offline";

export function ExecutionCockpit({
  task,
  agent,
  phase,
  status,
  runEvents,
  todos,
  todosUpdatedAt,
  planMode,
  pendingPlan,
  inflightUser,
  currentUserId,
  scheduledItems,
  canWrite,
  onTogglePlanMode,
  onApprovePlan,
  onRejectPlan,
  onOpenScheduled,
}: Props) {
  const latest = runEvents[runEvents.length - 1] ?? null;
  const cockpitStatus = getCockpitStatus({
    phase,
    status,
    latest,
    pendingPlan,
    inflightUser,
  });
  const statusCopy = statusMeta[cockpitStatus];
  const progress = deriveProgress(todos, latest, cockpitStatus);
  const visibleEvents = runEvents.slice(-8).reverse();
  const activeTodos = todos.length > 0 ? todos : deriveTodosFromEvents(runEvents);

  return (
    <div className="exec-cockpit">
      <section className={`exec-hero exec-hero--${cockpitStatus}`}>
        <div className="exec-hero__top">
          <div>
            <div className="exec-eyebrow">Run Cockpit</div>
            <h3>{statusCopy.title}</h3>
          </div>
          <span className={`exec-status-pill exec-status-pill--${cockpitStatus}`}>
            <span className="exec-status-dot" />
            {statusCopy.label}
          </span>
        </div>
        <p>{statusCopy.description}</p>
        <div className="exec-meter" aria-label={`执行进度 ${progress}%`}>
          <div style={{ width: `${progress}%` }} />
        </div>
        <div className="exec-hero__meta">
          <span>{agent ? `${agent.icon} ${agent.name}` : "未绑定 Agent"}</span>
          <span>{task.paradigm}</span>
          <span>{status === "open" ? "WS online" : status}</span>
        </div>
      </section>

      {pendingPlan && (
        <section className="exec-card exec-plan-card">
          <div className="exec-card__head">
            <span>等待方案确认</span>
            <span className="exec-card__tag">HITL</span>
          </div>
          <div className="exec-plan-text">{pendingPlan.plan_text}</div>
          <div className="exec-actions">
            <button
              type="button"
              className="exec-btn exec-btn--secondary"
              onClick={() => onRejectPlan(pendingPlan.plan_id)}
            >
              拒绝
            </button>
            <button
              type="button"
              className="exec-btn exec-btn--primary"
              onClick={() => onApprovePlan(pendingPlan.plan_id)}
            >
              批准并执行
            </button>
          </div>
        </section>
      )}

      <section className="exec-card">
        <div className="exec-card__head">
          <span>执行计划</span>
          {todosUpdatedAt && <time>{formatRelative(todosUpdatedAt)}</time>}
        </div>
        {activeTodos.length === 0 ? (
          <div className="exec-empty">
            Agent 开始多步任务后，这里会显示执行树、当前节点和完成状态。
          </div>
        ) : (
          <ol className="exec-tree">
            {activeTodos.map((item, index) => (
              <li key={item.id || `${item.content}-${index}`} className={`exec-node exec-node--${item.status}`}>
                <span className="exec-node__rail" />
                <span className="exec-node__mark">{nodeIcon(item.status)}</span>
                <div className="exec-node__body">
                  <div className="exec-node__title">
                    {item.status === "in_progress" ? item.activeForm || item.content : item.content}
                  </div>
                  <div className="exec-node__meta">{statusLabel(item.status)}</div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="exec-card">
        <div className="exec-card__head">
          <span>事件流</span>
          <span>{runEvents.length}</span>
        </div>
        {visibleEvents.length === 0 ? (
          <div className="exec-empty">暂无运行事件。发送消息后会实时记录上下文、工具调用和完成状态。</div>
        ) : (
          <div className="exec-events">
            {visibleEvents.map((event, index) => (
              <div key={`${event.run_id}-${event.created_at}-${index}`} className={`exec-event exec-event--${event.status}`}>
                <span className="exec-event__dot" />
                <div className="exec-event__body">
                  <div className="exec-event__label">{event.label}</div>
                  <div className="exec-event__meta">
                    <span>{event.stage}</span>
                    <span>{formatTime(event.created_at)}</span>
                  </div>
                  {event.detail && <div className="exec-event__detail">{event.detail}</div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="exec-card">
        <div className="exec-card__head">
          <span>控制</span>
          {inflightUser && (
            <span className="exec-card__tag">
              {inflightUser.id === currentUserId ? "本账号运行中" : `${inflightUser.name} 运行中`}
            </span>
          )}
        </div>
        <div className="exec-control-grid">
          <button
            type="button"
            className={`exec-control ${planMode ? "is-active" : ""}`}
            onClick={onTogglePlanMode}
            disabled={!canWrite}
          >
            <span>Plan Mode</span>
            <b>{planMode ? "ON" : "OFF"}</b>
          </button>
          <button
            type="button"
            className="exec-control"
            onClick={onOpenScheduled}
          >
            <span>定时任务</span>
            <b>{scheduledItems.length}</b>
          </button>
        </div>
      </section>
    </div>
  );
}

function getCockpitStatus({
  phase,
  status,
  latest,
  pendingPlan,
  inflightUser,
}: {
  phase: StreamPhase;
  status: "idle" | "connecting" | "open" | "closed";
  latest: RunEvent | null;
  pendingPlan: PlanProposal | null;
  inflightUser: InflightUser | null;
}): CockpitStatus {
  if (pendingPlan || latest?.status === "waiting") return "waiting";
  if (latest?.status === "error" || phase === "error") return "error";
  if (latest?.status === "warning") return "warning";
  if (latest?.status === "done") return "done";
  if (["typing", "streaming", "tool"].includes(phase) || inflightUser || latest?.status === "running") return "running";
  if (status === "closed" || status === "connecting") return "offline";
  return "idle";
}

const statusMeta: Record<CockpitStatus, { label: string; title: string; description: string }> = {
  idle: {
    label: "Idle",
    title: "待命中",
    description: "当前没有运行中的回合。发起指令后，这里会成为任务执行的总控面板。",
  },
  running: {
    label: "Running",
    title: "任务正在执行",
    description: "Agent 正在处理当前回合，可在下方跟踪事件、工具调用与计划节点。",
  },
  waiting: {
    label: "Paused",
    title: "等待人工确认",
    description: "执行流已挂起，需要你批准方案或补充判断后才能继续。",
  },
  done: {
    label: "Done",
    title: "本轮已完成",
    description: "当前回合已结束。你可以继续追问、导出结果，或将任务转为定时运行。",
  },
  warning: {
    label: "Warning",
    title: "执行有警告",
    description: "任务已继续推进，但有部分步骤出现回退或非阻塞异常。",
  },
  error: {
    label: "Error",
    title: "执行异常",
    description: "本轮执行遇到错误。查看事件流细节后，可重试工具调用或重新加载任务。",
  },
  offline: {
    label: "Syncing",
    title: "连接同步中",
    description: "正在建立或恢复实时连接。后台任务可能仍在继续运行。",
  },
};

function deriveProgress(todos: TodoItem[], latest: RunEvent | null, status: CockpitStatus): number {
  if (todos.length > 0) {
    const done = todos.filter((todo) => todo.status === "completed").length;
    const active = todos.some((todo) => todo.status === "in_progress") ? 0.5 : 0;
    return Math.min(100, Math.round(((done + active) / todos.length) * 100));
  }
  if (status === "done") return 100;
  if (status === "waiting") return 58;
  if (status === "running") return 38;
  if (latest) return 18;
  return 0;
}

function deriveTodosFromEvents(events: RunEvent[]): TodoItem[] {
  return events.slice(-5).map((event, index) => ({
    id: `${event.run_id}-${event.stage}-${index}`,
    content: event.label,
    activeForm: event.detail || event.label,
    status:
      event.status === "done"
        ? "completed"
        : event.status === "running"
          ? "in_progress"
          : "pending",
  }));
}

function nodeIcon(status: TodoItem["status"]): string {
  if (status === "completed") return "✓";
  if (status === "in_progress") return "•";
  return "";
}

function statusLabel(status: TodoItem["status"]): string {
  if (status === "completed") return "Completed";
  if (status === "in_progress") return "In progress";
  return "Pending";
}

function formatRelative(iso: string): string {
  const ts = new Date(iso).getTime();
  if (!Number.isFinite(ts)) return "";
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚更新";
  if (min < 60) return `${min} 分钟前`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour} 小时前`;
  return new Date(iso).toLocaleDateString();
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
