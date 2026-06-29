import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";

interface Overview {
  users: number;
  teams: number;
  projects: number;
  agents: number;
  tasks: number;
  total_tokens: number;
  total_cost_usd: number;
  global_paused: boolean;
}

interface AdminUser {
  id: string;
  name: string;
  platform_role: string;
}

interface AdminTeam {
  id: string;
  name: string;
  member_count: number;
  project_count: number;
}

interface UsageSummary {
  total_calls: number;
  total_tokens: number;
  total_cost_usd: number;
  monthly_budget_usd: number;
  budget_used_pct: number | null;
  by_model: Record<string, { calls: number; tokens: number; cost_usd: number }>;
}

interface SettingsData {
  llm_enabled: boolean;
  pgvector_enabled: boolean;
  feishu_configured: boolean;
  kyuubi_configured: boolean;
  features: Record<string, boolean>;
}

type Tab = "overview" | "users" | "teams" | "usage" | "settings";

export default function Admin() {
  const { user } = useAuthStore();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [teams, setTeams] = useState<AdminTeam[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    apiGet<Overview>("/admin/overview")
      .then(setOverview)
      .catch(() => setDenied(true));
  }, []);

  useEffect(() => {
    if (tab === "users" && users.length === 0) apiGet<AdminUser[]>("/admin/users").then(setUsers).catch(() => {});
    if (tab === "teams" && teams.length === 0) apiGet<AdminTeam[]>("/admin/teams").then(setTeams).catch(() => {});
    if (tab === "usage" && !usage) apiGet<UsageSummary>("/admin/usage").then(setUsage).catch(() => {});
    if (tab === "settings" && !settings) apiGet<SettingsData>("/admin/settings").then(setSettings).catch(() => {});
  }, [tab, users.length, teams.length, usage, settings]);

  if (denied) {
    return (
      <div className="page">
        <h1>管理后台</h1>
        <div className="card err">需要管理员权限（当前：{user?.platform_role}）。</div>
      </div>
    );
  }

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="eyebrow">Admin · admin+</div>
          <h1>管理后台</h1>
          <p className="subtle">用户、Agent/Skill、团队项目、用量与系统设置。角色编辑限 super_admin。</p>
        </div>
      </div>

      <div className="admin-tabs">
        {(["overview", "users", "teams", "usage", "settings"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {{ overview: "概览", users: "用户", teams: "团队/项目", usage: "用量与成本", settings: "系统设置" }[t]}
          </button>
        ))}
      </div>

      {tab === "overview" && overview && (
        <div className="admin-stats">
          <div className="stat"><b>{overview.users}</b><span>用户</span></div>
          <div className="stat"><b>{overview.teams}</b><span>团队</span></div>
          <div className="stat"><b>{overview.projects}</b><span>项目</span></div>
          <div className="stat"><b>{overview.agents}</b><span>Agent</span></div>
          <div className="stat"><b>{overview.tasks}</b><span>任务</span></div>
          <div className="stat"><b>{overview.total_tokens}</b><span>累计 Token</span></div>
          <div className="stat"><b>${overview.total_cost_usd}</b><span>累计成本</span></div>
          <div className="stat"><b>{overview.global_paused ? "暂停" : "运行"}</b><span>执行状态</span></div>
        </div>
      )}

      {tab === "users" && (
        <div className="card">
          <div className="table-head">
            <span>用户</span><span>平台角色</span>
          </div>
          {users.map((u) => (
            <div className="row" key={u.id}>
              <span><strong>{u.name}</strong> <span className="mono">{u.id}</span></span>
              <span className={`pill ${u.platform_role === "super_admin" ? "violet" : u.platform_role === "admin" ? "blue" : "slate"}`}>
                {u.platform_role}
              </span>
            </div>
          ))}
        </div>
      )}

      {tab === "teams" && (
        <div className="card">
          <div className="table-head"><span>团队</span><span>成员 / 项目</span></div>
          {teams.map((t) => (
            <div className="row" key={t.id}>
              <span><strong>{t.name}</strong> <span className="mono">{t.id}</span></span>
              <span className="task-meta">{t.member_count} 成员 · {t.project_count} 项目</span>
            </div>
          ))}
          {teams.length === 0 && <div className="lane-empty">暂无团队</div>}
        </div>
      )}

      {tab === "usage" && usage && (
        <div>
          <div className="admin-stats">
            <div className="stat"><b>{usage.total_calls}</b><span>调用次数</span></div>
            <div className="stat"><b>{usage.total_tokens}</b><span>总 Token</span></div>
            <div className="stat"><b>${usage.total_cost_usd}</b><span>总成本</span></div>
            <div className="stat"><b>{usage.budget_used_pct ?? 0}%</b><span>预算用量 (${usage.monthly_budget_usd})</span></div>
          </div>
          <div className="card">
            <div className="card-head"><h3>按模型</h3>
              <a className="btn-sm" href="/api/v1/usage/export" target="_blank" rel="noreferrer">导出 CSV</a>
            </div>
            {Object.entries(usage.by_model).map(([m, v]) => (
              <div className="row" key={m}>
                <span><strong>{m}</strong></span>
                <span className="task-meta">{v.calls} 次 · {v.tokens} tokens · ${v.cost_usd}</span>
              </div>
            ))}
            {Object.keys(usage.by_model).length === 0 && <div className="lane-empty">暂无用量数据</div>}
          </div>
        </div>
      )}

      {tab === "settings" && settings && (
        <div className="card">
          <div className="row"><b>LLM 网关</b><span className={`pill ${settings.llm_enabled ? "green" : "slate"}`}>{settings.llm_enabled ? "已配置" : "未配置(mock)"}</span></div>
          <div className="row"><b>pgvector</b><span className={`pill ${settings.pgvector_enabled ? "green" : "slate"}`}>{settings.pgvector_enabled ? "on" : "off"}</span></div>
          <div className="row"><b>飞书集成</b><span className={`pill ${settings.feishu_configured ? "green" : "slate"}`}>{settings.feishu_configured ? "已配置" : "未配置"}</span></div>
          <div className="row"><b>Kyuubi</b><span className={`pill ${settings.kyuubi_configured ? "green" : "slate"}`}>{settings.kyuubi_configured ? "已配置" : "未配置"}</span></div>
          <div className="row"><b>特性开关</b><span className="mono">{JSON.stringify(settings.features)}</span></div>
        </div>
      )}
    </div>
  );
}
