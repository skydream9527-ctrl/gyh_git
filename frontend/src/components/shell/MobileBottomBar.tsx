import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import "./MobileBottomBar.css";

interface Tab {
  to: string;
  icon: string;
  label: string;
  match: (path: string) => boolean;
  adminOnly?: boolean;
}

const TABS: Tab[] = [
  { to: "/dashboard", icon: "📒", label: "笔记本", match: (p) => p.startsWith("/dashboard") || p === "/" },
  { to: "/scheduled-tasks", icon: "⏱", label: "定时", match: (p) => p.startsWith("/scheduled") },
  { to: "/guide", icon: "📖", label: "指南", match: (p) => p.startsWith("/guide") },
  { to: "/admin", icon: "🛡", label: "管理", match: (p) => p.startsWith("/admin"), adminOnly: true },
];

export function MobileBottomBar() {
  const { pathname } = useLocation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.auth_role === "admin" || user?.auth_role === "super_admin";

  const visible = TABS.filter((t) => !t.adminOnly || isAdmin);
  const fillCount = isAdmin ? 4 : 3;
  // 非 admin 时用「我」占位，提供退出/账号入口（最简实现：链接到首页 + 头像，可后续扩展）
  const tabs: Tab[] = isAdmin
    ? visible
    : [
        ...visible,
        {
          to: "/dashboard?profile=1",
          icon: user?.name?.[0] || "我",
          label: "我",
          match: () => false,
        },
      ];

  return (
    <nav className="m-bottombar" aria-label="底部导航" data-cnt={fillCount}>
      {tabs.map((t) => {
        const active = t.match(pathname);
        return (
          <Link
            key={t.label}
            to={t.to}
            className={`m-bottombar-tab${active ? " active" : ""}`}
          >
            <span className="pill">{t.icon}</span>
            <span>{t.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
