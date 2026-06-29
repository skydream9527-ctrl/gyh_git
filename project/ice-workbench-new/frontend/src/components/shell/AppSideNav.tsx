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

  const isQuick = active === "quick";
  const isMine = active === "mine";
  const isPublic = active === "public";
  const isScheduled = active === "scheduled" || location.pathname.startsWith("/scheduled");
  const isGuide = active === "guide" || location.pathname.startsWith("/guide");
  const isAdminActive = active === "admin" || location.pathname.startsWith("/admin");

  return (
    <aside className={`app-sidebar${collapsed ? " collapsed" : ""}`} aria-label="主导航">
      {/* Logo */}
      <div className="app-sidebar-logo" onClick={() => navigate("/dashboard")} title="ICE Workbench">
        <i className="ph-fill ph-hexagon app-sidebar-logo-icon"></i>
        {!collapsed && (
          <span className="app-sidebar-logo-text">
            <span className="app-sidebar-logo-accent">ICE</span> Workbench
          </span>
        )}
      </div>

      {/* Toggle */}
      <button
        type="button"
        className="app-sidebar-toggle"
        onClick={() => setCollapsed((v) => !v)}
        aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        title={collapsed ? "展开侧边栏" : "收起侧边栏"}
      >
        <i className={`ph ph-${collapsed ? "caret-right" : "caret-left"}`}></i>
      </button>

      {/* Nav */}
      <nav className="app-sidebar-nav">
        <div className="app-sidebar-group">{!collapsed && "工作区"}</div>
        <button
          type="button"
          className={`app-sidebar-item${isQuick ? " active" : ""}`}
          onClick={() => goDash("quick")}
          title="快速开始"
        >
          <i className="ph ph-lightning app-sidebar-icon"></i>
          {!collapsed && <span className="app-sidebar-label">快速开始</span>}
        </button>
        <button
          type="button"
          className={`app-sidebar-item${isMine ? " active" : ""}`}
          onClick={() => goDash("mine")}
          title="我的任务"
        >
          <i className="ph ph-clipboard-text app-sidebar-icon"></i>
          {!collapsed && <span className="app-sidebar-label">我的任务</span>}
          {actionRequiredCount > 0 && (
            <span className="app-sidebar-badge">{actionRequiredCount}</span>
          )}
        </button>
        <button
          type="button"
          className={`app-sidebar-item${isPublic ? " active" : ""}`}
          onClick={() => goDash("public")}
          title="团队公共区"
        >
          <i className="ph ph-globe app-sidebar-icon"></i>
          {!collapsed && <span className="app-sidebar-label">团队公共区</span>}
        </button>

        <div className="app-sidebar-group">{!collapsed && "资源"}</div>
        <button
          type="button"
          className={`app-sidebar-item${isScheduled ? " active" : ""}`}
          onClick={() => navigate("/scheduled-tasks")}
          title="定时任务"
        >
          <i className="ph ph-timer app-sidebar-icon"></i>
          {!collapsed && <span className="app-sidebar-label">定时任务</span>}
        </button>
        <button
          type="button"
          className={`app-sidebar-item${isGuide ? " active" : ""}`}
          onClick={() => navigate("/guide")}
          title="使用指南"
        >
          <i className="ph ph-book-open app-sidebar-icon"></i>
          {!collapsed && <span className="app-sidebar-label">使用指南</span>}
        </button>
      </nav>

      {/* Footer */}
      {isAdmin && (
        <div className="app-sidebar-footer">
          <button
            type="button"
            className={`app-sidebar-item${isAdminActive ? " active" : ""}`}
            onClick={() => navigate("/admin")}
            title="管理后台"
          >
            <i className="ph ph-shield-check app-sidebar-icon"></i>
            {!collapsed && <span className="app-sidebar-label">管理后台</span>}
          </button>
        </div>
      )}
    </aside>
  );
}
