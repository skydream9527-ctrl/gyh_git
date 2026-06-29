import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "@/api/endpoints";
import type { AdminAgent } from "@/api/endpoints";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useBackdropClose } from "@/hooks/useBackdropClose";
import { useUIStore } from "@/stores/uiStore";

// Seed agents ship with the platform — deleting them would break the seed
// loop, so the UI refuses (and so does the backend as defense-in-depth).
const PROTECTED_IDS = new Set([
  "biz-insight",
  "ab-experiment",
  "wave-attribution",
  "data-analysis",
  "gray-release",
  "know",
]);

export function AdminAgents() {
  const pushToast = useUIStore((s) => s.pushToast);
  const [items, setItems] = useState<AdminAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<AdminAgent | null>(null);
  const [_busy, setBusy] = useState(false);

  const reload = async () => {
    setLoading(true);
    try {
      const r = await adminApi.listAgents();
      setItems(r.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, []);

  const handleDelete = async (force: boolean) => {
    if (!deleting) return;
    setBusy(true);
    try {
      const r = await adminApi.deleteAgent(deleting.id, force);
      if (r.tasks_orphaned > 0) {
        pushToast("success", `已删除（${r.tasks_orphaned} 个历史任务继续用快照）`);
      } else {
        pushToast("success", "已删除");
      }
      setDeleting(null);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="adm-page-head" style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <h1>🤖 Agents</h1>
          <p>系统预置 6 个 Agent；自建 Agent 可随时增删改</p>
        </div>
        <button className="btn-primary" onClick={() => setCreating(true)}>
          + 新建 Agent
        </button>
      </div>
      {loading ? (
        <Skeleton lines={6} />
      ) : (
        <div className="adm-agent-grid">
          {items.map((a) => {
            const isProtected = PROTECTED_IDS.has(a.id);
            return (
              <div key={a.id} className="adm-agent-card" style={{ position: "relative" }}>
                <Link
                  to={`/admin/agents/${a.id}`}
                  style={{
                    display: "block",
                    color: "inherit",
                    textDecoration: "none",
                  }}
                >
                  <div className="adm-agent-icon" style={{ color: a.color }}>
                    {a.icon}
                  </div>
                  <div className="adm-agent-name">{a.name}</div>
                  <div className="adm-agent-paradigm">{a.paradigm}</div>
                  <div className="adm-agent-desc">{a.description}</div>
                  <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>
                    状态：{a.publish_status}
                    {isProtected && (
                      <span style={{ marginLeft: 8, color: "var(--text-muted)" }}>· 预置</span>
                    )}
                  </div>
                </Link>
                {!isProtected && (
                  <button
                    className="danger"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleting(a);
                    }}
                    style={{
                      position: "absolute",
                      top: 8,
                      right: 8,
                      padding: "2px 8px",
                      fontSize: 12,
                    }}
                    title="删除 Agent"
                  >
                    🗑
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {creating && (
        <AgentCreateModal
          existingIds={new Set(items.map((a) => a.id))}
          onClose={() => setCreating(false)}
          onSaved={async () => {
            setCreating(false);
            await reload();
          }}
        />
      )}

      <ConfirmModal
        open={!!deleting}
        title={`确认删除 Agent「${deleting?.name}」？`}
        body={
          "该 Agent 将从目录中移除；已创建的历史任务继续使用各自的 agent 快照。" +
          "若仍被活跃任务引用，后端会拒绝；需要强制删除请在确认后重试并选 force。"
        }
        danger
        onConfirm={() => handleDelete(false)}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}

interface CreateProps {
  existingIds: Set<string>;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

const PARADIGMS = [
  { value: "biz", label: "经营洞察 biz" },
  { value: "ab", label: "实验分析 ab" },
  { value: "wave", label: "波动归因 wave" },
  { value: "data", label: "数据分析 data" },
  { value: "gray", label: "灰度版本 gray" },
  { value: "knowledge", label: "知识库 knowledge" },
  { value: "custom", label: "自定义 custom" },
];

function AgentCreateModal({ existingIds, onClose, onSaved }: CreateProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [form, setForm] = useState({
    id: "",
    name: "",
    paradigm: "custom",
    icon: "🤖",
    color: "var(--primary)",
    description: "",
    system_prompt: "",
    publish_status: "draft",
  });
  const [saving, setSaving] = useState(false);

  const validate = (): string | null => {
    const id = form.id.trim().toLowerCase();
    if (!/^[a-z][a-z0-9-]{2,40}$/.test(id)) {
      return "ID 必须以字母开头，3-40 位，仅允许小写字母 / 数字 / 短横线";
    }
    if (existingIds.has(id)) return `ID \`${id}\` 已存在`;
    if (!form.name.trim()) return "name 不能为空";
    if (!form.paradigm.trim()) return "paradigm 不能为空";
    return null;
  };

  const save = async () => {
    const err = validate();
    if (err) {
      pushToast("warning", err);
      return;
    }
    setSaving(true);
    try {
      await adminApi.createAgent({
        id: form.id.trim().toLowerCase(),
        name: form.name.trim(),
        paradigm: form.paradigm,
        icon: form.icon || "🤖",
        color: form.color || "var(--primary)",
        description: form.description,
        system_prompt: form.system_prompt,
        publish_status: form.publish_status,
      });
      pushToast("success", "已创建");
      await onSaved();
    } catch (e) {
      pushToast("error", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const backdrop = useBackdropClose(onClose);
  return (
    <div className="cm-overlay" {...backdrop}>
      <div className="cm-card" style={{ minWidth: 560, maxWidth: 720 }}>
        <h3>新建 Agent</h3>
        <div className="cm-body">
          <div className="adm-form-grid">
            <label>
              ID
              <input
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value })}
                placeholder="agent-id（小写字母+数字+短横线）"
              />
            </label>
            <label>
              名称
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="显示用的中文名"
              />
            </label>
            <label>
              工作范式
              <select
                value={form.paradigm}
                onChange={(e) => setForm({ ...form, paradigm: e.target.value })}
              >
                {PARADIGMS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              发布状态
              <select
                value={form.publish_status}
                onChange={(e) => setForm({ ...form, publish_status: e.target.value })}
              >
                <option value="draft">草稿 draft</option>
                <option value="published">已发布 published</option>
                <option value="coming_soon">待上线 coming_soon</option>
                <option value="archived">已归档 archived</option>
              </select>
            </label>
            <label>
              图标（emoji）
              <input
                value={form.icon}
                onChange={(e) => setForm({ ...form, icon: e.target.value })}
                placeholder="🤖"
              />
            </label>
            <label>
              主题色
              <input
                type="color"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
              />
            </label>
            <label style={{ gridColumn: "span 2" }}>
              描述
              <input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="一句话描述用途"
              />
            </label>
            <label style={{ gridColumn: "span 2" }}>
              system prompt（可稍后在编辑页完善）
              <textarea
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                rows={6}
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                placeholder="你是一名……"
              />
            </label>
          </div>
        </div>
        <div className="cm-actions">
          <button className="btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn-primary" disabled={saving} onClick={save}>
            {saving ? "创建中…" : "创建"}
          </button>
        </div>
      </div>
    </div>
  );
}
