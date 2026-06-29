import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { TopNav } from "@/components/shell/TopNav";
import { MobileBottomBar } from "@/components/shell/MobileBottomBar";
import "./Admin.css";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  group: "monitor" | "resource" | "business" | "ops";
  super?: boolean;
}

const NAV: NavItem[] = [
  // 系统监控 (System Monitoring)
  { to: "/admin", label: "管理大盘 (Overview)", icon: "ph-chart-line-up", group: "monitor" },
  { to: "/admin/usage", label: "使用统计 (Usage)", icon: "ph-trend-up", group: "monitor" },
  { to: "/admin/diagnostics", label: "系统诊断 (Diagnostics)", icon: "ph-stethoscope", group: "monitor" },
  
  // 资源与权限 (Resources & Roles)
  { to: "/admin/users", label: "用户管理 (Users)", icon: "ph-users", group: "resource" },
  { to: "/admin/experience-cards", label: "体验卡管理 (Exp Cards)", icon: "ph-ticket", group: "resource" },

  // 业务管理 (Business Management)
  { to: "/admin/agents", label: "全局智能体 (Agents)", icon: "ph-robot", group: "business" },
  { to: "/admin/skills", label: "全局技能 (Skills)", icon: "ph-puzzle-piece", group: "business" },
  { to: "/admin/templates", label: "提示词模板 (Templates)", icon: "ph-layout", group: "business" },
  { to: "/admin/knowledge-bases", label: "知识库 (Knowledge Base)", icon: "ph-books", group: "business" },
  { to: "/admin/files", label: "公共文件 (Files)", icon: "ph-folder", group: "business" },

  // 运营与安全 (Ops & Security)
  { to: "/admin/review-center", label: "审批中心 (Review)", icon: "ph-list-checks", group: "ops" },
  { to: "/admin/audit", label: "审计日志 (Audit Logs)", icon: "ph-file-text", group: "ops" },
  { to: "/admin/sql-audit", label: "SQL 审计 (SQL Audit)", icon: "ph-database", group: "ops" },
  { to: "/admin/settings", label: "系统设置 (Settings)", icon: "ph-gear", group: "ops", super: true },
];

const GROUP_LABEL: Record<NavItem["group"], string> = {
  monitor: "系统监控",
  resource: "资源与权限",
  business: "业务管理",
  ops: "运营与安全",
};

export function AdminLayout() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const groupOrder: NavItem["group"][] = ["monitor", "resource", "business", "ops"];
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className="adm-shell v6-admin">
      <div className="adm-body">
        {mobileOpen && (
          <div
            className="adm-sb-backdrop"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        <aside className={`adm-sb v6-sidebar ${mobileOpen ? "mobile-open" : ""}`}>
          <div className="v6-sidebar-logo" onClick={() => navigate("/admin")}>
            <div className="v6-logo-content">
              <i className="ph-fill ph-hexagon"></i>
              <span>System Admin</span>
              <span className="v6-version-badge">v6</span>
            </div>
          </div>

          <div className="v6-sidebar-nav">
            {groupOrder.map((g) => {
              const items = NAV.filter((n) => n.group === g);
              if (items.length === 0) return null;
              return (
                <div key={g}>
                  <div className="v6-sidebar-group">{GROUP_LABEL[g]}</div>
                  {items.map((n) => {
                    const isRestricted = n.super && user?.auth_role !== "super_admin";
                    return (
                      <NavLink
                        key={n.to}
                        to={isRestricted ? "#" : n.to}
                        end={n.to === "/admin"}
                        className={({ isActive }) => 
                          `v6-sidebar-item ${isActive && !isRestricted ? "active" : ""} ${isRestricted ? "restricted" : ""}`
                        }
                        onClick={(e) => {
                          if (isRestricted) {
                            e.preventDefault();
                            alert("需要 super_admin 权限");
                          }
                        }}
                      >
                        <i className={`ph ${n.icon}`}></i>
                        <span className="v6-item-label">{n.label}</span>
                        {isRestricted && <i className="ph-bold ph-lock-key v6-lock-icon"></i>}
                      </NavLink>
                    );
                  })}
                </div>
              );
            })}
          </div>

          <div className="v6-sidebar-footer">
            <button className="v6-return-btn" onClick={() => navigate("/dashboard")}>
              <i className="ph ph-arrow-left"></i> 返回前台工作区
            </button>
          </div>
        </aside>

        <main className="adm-main has-bottombar v6-main">
          {/* TopNav is now just a mobile hamburger trigger and breadcrumb in v6 mobile, 
              but since we hide TopNav entirely on desktop in v6, we render a local header in each page. */}
          <div className="v6-mobile-header">
            <button className="adm-mobile-menu" onClick={() => setMobileOpen((v) => !v)}>
              <i className="ph ph-list"></i>
            </button>
            <span className="font-bold">System Admin</span>
          </div>
          <div className="v6-content-area">
             <Outlet />
          </div>
        </main>
      </div>
      <MobileBottomBar />
    </div>
  );
}
