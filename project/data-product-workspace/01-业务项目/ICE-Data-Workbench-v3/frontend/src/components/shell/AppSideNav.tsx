import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import "./AppSideNav.css";

export type AppSideKey = "quick" | "mine" | "public" | "scheduled" | "guide" | "admin";

interface Props {
  active: AppSideKey;
  actionRequiredCount?: number;
  onDashboardTab?: (tab: "quick" | "mine" | "public") => void;
}

const COLLAPSE_KEY = "ice-app-sidebar-collapsed";

export function AppSideNav({ active, actionRequiredCount = 0, onDashboardTab }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.auth_role === "admin" || user?.auth_role === "super_admin";
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === "1");

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  const goDash = (tab: "quick" | "mine" | "public") => {
    if (onDashboardTab) {
      onDashboardTab(tab);
      return;
    }
    navigate(`/dashboard?tab=${tab}`);
  };

  return (
    <aside className={`app-sidebar ${collapsed ? "collapsed" : ""}`} aria-label="主导航">
      <button
        type="button"
        className="app-sidebar-toggle"
        onClick={() => setCollapsed((v) => !v)}
        aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        title={collapsed ? "展开侧边栏" : "收起侧边栏"}
      >
        {collapsed ? "»" : "«"}
      </button>

      <div className="app-sidebar-section">
        <div className="app-sidebar-title">导航</div>
        <button type="button" className={`app-sidebar-item ${active === "quick" ? "active" : ""}`} onClick={() => goDash("quick")}>
          <span><span className="app-sidebar-icon">⚡</span><span className="app-sidebar-label">快速开始</span></span>
        </button>
        <button type="button" className={`app-sidebar-item ${active === "mine" ? "active" : ""}`} onClick={() => goDash("mine")}>
          <span><span className="app-sidebar-icon">📋</span><span className="app-sidebar-label">我的任务</span></span>
          {actionRequiredCount > 0 && <span className="app-sidebar-badge">{actionRequiredCount}</span>}
        </button>
        <button type="button" className={`app-sidebar-item ${active === "public" ? "active" : ""}`} onClick={() => goDash("public")}>
          <span><span className="app-sidebar-icon">🌐</span><span className="app-sidebar-label">团队公共区</span></span>
        </button>
      </div>

      <div className="app-sidebar-section">
        <div className="app-sidebar-title">资源</div>
        <button type="button" className={`app-sidebar-item ${active === "scheduled" || location.pathname.startsWith("/scheduled") ? "active" : ""}`} onClick={() => navigate("/scheduled-tasks")}>
          <span><span className="app-sidebar-icon">⏱</span><span className="app-sidebar-label">定时任务</span></span>
        </button>
        <button type="button" className={`app-sidebar-item ${active === "guide" || location.pathname.startsWith("/guide") ? "active" : ""}`} onClick={() => navigate("/guide")}>
          <span><span className="app-sidebar-icon">📖</span><span className="app-sidebar-label">使用指南</span></span>
        </button>
        {isAdmin && (
          <button type="button" className={`app-sidebar-item ${active === "admin" || location.pathname.startsWith("/admin") ? "active" : ""}`} onClick={() => navigate("/admin")}>
            <span><span className="app-sidebar-icon">🛡</span><span className="app-sidebar-label">管理</span></span>
          </button>
        )}
      </div>
    </aside>
  );
}
