import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { adminApi } from "@/api/endpoints";
import { Skeleton } from "@/components/feedback/Skeleton";

interface Stats {
  users: number;
  tasks: number;
  messages: number;
}
interface BudgetInfo {
  month: string;
  cost_usd: number;
  budget_usd: number;
  used_ratio: number;
  state: "ok" | "warning" | "exceeded";
}
interface Alerts {
  experience_cards: number;
  public_tasks: number;
  templates: number;
  scheduled_failed: number;
  pending_users: number;
  budget_alert: "warning" | "exceeded" | null;
  budget: BudgetInfo | null;
}
interface RankItem {
  agent_id: string;
  name: string;
  icon: string;
  messages: number;
  satisfaction: number;
}
interface RecentUser {
  id: string;
  email: string;
  name: string;
  auth_role: string;
  created_at?: string | null;
}

export function AdminOverview() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [rank, setRank] = useState<RankItem[]>([]);
  const [recent, setRecent] = useState<RecentUser[]>([]);

  useEffect(() => {
    adminApi.stats().then(setStats).catch(() => {});
    adminApi.alerts().then(setAlerts).catch(() => {});
    adminApi.agentRanking().then((r) => setRank(r.items)).catch(() => {});
    adminApi.recentUsers().then((r) => setRecent(r.items)).catch(() => {});
  }, []);

  const budgetAlert = alerts?.budget_alert ?? null;

  return (
    <>
      <header className="v6-page-header">
        <div>
          <h1 className="flex items-center gap-2">系统管理大盘 (Overview)</h1>
        </div>
        <div style={{ fontSize: 14, fontWeight: 500, color: "var(--text-dim)", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: 4, background: "var(--success)" }}></span> 系统运行正常
        </div>
      </header>

      <div className="v6-page-content">
        {/* 预警与待办 (Alerts) */}
        {alerts && (
          <section style={{ marginBottom: 32 }}>
            <div className="v6-grid-4">
              <div
                onClick={() => navigate("/admin/users?status=pending")}
                className="v6-card v6-alert-red"
                style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 16 }}
              >
                <div className="v6-icon-box red"><i className="ph-bold ph-user-plus"></i></div>
                <div>
                  <div className="v6-stat-value" style={{ color: "var(--error)", margin: 0, fontSize: 24 }}>{alerts.pending_users}</div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--error)", textTransform: "uppercase", letterSpacing: "1px" }}>待审批新用户</div>
                </div>
              </div>
              
              <div 
                className="v6-card v6-alert-amber"
                style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 16 }}
              >
                <div className="v6-icon-box amber"><i className="ph-bold ph-clock"></i></div>
                <div>
                  <div className="v6-stat-value" style={{ color: "var(--warning)", margin: 0, fontSize: 24 }}>{alerts.scheduled_failed}</div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--warning)", textTransform: "uppercase", letterSpacing: "1px" }}>失败定时任务</div>
                </div>
              </div>

              <div 
                className="v6-card" 
                style={{ gridColumn: "span 2", display: "flex", alignItems: "center", gap: 16 }}
              >
                <div className="v6-icon-box blue"><i className="ph-bold ph-currency-circle-dollar"></i></div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-dim)" }}>本月模型消耗 (API Budget)</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: budgetAlert === "exceeded" ? "var(--error)" : "var(--info)" }}>
                      ${alerts.budget?.cost_usd.toFixed(2) ?? "0.00"}
                      <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 400 }}> / ${alerts.budget?.budget_usd.toFixed(0) ?? "500"}</span>
                    </div>
                  </div>
                  <div style={{ width: "100%", background: "var(--surface-2)", borderRadius: 4, height: 8, overflow: "hidden" }}>
                    <div 
                      style={{ 
                        background: budgetAlert === "exceeded" ? "var(--error)" : "var(--info)", 
                        height: "100%", 
                        width: `${Math.min(100, (alerts.budget?.used_ratio || 0) * 100)}%` 
                      }} 
                    />
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* 数据概览 (Stats) & 排行 */}
        <div className="v6-grid-3">
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="v6-grid-3">
              <div className="v6-card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 24 }}>
                <div className="v6-stat-label"><i className="ph-fill ph-users"></i> 总用户数</div>
                <div className="v6-stat-value">{stats ? stats.users.toLocaleString() : <Skeleton lines={1} />}</div>
                {stats && <div className="v6-stat-trend"><i className="ph-bold ph-trend-up"></i> +12% 本月</div>}
              </div>
              <div className="v6-card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 24 }}>
                <div className="v6-stat-label"><i className="ph-fill ph-squares-four"></i> 累计任务数</div>
                <div className="v6-stat-value">{stats ? stats.tasks.toLocaleString() : <Skeleton lines={1} />}</div>
                {stats && <div className="v6-stat-trend"><i className="ph-bold ph-trend-up"></i> +8% 本月</div>}
              </div>
              <div className="v6-card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: 24 }}>
                <div className="v6-stat-label"><i className="ph-fill ph-chat-centered-text"></i> 消息交互数</div>
                <div className="v6-stat-value">{stats ? stats.messages.toLocaleString() : <Skeleton lines={1} />}</div>
                {stats && <div className="v6-stat-trend"><i className="ph-bold ph-trend-up"></i> +24% 本月</div>}
              </div>
            </div>

            {/* Recent Users Table */}
            <div className="v6-card" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--surface-2)", background: "rgba(248,250,252,0.5)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text)" }}>最新注册用户 (Recent Users)</h3>
                <Link to="/admin/users" style={{ fontSize: 13, fontWeight: 700, color: "var(--primary)", textDecoration: "none" }}>查看全部</Link>
              </div>
              <table style={{ width: "100%", textAlign: "left", fontSize: 14, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--surface-2)" }}>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>邮箱 / 姓名</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>角色</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600, textAlign: "right" }}>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.length === 0 ? (
                    <tr><td colSpan={3} style={{ padding: 20 }}><Skeleton lines={3} /></td></tr>
                  ) : (
                    recent.slice(0, 4).map(u => (
                      <tr key={u.id} style={{ borderBottom: "1px solid var(--surface-2)" }}>
                        <td style={{ padding: "12px 20px" }}>
                          <div style={{ fontWeight: 700, color: "var(--text)" }}>{u.email}</div>
                          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{u.name || "未设置姓名"}</div>
                        </td>
                        <td style={{ padding: "12px 20px" }}>
                          {u.auth_role === "super_admin" ? (
                            <span style={{ background: "var(--warning-soft)", color: "var(--warning)", padding: "4px 8px", borderRadius: 4, fontSize: 12, fontWeight: 700, border: "1px solid var(--warning-soft)" }}>Super</span>
                          ) : u.auth_role === "admin" ? (
                            <span style={{ background: "var(--p-gray-soft)", color: "var(--p-gray)", padding: "4px 8px", borderRadius: 4, fontSize: 12, fontWeight: 700, border: "1px solid var(--p-gray-soft)" }}>Admin</span>
                          ) : (
                            <span style={{ background: "var(--info-soft)", color: "var(--info)", padding: "4px 8px", borderRadius: 4, fontSize: 12, fontWeight: 700, border: "1px solid var(--info-soft)" }}>User</span>
                          )}
                        </td>
                        <td style={{ padding: "12px 20px", textAlign: "right", color: "var(--text-muted)", fontSize: 12 }}>
                          {fmt(u.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 智能体热度排行 (Agent Rank) */}
          <div className="v6-card" style={{ padding: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--surface-2)", background: "rgba(248,250,252,0.5)" }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text)" }}>智能体调用排行 (Hot Agents)</h3>
            </div>
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
              {rank.length === 0 ? (
                <Skeleton lines={4} />
              ) : (
                rank.slice(0, 5).map((r, i) => (
                  <div key={r.agent_id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 24, height: 24, borderRadius: 4, background: "var(--surface-2)", color: "var(--text-muted)", fontWeight: 700, fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</div>
                    <div style={{ width: 40, height: 40, borderRadius: 20, background: "var(--primary-dim)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, border: "1px solid var(--primary-dim)" }}>
                      {r.icon || "🤖"}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, color: "var(--text)", fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{r.messages.toLocaleString()} 次调用</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function fmt(iso?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toLocaleDateString()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString();
}
