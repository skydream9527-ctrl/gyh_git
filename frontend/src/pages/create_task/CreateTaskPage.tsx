import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { agentApi, scheduledApi, taskApi, templateApi } from "@/api/endpoints";
import type { ApiError } from "@/api/client";
import type { AgentCard } from "@/types/api";
import type { TemplateRecord } from "@/api/endpoints";
import { TopNav } from "@/components/shell/TopNav";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useUIStore } from "@/stores/uiStore";
import "./CreateTask.css";

type Step = 1 | 2 | 3;

const PARADIGM_PLACEHOLDER: Record<string, string> = {
  biz: "上周新版本上线后的留存表现 / 经营异常拆解…",
  ab: "v2.3 vs v2.2 留存对比，样本均衡 + 显著性…",
  wave: "周末 GMV 突然下滑，多维下钻定位根因…",
  data: "本月各渠道 ARPU + 同比环比，自动可视化…",
  gray: "v1.5 vs v1.4 灰度版本的核心指标差异…",
  open: "任意目标：跨范式协作 / 多工具编排 / 自由探索…",
};

const PARADIGM_NAME: Record<string, string> = {
  biz: "经营分析",
  ab: "AB 实验",
  wave: "波动分析",
  data: "数据分析",
  gray: "版本灰度",
  open: "开放任务",
};

// 与 Dashboard 快速开始 保持一致：前 4 个已上线，后 3 个待上线
const AGENT_ORDER = [
  "general",
  "data-analysis",
  "ab-experiment",
  "know",
  "gray-release",
  "biz-insight",
  "wave-attribution",
];

