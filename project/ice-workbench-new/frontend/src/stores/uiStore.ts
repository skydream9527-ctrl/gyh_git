import { create } from "zustand";

export type Theme = "light" | "dark" | "su7-gulf" | "su7-elegant" | "su7-olive" | "su7-purple" | "su7-meteor" | "su7-cambrian" | "su7-pearl" | "su7-diamond" | "yu7-moon" | "yu7-night" | "yu7-sky" | "yu7-forest" | "ip13-pink" | "ip13-blue" | "ip13p-sierra" | "ip13p-alpine" | "ip14-yellow" | "ip14p-purple" | "ip14p-space" | "ip15-green" | "ip15p-blue" | "ip15p-natural" | "ip16-ultra" | "ip16-teal" | "ip16p-desert" | "ip17-ice" | "ip17p-rose";

export const getThemeIcon = (t: Theme) => {
  switch (t) {
    case "light": return "☀";
    case "dark": return "🌓";
    case "su7-gulf": return "🏎";
    case "su7-elegant": return "🌫";
    case "su7-olive": return "🍃";
    case "su7-purple": return "✨";
    case "su7-meteor": return "☄";
    case "su7-cambrian": return "🪨";
    case "su7-pearl": return "⚪";
    case "su7-diamond": return "⚫";
    case "yu7-moon": return "🌙";
    case "yu7-night": return "🌑";
    case "yu7-sky": return "🌌";
    case "yu7-forest": return "🌲";
    case "ip13-pink": return "🌸";
    case "ip13-blue": return "🌊";
    case "ip13p-sierra": return "🏔";
    case "ip13p-alpine": return "🌿";
    case "ip14-yellow": return "🍋";
    case "ip14p-purple": return "🔮";
    case "ip14p-space": return "🚀";
    case "ip15-green": return "🍏";
    case "ip15p-blue": return "⚓";
    case "ip15p-natural": return "⚙";
    case "ip16-ultra": return "🌀";
    case "ip16-teal": return "🦚";
    case "ip16p-desert": return "🏜";
    case "ip17-ice": return "🧊";
    case "ip17p-rose": return "🥀";
    default: return "☀";
  }
};

export const getThemeName = (t: Theme) => {
  switch (t) {
    case "light": return "默认浅色";
    case "dark": return "默认深色";
    case "su7-gulf": return "海湾蓝";
    case "su7-elegant": return "雅灰";
    case "su7-olive": return "橄榄绿";
    case "su7-purple": return "霞光紫";
    case "su7-meteor": return "流星蓝";
    case "su7-cambrian": return "寒武岩灰";
    case "su7-pearl": return "珍珠白";
    case "su7-diamond": return "钻石黑";
    case "yu7-moon": return "月光银";
    case "yu7-night": return "极夜黑";
    case "yu7-sky": return "远空蓝";
    case "yu7-forest": return "旷野绿";
    case "ip13-pink": return "粉色";
    case "ip13-blue": return "蓝色";
    case "ip13p-sierra": return "远峰蓝";
    case "ip13p-alpine": return "苍岭绿";
    case "ip14-yellow": return "黄色";
    case "ip14p-purple": return "暗紫色";
    case "ip14p-space": return "空间黑";
    case "ip15-green": return "绿色";
    case "ip15p-blue": return "蓝色钛金属";
    case "ip15p-natural": return "原色钛金属";
    case "ip16-ultra": return "群青色";
    case "ip16-teal": return "深青色";
    case "ip16p-desert": return "沙漠钛金属";
    case "ip17-ice": return "冰雪蓝";
    case "ip17p-rose": return "玫瑰钛金属";
    default: return "默认浅色";
  }
};

export interface ToastMsg {
  id: string;
  kind: "success" | "warning" | "error" | "info";
  message: string;
}

interface UIState {
  theme: Theme;
  toasts: ToastMsg[];
  /** Server-reported feature flag — set by ensureVoiceConfig() after first
   * /system-config/global-toggles fetch. `null` means "not yet loaded";
   * components should treat that as "off" until it resolves. */
  voiceEnabled: boolean | null;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
  /** Show a toast. `durationMs` controls auto-dismiss; defaults to 3500ms. */
  pushToast: (kind: ToastMsg["kind"], message: string, durationMs?: number) => void;
  dismissToast: (id: string) => void;
  setVoiceEnabled: (v: boolean) => void;
}

const THEME_KEY = "ice-theme-v3";

function readTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const saved = localStorage.getItem(THEME_KEY) as Theme;
  if (["light", "dark", "su7-gulf", "su7-elegant", "su7-olive", "su7-purple", "su7-meteor", "su7-cambrian", "su7-pearl", "su7-diamond", "yu7-moon", "yu7-night", "yu7-sky", "yu7-forest", "ip13-pink", "ip13-blue", "ip13p-sierra", "ip13p-alpine", "ip14-yellow", "ip14p-purple", "ip14p-space", "ip15-green", "ip15p-blue", "ip15p-natural", "ip16-ultra", "ip16-teal", "ip16p-desert", "ip17-ice", "ip17p-rose"].includes(saved)) {
    return saved;
  }
  return "light";
}

function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem(THEME_KEY, t);
}

export const useUIStore = create<UIState>((set, get) => ({
  theme: readTheme(),
  toasts: [],
  voiceEnabled: null,
  setVoiceEnabled: (v) => set({ voiceEnabled: v }),
  toggleTheme: () => {
    const order: Theme[] = ["light", "dark", "su7-gulf", "su7-elegant", "su7-olive", "su7-purple", "su7-meteor", "su7-cambrian", "su7-pearl", "su7-diamond", "yu7-moon", "yu7-night", "yu7-sky", "yu7-forest", "ip13-pink", "ip13-blue", "ip13p-sierra", "ip13p-alpine", "ip14-yellow", "ip14p-purple", "ip14p-space", "ip15-green", "ip15p-blue", "ip15p-natural", "ip16-ultra", "ip16-teal", "ip16p-desert", "ip17-ice", "ip17p-rose"];
    const current = get().theme;
    let idx = order.indexOf(current);
    if (idx === -1) idx = 0;
    const next = order[(idx + 1) % order.length];
    applyTheme(next);
    set({ theme: next });
  },
  setTheme: (t) => {
    applyTheme(t);
    set({ theme: t });
  },
  pushToast: (kind, message, durationMs = 3500) => {
    const id = Math.random().toString(36).slice(2);
    set({ toasts: [...get().toasts, { id, kind, message }] });
    setTimeout(() => get().dismissToast(id), durationMs);
  },
  dismissToast: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

if (typeof window !== "undefined") {
  applyTheme(readTheme());
}
