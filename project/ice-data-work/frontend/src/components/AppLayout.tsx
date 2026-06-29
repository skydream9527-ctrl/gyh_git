import { useEffect } from "react";
import { Outlet, useNavigate, NavLink } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useSpaceStore } from "@/stores/spaceStore";
import TwinDock from "@/components/TwinDock";

export default function AppLayout() {
  const { user, token, fetchMe, logout } = useAuthStore();
  const { teams, currentTeam, fetchTeams, selectTeam, fetchProjects } = useSpaceStore();
  const navigate = useNavigate();

  const isAdmin = user?.platform_role === "admin" || user?.platform_role === "super_admin";

  useEffect(() => {
    if (token && !user) {
      fetchMe();
    }
    if (!token) {
      navigate("/login");
    }
  }, [token, user, fetchMe, navigate]);

  useEffect(() => {
    if (token) {
      fetchTeams();
    }
  }, [token, fetchTeams]);

  useEffect(() => {
    if (currentTeam) {
      fetchProjects(currentTeam.id);
    }
  }, [currentTeam, fetchProjects]);

  if (!token) return null;

  return (
    <div className="app-layout">
      <nav className="app-sidebar">
        <div className="sidebar-header">
          <span className="brand">ICE-DATA-WORK</span>
        </div>

        {/* Team 切换器 */}
        <div className="sidebar-section">
          <label className="sidebar-label">团队</label>
          <select
            className="space-select"
            value={currentTeam?.id || ""}
            onChange={(e) => {
              const t = teams.find((x) => x.id === e.target.value);
              if (t) selectTeam(t);
            }}
          >
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {/* 导航 */}
        <div className="sidebar-nav">
          <span className="nav-group">工作</span>
          <NavLink to="/workbench" className="nav-item">工作台</NavLink>
          <NavLink to="/board" className="nav-item">任务看板</NavLink>
          <NavLink to="/agents" className="nav-item">Agent Hub</NavLink>
          <NavLink to="/knowledge" className="nav-item">知识与产物</NavLink>

          <span className="nav-group">治理</span>
          <NavLink to="/approvals" className="nav-item">审批与审计</NavLink>
          {isAdmin && <NavLink to="/admin" className="nav-item">管理后台</NavLink>}

          <span className="nav-group">空间</span>
          <NavLink to="/team" className="nav-item">团队</NavLink>
          <NavLink to="/project" className="nav-item">项目</NavLink>
          <NavLink to="/twin" className="nav-item">Twin</NavLink>
        </div>

        {/* 用户信息 */}
        <div className="sidebar-footer">
          {user && (
            <div className="user-info">
              <span className="user-name">{user.name}</span>
              <span className="user-role">{user.platform_role}</span>
            </div>
          )}
          <button className="link-btn" onClick={() => { logout(); navigate("/login"); }}>
            退出
          </button>
        </div>
      </nav>

      <main className="app-main">
        <Outlet />
      </main>

      <TwinDock />
    </div>
  );
}
