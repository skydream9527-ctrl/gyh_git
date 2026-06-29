import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi } from "@/api/endpoints";
import type { AdminAgent, AdminAgentFeatures, AgentPromptSnapshot } from "@/api/endpoints";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useUIStore } from "@/stores/uiStore";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRendererCore";

const TABS = [
  { k: "basic", label: "基础" },
  { k: "skills", label: "Skills 绑定" },
  { k: "test", label: "🧪 测试对话" },
  { k: "history", label: "经验 / 记忆 / 日志" },
] as const;

type TabKey = (typeof TABS)[number]["k"];

export function AdminAgentEdit() {
  const { agentId = "" } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const pushToast = useUIStore((s) => s.pushToast);
  const [tab, setTab] = useState<TabKey>("basic");
  const [agent, setAgent] = useState<AdminAgent | null>(null);
  const [history, setHistory] = useState<AgentPromptSnapshot[]>([]);
  const [form, setForm] = useState({
    name: "",
    description: "",
    icon: "",
    color: "",
    publish_status: "published",
    system_prompt: "",
    change_note: "",
  });
  // Three-state: true (force on) / false (force off) / null (inherit env)
  const [features, setFeatures] = useState<{
    [K in keyof AdminAgentFeatures]: boolean | null;
  }>({
    spawn_subagent: null,
    run_background: null,
    todo_write: null,
    exit_plan_mode: null,
  });
  const [saving, setSaving] = useState(false);
  const [confirmSave, setConfirmSave] = useState(false);
  const [testInput, setTestInput] = useState("");
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [testRunning, setTestRunning] = useState(false);

  const reload = async () => {
    const a = await adminApi.getAgent(agentId);
    setAgent(a);
    setForm({
      name: a.name,
      description: a.description || "",
      icon: a.icon,
      color: a.color,
      publish_status: a.publish_status || "published",
      system_prompt: a.system_prompt || "",
      change_note: "",
    });
    const f = a.features || {};
    setFeatures({
      spawn_subagent: f.spawn_subagent ?? null,
      run_background: f.run_background ?? null,
      todo_write: f.todo_write ?? null,
      exit_plan_mode: f.exit_plan_mode ?? null,
    });
    const h = await adminApi.promptHistory(agentId);
    setHistory(h.items);
  };

  useEffect(() => {
    reload().catch((e) => pushToast("error", (e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  const save = async () => {
    setSaving(true);
    try {
      // Strip null entries — backend treats absent keys as "no override".
      const featPayload: AdminAgentFeatures = {};
      (Object.keys(features) as (keyof AdminAgentFeatures)[]).forEach((k) => {
        const v = features[k];
        if (v !== null && v !== undefined) featPayload[k] = v;
      });
      await adminApi.updateAgent(agentId, {
        name: form.name,
        description: form.description,
        icon: form.icon,
        color: form.color,
        publish_status: form.publish_status,
        system_prompt: form.system_prompt,
        features: featPayload,
        change_note: form.change_note || undefined,
      });
      pushToast("success", "已保存");
      setForm((f) => ({ ...f, change_note: "" }));
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSaving(false);
      setConfirmSave(false);
    }
  };

  const rollback = async (snap: AgentPromptSnapshot) => {
    try {
      await adminApi.promptRollback(agentId, snap.id);
      pushToast("success", `已回滚到 ${new Date(snap.saved_at).toLocaleString()}`);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const testRun = async () => {
    if (!testInput.trim()) return;
    setTestRunning(true);
    setTestOutput(null);
    try {
      const r = await adminApi.testChat(agentId, {
        content: testInput,
        system_prompt: form.system_prompt,
      });
      setTestOutput(r.response);
    } catch (err) {
      const e = err as { errorCode?: string; message: string };
      setTestOutput(`[${e.errorCode || "ERROR"}] ${e.message}`);
    } finally {
      setTestRunning(false);
    }
  };

  if (!agent) {
    return (
      <div>
        <Skeleton lines={6} />
      </div>
    );
  }

  return (
    <div>
      <div className="adm-page-head" style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <h1>
            {form.icon} {agent.name}
          </h1>
          <p>系统预置 · {agent.paradigm} 范式 · {agent.publish_status}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-secondary" onClick={() => navigate("/admin/agents")}>
            ← 返回
          </button>
          <button className="btn-primary" disabled={saving} onClick={() => setConfirmSave(true)}>
            💾 保存
          </button>
        </div>
      </div>

      <div className="adm-edit-tabs">
        {TABS.map((t) => (
          <button
            key={t.k}
            type="button"
            className={`adm-edit-tab ${tab === t.k ? "active" : ""}`}
            onClick={() => setTab(t.k)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "basic" && (
        <div className="adm-section">
          <div className="adm-form-grid">
            <label>
              名称
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              发布状态
              <select
                value={form.publish_status}
                onChange={(e) => setForm({ ...form, publish_status: e.target.value })}
              >
                <option value="published">published</option>
                <option value="draft">draft</option>
              </select>
            </label>
            <label style={{ gridColumn: "span 2" }}>
              描述
              <input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </label>
            <label>
              Icon
              <input value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })} />
            </label>
            <label>
              Color
              <input value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </label>
          </div>
          <h3 style={{ fontFamily: "var(--font-head)", fontSize: 14, margin: "22px 0 10px" }}>
            🛠 Runtime 能力开关
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: 12, margin: "0 0 10px" }}>
            「继承全局」= 跟随 .env 的 ICE_*_ENABLED；强制开 / 关 = 仅对本 Agent 生效，
            优先级高于全局开关。
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: 12,
            }}
          >
            {(
              [
                { key: "spawn_subagent", label: "spawn_subagent（派子 agent）", env: "ICE_SUBAGENT_ENABLED" },
                { key: "run_background", label: "run_background（后台任务）", env: "ICE_BG_TASK_ENABLED" },
                { key: "todo_write", label: "todo_write（自维护待办）", env: "ICE_TODO_ENABLED" },
                { key: "exit_plan_mode", label: "exit_plan_mode（计划模式）", env: "ICE_PLAN_MODE_ENABLED" },
              ] as { key: keyof AdminAgentFeatures; label: string; env: string }[]
            ).map((f) => {
              const cur = features[f.key];
              const value = cur === true ? "on" : cur === false ? "off" : "inherit";
              return (
                <label
                  key={f.key}
                  style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}
                >
                  <span>{f.label}</span>
                  <select
                    value={value}
                    onChange={(e) => {
                      const v = e.target.value;
                      setFeatures((prev) => ({
                        ...prev,
                        [f.key]: v === "on" ? true : v === "off" ? false : null,
                      }));
                    }}
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                      padding: "5px 8px",
                      borderRadius: 4,
                    }}
                  >
                    <option value="inherit">继承全局（{f.env}）</option>
                    <option value="on">强制开启</option>
                    <option value="off">强制关闭</option>
                  </select>
                </label>
              );
            })}
          </div>
          <h3 style={{ fontFamily: "var(--font-head)", fontSize: 14, margin: "22px 0 10px" }}>
            System Prompt
          </h3>
          <textarea
            rows={14}
            value={form.system_prompt}
            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            style={{
              width: "100%",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
              padding: 14,
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              outline: "none",
              resize: "vertical",
            }}
          />
          <input
            placeholder="变更说明（推荐填写）"
            value={form.change_note}
            onChange={(e) => setForm({ ...form, change_note: e.target.value })}
            style={{
              width: "100%",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text)",
              padding: "8px 12px",
              fontSize: 12,
              outline: "none",
              marginTop: 10,
            }}
          />
        </div>
      )}

      {tab === "skills" && (
        <div className="adm-section">
          <p style={{ color: "var(--text-dim)" }}>
            MVP 阶段：所有 Agent 默认绑定 3 个内置 Skills（now / echo / kyuubi_query）。后续 session 实现细粒度绑定 UI。
          </p>
        </div>
      )}

      {tab === "test" && (
        <div className="adm-section">
          <div className="adm-split-view">
            {/* Left: editable prompt */}
            <div className="adm-split-left">
              <h3 className="adm-split-heading">
                📝 System Prompt（实时编辑）
              </h3>
              <textarea
                className="adm-split-prompt-editor"
                rows={18}
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                placeholder="在此编辑 system prompt，右侧测试将实时使用最新内容…"
              />
              <div className="adm-split-prompt-meta">
                <span>{form.system_prompt.length} 字符</span>
                <button
                  className="btn-secondary"
                  style={{ fontSize: 11, padding: "3px 10px" }}
                  onClick={() => setConfirmSave(true)}
                  disabled={saving}
                >
                  💾 保存到 Agent
                </button>
              </div>
            </div>

            {/* Right: sandbox conversation */}
            <div className="adm-split-right">
              <h3 className="adm-split-heading">
                🧪 沙盒对话（使用左侧 Prompt，不入库 / 不计费）
              </h3>
              <div className="adm-sandbox-chat">
                {testOutput !== null && (
                  <div className="adm-sandbox-response">
                    <MarkdownRenderer content={testOutput} />
                  </div>
                )}
                {testRunning && (
                  <div className="adm-sandbox-loading">思考中…</div>
                )}
              </div>
              <div className="adm-sandbox-input-row">
                <input
                  type="text"
                  className="adm-sandbox-input"
                  placeholder="输入测试消息…"
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                      e.preventDefault();
                      testRun();
                    }
                  }}
                  disabled={testRunning}
                />
                <button className="btn-primary" disabled={testRunning || !testInput.trim()} onClick={testRun}>
                  {testRunning ? "…" : "▶"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="adm-section">
          <h3 style={{ fontFamily: "var(--font-head)", fontSize: 14, marginTop: 0 }}>
            📜 Prompt 版本历史（{history.length} 个版本）
          </h3>
          {history.length === 0 ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 24 }}>
              暂无历史记录
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {history.map((h) => (
                <details
                  key={h.id}
                  style={{
                    background: "var(--surface-2)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    padding: 0,
                  }}
                >
                  <summary
                    style={{
                      padding: "8px 12px",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      fontSize: 12,
                    }}
                  >
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", minWidth: 160 }}>
                      {new Date(h.saved_at).toLocaleString()}
                    </span>
                    <span style={{ flex: 1, color: "var(--text-dim)" }}>
                      {h.saved_by_name || h.saved_by} · {h.change_note || "(无说明)"}
                    </span>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        rollback(h);
                      }}
                      style={{
                        background: "transparent",
                        border: "1px solid var(--border)",
                        color: "var(--text-dim)",
                        padding: "3px 9px",
                        borderRadius: 4,
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      ↩ 回滚
                    </button>
                  </summary>
                  <pre
                    style={{
                      borderTop: "1px solid var(--border)",
                      margin: 0,
                      padding: 10,
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {h.system_prompt}
                  </pre>
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      <ConfirmModal
        open={confirmSave}
        title="确认保存配置？"
        body="修改 Prompt 会影响所有进行中的对话；旧版本会自动归档到版本历史。"
        confirmText="确认保存"
        onConfirm={save}
        onCancel={() => setConfirmSave(false)}
      />
    </div>
  );
}
