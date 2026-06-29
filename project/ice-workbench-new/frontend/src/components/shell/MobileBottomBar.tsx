/**
 * Mobile bottom TabBar — shown on screens ≤ 800px.
 * Matches mobile_dashboard.html design (v7 prototype).
 */
import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import "./MobileBottomBar.css";

interface Tab {
  to: string;
  icon: string;
  activeIcon: string;
  label: string;
  match: (path: string) => boolean;
  adminOnly?: boolean;
}

const TABS: Tab[] = [
  { to: "/dashboard", icon: "ph-lightning", activeIcon: "ph-fill ph-lightning", label: "首页", match: (p) => p === "/dashboard" || p === "/" },
  { to: "/dashboard?tab=mine", icon: "ph-clipboard-text", activeIcon: "ph-fill ph-clipboard-text", label: "任务", match: (p) => p.startsWith("/dashboard") && p.includes("tab=mine") },
  { to: "/scheduled-tasks", icon: "ph-timer", activeIcon: "ph-fill ph-timer", label: "定时", match: (p) => p.startsWith("/scheduled") },
  { to: "/guide", icon: "ph-book-open", activeIcon: "ph-fill ph-book-open", label: "指南", match: (p) => p.startsWith("/guide") },
  { to: "/admin", icon: "ph-user", activeIcon: "ph-fill ph-user", label: "我的", match: (p) => p.startsWith("/admin"), adminOnly: false },
];

export function MobileBottomBar() {
  const { pathname, search } = useLocation();
  const fullPath = pathname + search;
  const isAdmin = useAuthStore(
    (s) => s.user?.auth_role === "admin" || s.user?.auth_role === "super_admin",
  );
  // "我的" tab always visible; admin tab only for admins (handled elsewhere)
  const tabs = TABS.filter((t) => !t.adminOnly || isAdmin);

  return (
    <nav className="m-bottombar" aria-label="底部导航">
      {tabs.map((t) => {
        const active = t.match(fullPath);
        return (
          <Link
            key={t.label}
            to={t.to}
            className={`m-bottombar-tab${active ? " active" : ""}`}
          >
            <i className={`ph ${active ? t.activeIcon : t.icon}`} />
            <span>{t.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