function sortAgents(list: AgentCard[]): AgentCard[] {
  return [...list].sort((a, b) => {
    const ia = AGENT_ORDER.indexOf(a.id);
    const ib = AGENT_ORDER.indexOf(b.id);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

export function CreateTaskPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const pushToast = useUIStore((s) => s.pushToast);

  const [step, setStep] = useState<Step>(1);
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);

  const [form, setForm] = useState({
    name: "",
    paradigm: params.get("paradigm") || "biz",
    description: "",
    agent_id: params.get("agentId") || "",
    initial_prompt: "",
    visibility: "private",
    enable_schedule: false,
    cron: "0 9 * * *",
    schedule_prompt: "",
    auto_open: true,
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    agentApi
      .list()
      .then((r) => setAgents(sortAgents(r.items)))
      .catch(() => {})
      .finally(() => setAgentsLoading(false));
  }, []);

  useEffect(() => {
    const tplId = params.get("template");
    if (tplId) {
      templateApi
        .get(tplId)
        .then((t) => applyTemplate(t))
        .catch(() => {});
    }
  }, [params]);

  const filteredAgents = useMemo(
    () => agents.filter((a) => !form.paradigm || a.paradigm === form.paradigm),
    [agents, form.paradigm],
  );

  const applyTemplate = (t: TemplateRecord) => {
    setForm((f) => ({
      ...f,
      paradigm: t.paradigm,
      agent_id: t.agent_id || "",
      initial_prompt: t.initial_prompt || "",
      enable_schedule: t.has_schedule,
      cron: (t.schedule_config as any)?.cron || "0 9 * * *",
      schedule_prompt: (t.schedule_config as any)?.prompt || "",
      name: f.name || t.name,
    }));
    // 从模板或带参进入：跳过 Step 1 的 Agent 选择，直接进入 Step 2 填名字 / Prompt
    setStep(2);
  };

  const pickAgent = (a: AgentCard) => {
    if (a.publish_status === "coming_soon") {
      pushToast("info", `${a.name} 待上线，敬请期待`);
      return;
    }
    setForm((f) => ({ ...f, agent_id: a.id, paradigm: a.paradigm }));
    setStep(2);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      pushToast("warning", "请填写任务名称");
      setStep(2);
      return;
    }
    setCreating(true);
    try {
      const t = await taskApi.create({
        name: form.name.trim(),
        paradigm: form.paradigm,
        agent_id: form.agent_id || null,
        description: form.description || undefined,
        initial_prompt: form.initial_prompt || undefined,
        skill_ids: [],
        visibility: form.visibility,
      });
      if (form.enable_schedule) {
        try {
          await scheduledApi.create(t.id, {
            name: `${form.name} · 定时`,
            cron: form.cron,
            prompt: form.schedule_prompt || form.initial_prompt || "",
          });
        } catch (err) {
          pushToast("warning", `定时配置失败：${(err as Error).message}`);
        }
      }
      pushToast("success", "任务已创建");
      if (form.auto_open) navigate(`/workspace/${t.id}`);
      else navigate("/dashboard");
    } catch (err) {
      const e = err as ApiError;
      pushToast("error", `创建失败：${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="ct-page">
      <TopNav mode="workspace" crumb={<span>首页 / <span className="current">创建任务</span></span>} />

      <main className="ct-main">
        <div className="ct-stepper">
          {[1, 2, 3].map((n) => (
            <div key={n} className={`ct-step ${step === n ? "active" : ""} ${step > n ? "done" : ""}`}>
              <div className="ct-step-num">{step > n ? "✓" : n}</div>
              <div className="ct-step-label">
                {n === 1 ? "选择起点" : n === 2 ? "任务基础" : "高级配置"}
              </div>
            </div>
          ))}
        </div>

        {step === 1 && (
          <section className="ct-section">
            <div className="ct-step1-head">
              <h3 className="ct-step1-title">选择一个 Agent 作为起点</h3>
              <p className="ct-step1-hint">点击即进入下一步；后续可在工作空间里继续增减 Skill</p>
            </div>
            <div className="ct-agent-grid">
              {agentsLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="ct-agent-card ct-agent-card-skel">
                      <Skeleton lines={3} />
                    </div>
                  ))
                : agents.map((a) => {
                    const comingSoon = a.publish_status === "coming_soon";
                    const selected = form.agent_id === a.id;
                    return (
                      <button
                        key={a.id}
                        type="button"
                        className={`ct-agent-card${comingSoon ? " ct-agent-card-soon" : ""}${selected ? " selected" : ""}`}
                        onClick={() => pickAgent(a)}
                        style={{ borderTopColor: a.color }}
                        title={comingSoon ? "待上线，敬请期待" : `以 ${a.name} 作为起点`}
                      >
                        {comingSoon && <span className="ct-agent-badge-soon">待上线</span>}
                        <div
                          className="ct-agent-icon"
                          style={{ background: `${a.color}22`, color: a.color }}
                        >
                          {a.icon}
                        </div>
                        <div className="ct-agent-name">{a.name}</div>
                        <div className="ct-agent-desc">{a.description}</div>
                      </button>
                    );
                  })}
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="ct-section">
            <div className="ct-fields">
              <label className="ct-field">
                <span>任务名称</span>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="例如：Q2 经营复盘 · 渠道归因"
                />
              </label>
              <label className="ct-field">
                <span>范式</span>
                <select
                  value={form.paradigm}
                  onChange={(e) => setForm({ ...form, paradigm: e.target.value })}
                >
                  {Object.entries(PARADIGM_NAME).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label className="ct-field full">
                <span>描述（可选）</span>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="一句话描述任务目标"
                />
              </label>
              <label className="ct-field full">
                <span>💬 初始 Prompt</span>
                <textarea
                  rows={4}
                  value={form.initial_prompt}
                  onChange={(e) => setForm({ ...form, initial_prompt: e.target.value })}
                  placeholder={PARADIGM_PLACEHOLDER[form.paradigm] || "Agent 初始指令…"}
                />
              </label>
            </div>
            <div className="ct-actions">
              <button className="btn-secondary" onClick={() => setStep(1)}>← 上一步</button>
              <button className="btn-primary" onClick={() => setStep(3)}>下一步 →</button>
            </div>
          </section>
        )}

        {step === 3 && (
          <section className="ct-section">
            <details className="ct-fold" open>
              <summary>🤖 Agent</summary>
              <div className="ct-fold-body">
                <label className="ct-field">
                  <span>Agent</span>
                  <select
                    value={form.agent_id}
                    onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
                  >
                    <option value="">系统自动选择</option>
                    {filteredAgents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.icon} {a.name}
                      </option>
                    ))}
                  </select>
                  <small style={{ color: "var(--text-muted)", marginTop: 4 }}>
                    Skill 可在工作空间随时添加 / 移除
                  </small>
                </label>
              </div>
            </details>

            <details className="ct-fold">
              <summary>⏱ 定时执行</summary>
              <div className="ct-fold-body">
                <label className="ct-toggle">
                  <input
                    type="checkbox"
                    checked={form.enable_schedule}
                    onChange={(e) => setForm({ ...form, enable_schedule: e.target.checked })}
                  />
                  启用定时执行
                </label>
                {form.enable_schedule && (
                  <>
                    <label className="ct-field">
                      <span>cron 表达式</span>
                      <input
                        value={form.cron}
                        onChange={(e) => setForm({ ...form, cron: e.target.value })}
                        placeholder="例如 0 9 * * 1-5（工作日早 9 点）"
                      />
                      <small style={{ color: "var(--text-muted)" }}>{cronHint(form.cron)}</small>
                    </label>
                    <div className="ct-cron-presets">
                      {[
                        { label: "每天 09:00", v: "0 9 * * *" },
                        { label: "工作日 09:00", v: "0 9 * * 1-5" },
                        { label: "每周一 09:00", v: "0 9 * * 1" },
                        { label: "每小时", v: "0 * * * *" },
                      ].map((p) => (
                        <button
                          key={p.v}
                          className="btn-ghost"
                          onClick={() => setForm({ ...form, cron: p.v })}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                    <label className="ct-field">
                      <span>定时 Prompt</span>
                      <textarea
                        rows={3}
                        value={form.schedule_prompt}
                        onChange={(e) =>
                          setForm({ ...form, schedule_prompt: e.target.value })
                        }
                        placeholder="留空则使用初始 Prompt"
                      />
                    </label>
                  </>
                )}
              </div>
            </details>

            <details className="ct-fold">
              <summary>🌐 可见性</summary>
              <div className="ct-fold-body">
                <div className="ct-visibility">
                  <label>
                    <input
                      type="radio"
                      checked={form.visibility === "private"}
                      onChange={() => setForm({ ...form, visibility: "private" })}
                    />
                    私有 · 仅我可见
                  </label>
                  <label>
                    <input
                      type="radio"
                      checked={form.visibility === "public"}
                      onChange={() => setForm({ ...form, visibility: "public" })}
                    />
                    公共 · 团队可见（需 admin 审核）
                  </label>
                </div>
              </div>
            </details>

            <div className="ct-confirm">
              <label className="ct-toggle">
                <input
                  type="checkbox"
                  checked={form.auto_open}
                  onChange={(e) => setForm({ ...form, auto_open: e.target.checked })}
                />
                创建后立即打开 Workspace
              </label>
            </div>

            <div className="ct-actions">
              <button className="btn-secondary" onClick={() => setStep(2)}>← 上一步</button>
              <button className="btn-primary" disabled={creating} onClick={submit}>
                {creating ? "创建中…" : "创建任务"}
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function cronHint(expr: string): string {
  const p = expr.trim().split(/\s+/);
  if (p.length !== 5) return "请输入 5 段 cron 表达式";
  const [m, h, dom, mo, dow] = p;
  return `分=${m} 时=${h} 日=${dom} 月=${mo} 周=${dow}`;
}
