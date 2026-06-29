import { useEffect, useState } from "react";
import { useSpaceStore } from "@/stores/spaceStore";

export default function Project() {
  const { currentTeam, projects, currentProject, selectProject, fetchProjects } = useSpaceStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (currentTeam && projects.length === 0) {
      setLoading(true);
      fetchProjects(currentTeam.id).finally(() => setLoading(false));
    }
  }, [currentTeam, projects.length, fetchProjects]);

  if (!currentTeam) {
    return <div className="page"><p className="subtle">请先选择团队</p></div>;
  }

  return (
    <div className="page">
      <div className="eyebrow">项目管理</div>
      <h1>{currentTeam.name} · 项目</h1>
      <p className="subtle">团队下所有项目</p>

      {loading && <p>加载中…</p>}

      <div className="project-list">
        {projects.map((p) => (
          <div
            key={p.id}
            className={`card project-card ${currentProject?.id === p.id ? "active" : ""}`}
            onClick={() => selectProject(p)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter") selectProject(p); }}
          >
            <div className="row">
              <b>{p.name}</b>
              <span className="pill ok">{p.type}</span>
            </div>
            <div className="mono">ID: {p.id}</div>
          </div>
        ))}
        {!loading && projects.length === 0 && (
          <p className="subtle">暂无项目</p>
        )}
      </div>
    </div>
  );
}
