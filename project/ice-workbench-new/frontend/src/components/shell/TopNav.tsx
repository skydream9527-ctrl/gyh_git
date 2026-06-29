import { Link, useNavigate } from "react-router-dom";
import { ReactNode, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { InviteInbox } from "./InviteInbox";
import { AccountModal } from "./AccountModal";
import { ThemeSelect } from "./ThemeSelect";
import "./TopNav.css";

type Mode = "dashboard" | "workspace" | "admin" | "introduce";

interface Props {
  mode: Mode;
  crumb?: ReactNode;
  agentChip?: ReactNode;
  rightActions?: ReactNode;
}

export function TopNav({ mode, crumb, agentChip, rightActions }: Props) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [menuOpen]);

  const handleLogout = async () => {
    setMenuOpen(false);
    try {
      await Promise.resolve(logout());
    } finally {
      navigate("/login?logout=1", { replace: true });
    }
  };

  return (
    <nav className={`topnav topnav-${mode}`}>
      <Link to="/dashboard" className="brand">
        <div className="brand-logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" style={{color: "var(--primary)"}}><path d="M12 2L2 7l10 5 10-5-10-5zm0 7.5l-10-5v10l10 5 10-5v-10l-10 5z"/></svg>
        </div>
        <span className="brand-name">
          <span className="brand-accent">ICE</span>{" "}
          {mode === "admin" ? "管理后台" : "Workbench"}
        </span>
      </Link>
      {crumb && <div className="crumb">{crumb}</div>}
      {agentChip && <div className="agent-chip">{agentChip}</div>}
      <div className="right">
        {rightActions}
        {user && <InviteInbox />}
        <ThemeSelect />
        {user && (
          <div className="user-menu" ref={menuRef}>
            <button
              className="user-pill"
              onClick={() => setMenuOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="avatar">{user.name?.[0] || "U"}</span>
              <span className="uname">{user.name}</span>
              <span className="caret">▾</span>
            </button>
            {menuOpen && (
              <div className="user-menu-pop" role="menu">
                <div className="umi-head">
                  <span className="avatar lg">{user.name?.[0] || "U"}</span>
                  <div className="umi-info">
                    <div className="umi-name">{user.name}</div>
                    {user.auth_role && (
                      <div className="umi-role">{user.auth_role}</div>
                    )}
                  </div>
                </div>
                <div className="umi-divider" />
                <button
                  className="umi-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setAccountOpen(true);
                  }}
                  role="menuitem"
                >
                  ✏ 编辑账户
                </button>
                <div className="umi-divider" />
                <button className="umi-item danger" onClick={handleLogout} role="menuitem">
                  🚪 退出登录
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      <AccountModal open={accountOpen} onClose={() => setAccountOpen(false)} />
    </nav>
  );
}
