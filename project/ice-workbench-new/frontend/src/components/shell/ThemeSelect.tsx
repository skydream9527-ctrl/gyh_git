import { useState, useRef, useEffect } from "react";
import { useUIStore, Theme, getThemeIcon, getThemeName } from "@/stores/uiStore";
import "./ThemeSelect.css";

const THEMES: Theme[] = ["light", "dark", "su7-gulf", "su7-elegant", "su7-olive", "su7-purple", "su7-meteor", "su7-cambrian", "su7-pearl", "su7-diamond", "yu7-moon", "yu7-night", "yu7-sky", "yu7-forest", "ip13-pink", "ip13-blue", "ip13p-sierra", "ip13p-alpine", "ip14-yellow", "ip14p-purple", "ip14p-space", "ip15-green", "ip15p-blue", "ip15p-natural", "ip16-ultra", "ip16-teal", "ip16p-desert", "ip17-ice", "ip17p-rose"];

export function ThemeSelect() {
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <div className="theme-select-container" ref={menuRef}>
      <button 
        className="icon-btn theme-btn" 
        onClick={() => setOpen(!open)}
        title={`切换主题 (当前: ${getThemeName(theme)})`}
        aria-label="theme-select"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {getThemeIcon(theme)}
      </button>
      
      {open && (
        <div className="theme-select-menu" role="listbox">
          <div className="theme-menu-title">切换外观</div>
          {THEMES.map((t) => (
            <button
              key={t}
              className={`theme-item ${theme === t ? "active" : ""}`}
              onClick={() => {
                setTheme(t);
                setOpen(false);
              }}
              role="option"
              aria-selected={theme === t}
            >
              <span className="theme-icon">{getThemeIcon(t)}</span>
              <span className="theme-name">{getThemeName(t)}</span>
              {theme === t && <span className="theme-check">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
