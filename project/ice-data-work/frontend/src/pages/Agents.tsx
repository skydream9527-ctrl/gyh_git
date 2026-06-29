import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet } from "@/api/client";

interface Agent {
  id: string;
  name: string;
  description?: string;
  type?: string;
  skills?: string[];
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiGet<Agent[]>("/agents").then(setAgents).catch(() => {});
  }, []);

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="eyebrow">Agent Hub</div>
          <h1>工具 Agent</h1>
          <p className="subtle">平台内置与团队共享的 Agent。点卡片查看能力、记忆分区与技能。</p>
        </div>
      </div>

      <div className="agent-grid">
        {agents.map((a) => (
          <div key={a.id} className="card agent-hub-card" onClick={() => navigate(`/agents/${a.id}`)} role="button" tabIndex={0}
               onKeyDown={(e) => { if (e.key === "Enter") navigate(`/agents/${a.id}`); }}>
            <div className="agent-hub-head">
              <span className="ava agent">{a.id.slice(0, 2).toUpperCase()}</span>
              <div>
                <strong>{a.name}</strong>
                <span className="task-meta">{a.type === "builtin" ? "内置" : a.type || "Agent"}</span>
              </div>
            </div>
            <p className="subtle">{a.description}</p>
            {a.skills && a.skills.length > 0 && (
              <div className="skill-tags">
                {a.skills.map((s) => <span key={s} className="pill slate">{s}</span>)}
              </div>
            )}
          </div>
        ))}
        {agents.length === 0 && <div className="lane-empty">暂无 Agent</div>}
      </div>
    </div>
  );
}
