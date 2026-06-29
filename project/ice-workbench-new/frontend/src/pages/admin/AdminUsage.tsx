import { useEffect, useMemo, useState } from "react";
import { adminApi, usageApi } from "@/api/endpoints";
import type { DailyUsage, DimUsage, UsageSummary } from "@/api/endpoints";
import type { AdminUser, AdminAgent } from "@/api/endpoints";
import { Skeleton } from "@/components/feedback/Skeleton";
import { BarSeries, Sparkline } from "@/components/charts/Sparkline";
import { EChartLazy } from "@/components/charts/EChartLazy";
import type { EChartsOption } from "@/components/charts/EChartLazy";

type Tab = "daily" | "model" | "user" | "agent" | "task";

const TABS: { k: Tab; label: string }[] = [
  { k: "daily", label: "日趋势" },
  { k: "model", label: "按模型" },
  { k: "user", label: "按用户" },
  { k: "agent", label: "按 Agent" },
  { k: "task", label: "按任务" },
];

const PERIODS = [7, 30, 90];

export function AdminUsage() {
  const [tab, setTab] = useState<Tab>("daily");
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [daily, setDaily] = useState<DailyUsage[]>([]);
  const [byDim, setByDim] = useState<Record<Tab, DimUsage[]>>({
    daily: [],
    model: [],
    user: [],
    agent: [],
    task: [],
  });
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [agents, setAgents] = useState<AdminAgent[]>([]);

  const reload = async () => {
    setSummary(await usageApi.summary());
    setDaily((await usageApi.daily(days)).items);
    const [m, u, a, t] = await Promise.all([
      usageApi.byDim("model", days, 10),
      usageApi.byDim("user_id", days, 10),
      usageApi.byDim("agent_id", days, 10),
      usageApi.byDim("task_id", days, 10),
    ]);
    setByDim({ daily: [], model: m.items, user: u.items, agent: a.items, task: t.items });
  };

  useEffect(() => {
    void reload();
    adminApi.listUsers().then((r) => setUsers(r.items)).catch(() => {});
    adminApi.listAgents().then((r) => setAgents(r.items)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const userById = useMemo(() => {
    const m: Record<string, AdminUser> = {};
    users.forEach((u) => (m[u.id] = u));
    return m;
  }, [users]);
  const agentById = useMemo(() => {
    const m: Record<string, AdminAgent> = {};
    agents.forEach((a) => (m[a.id] = a));
    return m;
  }, [agents]);

  /** Prefer the server-sent label (resolved via users_index / tasks_index /
   * agents catalog). Fall back to the local lookup maps (keeps email / icon
   * context we have on the client) and finally to a truncated id. */
  const labelFor = (t: Tab, item: DimUsage): string => {
    if (item.label && item.label !== item.key) return item.label;
    const key = item.key;
    if (t === "user") return userById[key]?.name || userById[key]?.email || key.slice(0, 8);
    if (t === "agent") return agentById[key]?.name || key;
    if (t === "task") return key.slice(0, 12) + "…";
    return key;
  };

  if (!summary) {
    return (
      <div>
        <Skeleton lines={6} />
      </div>
    );
  }

  return (
    <>
      <header className="adm-page-head adm-page-head-with-toolbar">
        <div>
          <h1>用量与成本 (Usage)</h1>
          <p>按 LLM tokens × 单价计算；超预算自动告警</p>
        </div>
        <div className="adm-period-toolbar">
          {PERIODS.map((d) => (
            <button
              key={d}
              className={d === days ? "btn-primary" : "btn-secondary"}
              onClick={() => setDays(d)}
              style={{ padding: "6px 14px", fontSize: 12 }}
            >
              {d} 天
            </button>
          ))}
          <a className="btn-secondary" href={usageApi.exportCsvUrl(days)} target="_blank" rel="noreferrer">
            <i className="ph ph-download-simple" aria-hidden="true" />
            CSV
          </a>
        </div>
      </header>

      <div className="v6-page-content adm-usage-page">
        <BudgetCard summary={summary} />

        <div className="adm-usage-stat-grid">
          <Stat label="本月调用" val={summary.calls.toLocaleString()} icon="ph-phone-call" tone="orange" />
          <Stat label="本月输入" val={fmtTokens(summary.input_tokens)} icon="ph-arrow-circle-down" tone="blue" />
          <Stat label="本月输出" val={fmtTokens(summary.output_tokens)} icon="ph-arrow-circle-up" tone="green" />
          <Stat label="本月成本" val={`$${summary.cost_usd.toFixed(2)}`} icon="ph-currency-dollar" tone="violet" />
        </div>

        <div className="adm-usage-tabs" role="tablist" aria-label="用量维度">
          {TABS.map((t) => (
            <button
              key={t.k}
              type="button"
              role="tab"
              aria-selected={tab === t.k}
              className={tab === t.k ? "active" : ""}
              onClick={() => setTab(t.k)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "daily" && (
          <section className="v6-card adm-usage-card">
            <div className="adm-usage-card-head">
              <div>
                <h2>过去 {days} 天每日成本</h2>
                <p>单位：USD</p>
              </div>
            </div>
            <div className="adm-usage-chart">
              <EChartLazy
                style={{ height: 200, width: "100%" }}
                fallback={<Sparkline values={daily.map((d) => d.cost_usd)} height={140} />}
                option={dailyCostOption(daily)}
              />
            </div>
            <div className="adm-usage-card-head compact">
              <div>
                <h2>调用次数</h2>
                <p>按自然日聚合</p>
              </div>
            </div>
            <div className="adm-usage-chart small">
              <EChartLazy
                style={{ height: 160, width: "100%" }}
                fallback={<Sparkline values={daily.map((d) => d.calls)} height={100} stroke="var(--info)" fill="var(--info-soft)" />}
                option={dailyCallsOption(daily)}
              />
            </div>
            <div className="adm-table-scroll">
              <table className="adm-usage-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th className="num">调用</th>
                    <th className="num">输入 tokens</th>
                    <th className="num">输出 tokens</th>
                    <th className="num">成本 (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {daily.slice().reverse().slice(0, 14).map((d) => (
                    <tr key={d.day}>
                      <td>{d.day}</td>
                      <td className="num">{d.calls}</td>
                      <td className="num mono">{d.input_tokens.toLocaleString()}</td>
                      <td className="num mono">{d.output_tokens.toLocaleString()}</td>
                      <td className="num mono">${d.cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {tab !== "daily" && (
          <section className="v6-card adm-usage-card">
            <div className="adm-usage-card-head">
              <div>
                <h2>{TABS.find((t) => t.k === tab)?.label}</h2>
                <p>按成本降序展示 Top 10</p>
              </div>
            </div>
            <div className="adm-usage-bars">
              {(() => {
                const rows = byDim[tab];
                const byKey: Record<string, DimUsage> = {};
                rows.forEach((it) => (byKey[it.key] = it));
                return (
                  <BarSeries
                    items={rows.map((it) => ({ key: it.key, value: it.cost_usd }))}
                    color={tab === "model" ? "var(--primary)" : tab === "user" ? "var(--info)" : tab === "agent" ? "var(--p-gray)" : "var(--success)"}
                    formatLabel={(k) => (byKey[k] ? labelFor(tab, byKey[k]) : k)}
                    formatValue={(v) => `$${v.toFixed(4)}`}
                  />
                );
              })()}
            </div>
            <div className="adm-table-scroll">
              <table className="adm-usage-table">
                <thead>
                  <tr>
                    <th>{tab === "model" ? "模型" : tab === "user" ? "用户" : tab === "agent" ? "Agent" : "任务"}</th>
                    <th className="num">调用</th>
                    <th className="num">输入</th>
                    <th className="num">输出</th>
                    <th className="num">成本</th>
                  </tr>
                </thead>
                <tbody>
                  {byDim[tab].map((it) => (
                    <tr key={it.key}>
                      <td>
                        <div className="adm-usage-name">
                          <span>{labelFor(tab, it)}</span>
                          {it.label && it.label !== it.key && <code>{it.key.slice(0, 8)}</code>}
                        </div>
                      </td>
                      <td className="num">{it.calls}</td>
                      <td className="num mono">{it.input_tokens.toLocaleString()}</td>
                      <td className="num mono">{it.output_tokens.toLocaleString()}</td>
                      <td className="num mono">${it.cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                  {byDim[tab].length === 0 && (
                    <tr>
                      <td colSpan={5} className="adm-empty-cell">
                        暂无数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </>
  );
}

function BudgetCard({ summary }: { summary: UsageSummary }) {
  const ratio = summary.budget_used_ratio;
  const pct = Math.min(100, ratio * 100);
  const color =
    summary.budget_state === "exceeded"
      ? "var(--error)"
      : summary.budget_state === "warning"
        ? "var(--warning)"
        : "var(--success)";
  const label =
    summary.budget_state === "exceeded"
      ? "已超预算"
      : summary.budget_state === "warning"
        ? "接近预算上限"
        : "预算充足";
  return (
    <section className={`v6-card adm-usage-budget ${summary.budget_state}`} style={{ borderColor: color }}>
      <div className="adm-usage-budget-row">
        <div>
          <div className="adm-usage-budget-title" style={{ color }}>
            {label}
          </div>
          <div className="adm-usage-budget-sub">
            本月预算 ${summary.budget_usd.toFixed(2)} · 已用 ${summary.cost_usd.toFixed(2)} ({(ratio * 100).toFixed(1)}%)
          </div>
        </div>
        <div className="adm-usage-month">{summary.month}</div>
      </div>
      <div className="adm-usage-progress">
        <div style={{ width: `${pct}%`, background: color }} />
      </div>
    </section>
  );
}

function Stat({
  label,
  val,
  icon,
  tone,
}: {
  label: string;
  val: string | number;
  icon: string;
  tone: "orange" | "blue" | "green" | "violet";
}) {
  return (
    <section className="v6-card adm-usage-stat">
      <div className={`adm-usage-stat-icon ${tone}`}>
        <i className={`ph ${icon}`} aria-hidden="true" />
      </div>
      <div>
        <div className="adm-usage-stat-label">{label}</div>
        <div className="adm-usage-stat-val">{val}</div>
      </div>
    </section>
  );
}

function fmtTokens(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

// ---- ECharts option builders ----

function dailyCostOption(daily: DailyUsage[]): EChartsOption {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: "category", data: daily.map((d) => d.day.slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => `$${v.toFixed(2)}` } },
    series: [{
      type: "line",
      data: daily.map((d) => d.cost_usd),
      smooth: true,
      areaStyle: { opacity: 0.15 },
      itemStyle: { color: "#6366f1" },
    }],
  };
}

function dailyCallsOption(daily: DailyUsage[]): EChartsOption {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
    xAxis: { type: "category", data: daily.map((d) => d.day.slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: "value" },
    series: [{
      type: "bar",
      data: daily.map((d) => d.calls),
      itemStyle: { color: "#3b82f6", borderRadius: [3, 3, 0, 0] },
    }],
  };
}
