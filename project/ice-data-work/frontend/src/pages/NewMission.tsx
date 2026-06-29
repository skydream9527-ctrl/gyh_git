import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTaskStore } from "@/stores/taskStore";
import { useSpaceStore } from "@/stores/spaceStore";
import { apiPost } from "@/api/client";

export default function NewMission() {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<"data" | "general">("data");
  const [inviteTwin, setInviteTwin] = useState(true);
  const [inviteAgent, setInviteAgent] = useState("data-analysis");
  const [submitting, setSubmitting] = useState(false);

  const { createTask } = useTaskStore();
  const { currentProject } = useSpaceStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      const task = await createTask({
        title: title.trim(),
        project_id: currentProject?.id,
        type,
      });
      // 邀请参与者
      if (inviteTwin) {
        await apiPost(`/tasks/${task.id}/participants`, {
          ref_type: "twin", ref_id: "twin-admin", role: "collaborator",
        }).catch(() => {});
      }
      if (inviteAgent) {
        await apiPost(`/tasks/${task.id}/participants`, {
          ref_type: "agent", ref_id: inviteAgent, role: "tool",
        }).catch(() => {});
      }
      navigate(`/task/${task.id}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <div className="eyebrow">New Mission</div>
      <h1>新建任务</h1>
      <p className="subtle">
        创建任务并邀请参与者。任务将归属当前项目
        {currentProject ? `：${currentProject.name}` : "（个人项目）"}。
      </p>

      <form onSubmit={handleSubmit} className="mission-form">
        <label>
          任务标题
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：浏览器 6.20 DAU 下滑归因"
            autoFocus
            required
          />
        </label>

        <label>
          任务类型
          <select value={type} onChange={(e) => setType(e.target.value as "data" | "general")}>
            <option value="data">数据分析</option>
            <option value="general">通用</option>
          </select>
        </label>

        <div className="invite-section">
          <span className="sidebar-label">邀请参与者</span>
          <label className="checkbox-row">
            <input type="checkbox" checked={inviteTwin} onChange={(e) => setInviteTwin(e.target.checked)} />
            我的 Twin（编排协调）
          </label>
          <label>
            工具 Agent
            <select value={inviteAgent} onChange={(e) => setInviteAgent(e.target.value)}>
              <option value="">不邀请</option>
              <option value="data-analysis">数据分析 Agent</option>
              <option value="report-writer">报告撰写 Agent</option>
              <option value="code-runner">代码执行 Agent</option>
            </select>
          </label>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "创建中…" : "创建并进入"}
          </button>
          <button type="button" className="link-btn" onClick={() => navigate("/board")}>取消</button>
        </div>
      </form>
    </div>
  );
}
