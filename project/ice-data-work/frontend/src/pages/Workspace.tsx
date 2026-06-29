import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiGet, apiPut } from "@/api/client";
import Chat from "@/components/Chat";
import MemoryPanel from "@/components/MemoryPanel";
import SkillPanel from "@/components/SkillPanel";
import { useTaskSocket, type ChatTurn } from "@/hooks/useTaskSocket";
import { STATUS_LABELS, STATUS_PILL, type Task, type TaskStatus } from "@/stores/taskStore";

interface Artifact {
  id: string;
  title: string;
  kind: string;
  status: string;
}

type Drawer = "none" | "artifacts" | "memory" | "skills";

function partAvatar(p: { ref_type: string; ref_id: string }): string {
  if (p.ref_type === "user") return "我";
  if (p.ref_type === "twin") return "TW";
  return p.ref_id.slice(0, 2).toUpperCase();
}

export default function Workspace() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [initialTurns, setInitialTurns] = useState<ChatTurn[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [drawer, setDrawer] = useState<Drawer>("none");

  useEffect(() => {
    if (!taskId) return;
    Promise.all([
      apiGet<Task>(`/tasks/${taskId}`),
      apiGet<ChatTurn[]>(`/tasks/${taskId}/conversation`).catch(() => []),
      apiGet<Artifact[]>(`/tasks/${taskId}/artifacts`).catch(() => []),
    ]).then(([t, convo, arts]) => {
      setTask(t);
      setArtifacts(arts);
      setInitialTurns(
        (convo as ChatTurn[]).map((turn) => ({
          id: turn.id,
          speaker: turn.speaker,
          content: turn.content,
        }))
      );
      setLoaded(true);
    });
  }, [taskId]);

  const { turns, connected, thinking, send } = useTaskSocket(loaded ? taskId! : "", initialTurns);

  const changeStatus = async (status: TaskStatus) => {
    if (!taskId) return;
    await apiPut(`/tasks/${taskId}/status`, { status, reason: "" });
    setTask((prev) => (prev ? { ...prev, status } : prev));
  };

  const toggleDrawer = (d: Drawer) => setDrawer((cur) => (cur === d ? "none" : d));

  if (!task) return <div className="page"><p>加载工作台中…</p></div>;

  const participants = task.participants || [];

  return (
    <div className="workspace">
      {/* 顶部任务条 */}
      <div className="ws-header">
        <div className="ws-header-left">
          <button className="link-btn" onClick={() => navigate("/board")}>← 看板</button>
          <h2>{task.title}</h2>
          <span className={`pill ${STATUS_PILL[task.status]}`}>{STATUS_LABELS[task.status]}</span>
        </div>
        <div className="ws-header-right">
          <div className="participant-chips">
            {participants.map((p) => (
              <span key={`${p.ref_type}:${p.ref_id}`} className={`chip ${p.ref_type}`} title={`${p.role}`}>
                <span className={`ava ${p.ref_type}`}>{partAvatar(p)}</span>
                {p.ref_type === "twin" ? "Twin" : p.ref_id}
              </span>
            ))}
          </div>
          <button className={`btn-sm ${drawer === "memory" ? "primary" : ""}`} onClick={() => toggleDrawer("memory")}>
            记忆/确认
          </button>
          <button className={`btn-sm ${drawer === "skills" ? "primary" : ""}`} onClick={() => toggleDrawer("skills")}>
            技能
          </button>
          <button className={`btn-sm ${drawer === "artifacts" ? "primary" : ""}`} onClick={() => toggleDrawer("artifacts")}>
            产物 ▸ {artifacts.length}
          </button>
        </div>
      </div>

      {/* 状态操作行 */}
      <div className="ws-status-bar">
        {task.status === "await" && (
          <>
            <span className="subtle">该任务等待你确认下一步：</span>
            <button className="btn-sm primary" onClick={() => changeStatus("doing")}>批准继续</button>
            <button className="btn-sm" onClick={() => changeStatus("done")}>标记完成</button>
          </>
        )}
        {task.status === "doing" && (
          <>
            <button className="btn-sm" onClick={() => changeStatus("paused")}>一键暂停</button>
            <button className="btn-sm" onClick={() => changeStatus("done")}>标记完成</button>
          </>
        )}
        {task.status === "paused" && (
          <button className="btn-sm primary" onClick={() => changeStatus("doing")}>恢复执行</button>
        )}
        {task.status === "done" && (
          <button className="btn-sm" onClick={() => changeStatus("doing")}>重新打开</button>
        )}
      </div>

      <div className="ws-body">
        {/* 主对话区 */}
        <div className="ws-chat">
          <Chat turns={turns} thinking={thinking} connected={connected} onSend={send} />
        </div>

        {/* 记忆/确认抽屉 */}
        {drawer === "memory" && (
          <MemoryPanel taskId={taskId!} participants={participants} onClose={() => setDrawer("none")} />
        )}

        {/* 技能候选抽屉（D-13 贡献为 Skill）*/}
        {drawer === "skills" && (
          <SkillPanel taskId={taskId!} participants={participants} onClose={() => setDrawer("none")} />
        )}

        {/* 产物抽屉 */}
        {drawer === "artifacts" && (
          <div className="ws-drawer">
            <div className="drawer-head">
              <h3>产出物</h3>
              <button className="link-btn" onClick={() => setDrawer("none")}>关闭</button>
            </div>
            {artifacts.length === 0 && <div className="lane-empty">还没有产物</div>}
            {artifacts.map((a) => (
              <div key={a.id} className="artifact-row">
                <div>
                  <strong>{a.title}</strong>
                  <span className="task-meta">{a.kind}</span>
                </div>
                <span className={`pill ${a.status === "published" ? "green" : "amber"}`}>
                  {a.status === "published" ? "已发布" : "草稿"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
