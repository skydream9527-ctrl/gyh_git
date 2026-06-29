import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTaskStore, STATUS_LABELS, STATUS_PILL, type Task, type TaskStatus } from "@/stores/taskStore";
import { useSpaceStore } from "@/stores/spaceStore";

// 看板泳道：待办/执行中/待确认/已完成。报错/已暂停作为执行中的子态展示。
const LANES: { key: TaskStatus; statuses: TaskStatus[] }[] = [
  { key: "todo", statuses: ["todo"] },
  { key: "doing", statuses: ["doing", "error", "paused"] },
  { key: "await", statuses: ["await"] },
  { key: "done", statuses: ["done"] },
];

function avatarFor(p: { ref_type: string; ref_id: string }): string {
  if (p.ref_type === "user") return "我";
  if (p.ref_type === "twin") return "TW";
  return p.ref_id.slice(0, 2).toUpperCase();
}

export default function Board() {
  const { tasks, fetchTasks, setStatus } = useTaskStore();
  const { currentProject, currentTeam } = useSpaceStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (currentProject) {
      fetchTasks(currentProject.id);
    } else {
      fetchTasks();
    }
  }, [currentProject, fetchTasks]);

  const laneTasks = (statuses: TaskStatus[]): Task[] =>
    tasks.filter((t) => statuses.includes(t.status));

  return (
    <div className="board-page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Mission Board</div>
          <h1>任务看板</h1>
          <p className="subtle">Agent 和人一样，是一等的 assignee。按状态分列，点卡片进入 Workspace。</p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/new-mission")}>新建任务</button>
      </div>

      <div className="toolbar">
        <span className="pill slate">
          项目：{currentProject?.name || currentTeam?.name || "全部"}
        </span>
      </div>

      <div className="board">
        {LANES.map((lane) => {
          const items = laneTasks(lane.statuses);
          return (
            <div className="lane" key={lane.key}>
              <div className="lane-head">
                {STATUS_LABELS[lane.key]} <span className="count">{items.length}</span>
              </div>
              {items.map((task) => (
                <div
                  key={task.id}
                  className="task-card"
                  onClick={() => navigate(`/task/${task.id}`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter") navigate(`/task/${task.id}`); }}
                >
                  <div className="task-card-top">
                    <span className={`pill ${STATUS_PILL[task.status]}`}>
                      {STATUS_LABELS[task.status]}
                    </span>
                    <div className="assignees">
                      {(task.participants || [])
                        .filter((p) => p.ref_type !== "user")
                        .slice(0, 3)
                        .map((p) => (
                          <span key={p.ref_id} className={`ava ${p.ref_type}`}>
                            {avatarFor(p)}
                          </span>
                        ))}
                    </div>
                  </div>
                  <strong>{task.title}</strong>
                  <span className="task-meta">
                    {task.type === "data" ? "数据分析" : "通用"}
                    {task.status === "error" && task.error_reason && ` · ${task.error_reason}`}
                    {task.artifact_count ? ` · 产物 ▸ ${task.artifact_count}` : ""}
                  </span>
                  {(task.status === "error" || task.status === "paused") && (
                    <div className="task-actions" onClick={(e) => e.stopPropagation()}>
                      {task.status === "error" && (
                        <button className="btn-sm" onClick={() => setStatus(task.id, "doing")}>重试</button>
                      )}
                      {task.status === "paused" && (
                        <button className="btn-sm" onClick={() => setStatus(task.id, "doing")}>恢复</button>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {items.length === 0 && <div className="lane-empty">暂无任务</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
