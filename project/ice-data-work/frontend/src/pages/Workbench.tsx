import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTaskStore, STATUS_LABELS, STATUS_PILL, type TaskStatus } from "@/stores/taskStore";
import { useSpaceStore } from "@/stores/spaceStore";
import { useAuthStore } from "@/stores/authStore";

// Workbench：最外层主页。聚合运行中任务、待确认、最近任务、在工作的 Agent。
export default function Workbench() {
  const { tasks, fetchTasks } = useTaskStore();
  const { currentProject } = useSpaceStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (currentProject) fetchTasks(currentProject.id);
    else fetchTasks();
  }, [currentProject, fetchTasks]);

  const running = tasks.filter((t) => t.status === "doing");
  const awaiting = tasks.filter((t) => t.status === "await");
  const recent = tasks.slice(0, 5);

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="eyebrow">Main Workbench</div>
          <h1>你的团队 AI 工作台</h1>
          <p className="subtle">看见正在运行的任务、待确认的事和下一步。</p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/new-mission")}>新建 Mission</button>
      </div>

      <div className="hero">
        <span className="pill blue">User → Wisdom Twin → Agents</span>
        <h2>
          当前项目 {currentProject?.name || "个人项目"}
        </h2>
        <div className="stat-line">
          <div className="stat"><b>{running.length}</b><span>运行中任务</span></div>
          <div className="stat"><b>{awaiting.length}</b><span>待我确认</span></div>
          <div className="stat"><b>{tasks.filter((t) => t.status === "done").length}</b><span>已完成</span></div>
          <div className="stat"><b>{user?.platform_role === "super_admin" ? "L4" : "L2"}</b><span>Twin 权限</span></div>
        </div>
      </div>

      <div className="wb-grid">
        <div className="card">
          <div className="card-head">
            <h3>运行中的任务</h3>
            <span className="pill blue">Current</span>
          </div>
          <div className="wb-list">
            {running.length === 0 && <div className="lane-empty">暂无运行中任务</div>}
            {running.map((t) => (
              <div className="wb-item" key={t.id}>
                <div className="wb-item-main">
                  <strong>{t.title}</strong>
                  <span className="task-meta">
                    {t.participant_count} 位参与者 · {t.type === "data" ? "数据分析" : "通用"}
                  </span>
                </div>
                <button className="btn-sm primary" onClick={() => navigate(`/task/${t.id}`)}>进入</button>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>待确认</h3>
            <span className="pill amber">Pending</span>
          </div>
          <div className="wb-list">
            {awaiting.length === 0 && <div className="lane-empty">没有待确认事项</div>}
            {awaiting.map((t) => (
              <div className="wb-item" key={t.id}>
                <div className="wb-item-main">
                  <strong>{t.title}</strong>
                  <span className="task-meta">等待你确认</span>
                </div>
                <button className="btn-sm" onClick={() => navigate(`/task/${t.id}`)}>查看</button>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>最近任务</h3>
            <span className="pill green">Recent</span>
          </div>
          <div className="wb-list">
            {recent.length === 0 && <div className="lane-empty">还没有任务，点右上角新建</div>}
            {recent.map((t) => (
              <div className="wb-item compact" key={t.id}>
                <div className="wb-item-main">
                  <strong>{t.title}</strong>
                  <span className={`pill ${STATUS_PILL[t.status as TaskStatus]}`}>
                    {STATUS_LABELS[t.status as TaskStatus]}
                  </span>
                </div>
                <button className="btn-sm" onClick={() => navigate(`/task/${t.id}`)}>打开</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
