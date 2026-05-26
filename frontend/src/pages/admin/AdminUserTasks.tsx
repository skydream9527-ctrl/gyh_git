import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi, agentApi } from "@/api/endpoints";
import type { AdminUser } from "@/api/endpoints";
import type { AgentCard, TaskDetail } from "@/types/api";
import { Skeleton } from "@/components/feedback/Skeleton";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { useBackdropClose } from "@/hooks/useBackdropClose";
import { useUIStore } from "@/stores/uiStore";
import { clickIgnoreSelection } from "@/utils/click";

type EditPatch = Parameters<typeof adminApi.updateTask>[1];

export function AdminUserTasks() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const pushToast = useUIStore((s) => s.pushToast);

  const [user, setUser] = useState<AdminUser | null>(null);
  const [items, setItems] = useState<TaskDetail[]>([]);
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<TaskDetail | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<TaskDetail | null>(null);

  const reload = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const [tasks, userList] = await Promise.all([
        adminApi.listUserTasks(userId, 200),
        adminApi.listUsers(undefined, undefined, undefined),
      ]);
      setItems(tasks.items);
      const u = userList.items.find((x) => x.id === userId) || null;
      setUser(u);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // load agents once for the edit modal
    void agentApi.list().then((r) => setAgents(r.items));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleDelete = async (t: TaskDetail) => {
    try {
      await adminApi.deleteTask(t.id);
      pushToast("success", "已删除任务");
      setConfirmDelete(null);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  return (
    <div>
      <div className="adm-page-head" style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <h1>📋 用户任务管理</h1>
          <p>
            {user ? (
              <>
                用户：<b>{user.name}</b>
                <span style={{ marginLeft: 8, fontFamily: "var(--font-mono)", fontSize: 11 }}>
                  {user.email}
                </span>
                <span className={`role-badge role-${user.auth_role}`} style={{ marginLeft: 8 }}>
                  {user.auth_role}
                </span>
              </>
            ) : (
              <span style={{ color: "var(--text-muted)" }}>用户 ID：{userId}</span>
            )}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-secondary" onClick={() => navigate("/admin/users")}>
            ← 返回用户列表
          </button>
        </div>
      </div>

      {loading ? (
        <Skeleton lines={6} />
      ) : items.length === 0 ? (
        <div className="adm-section" style={{ textAlign: "center", color: "var(--text-muted)" }}>
          该用户暂无任务
        </div>
      ) : (
        <table className="adm-table adm-table-cards">
          <thead>
            <tr>
              <th>任务名</th>
              <th>范式 / Agent</th>
              <th>角色</th>
              <th>可见性</th>
              <th>状态</th>
              <th>更新时间</th>
              <th style={{ width: 240 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id}>
                <td data-label="任务名">
                  <a
                    onClick={clickIgnoreSelection(() => navigate(`/workspace/${t.id}`))}
                    style={{ cursor: "pointer", color: "var(--primary)" }}
                  >
                    {t.name}
                  </a>
                  {t.last_message_preview ? (
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--text-muted)",
                        maxWidth: 320,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {t.last_message_preview}
                    </div>
                  ) : null}
                </td>
                <td data-label="范式 / Agent">
                  <span className="role-badge role-user">{t.paradigm}</span>
                  {t.agent_id && (
                    <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{t.agent_id}</div>
                  )}
                </td>
                <td data-label="角色">{t.role === "owner" ? "所有者" : "协作者"}</td>
                <td data-label="可见性">{t.visibility === "public" ? "🌐 公共" : "🔒 私有"}</td>
                <td data-label="状态">
                  <span className={`adm-status-${t.status}`}>{t.status}</span>
                </td>
                <td data-label="更新时间" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {t.updated_at ? new Date(t.updated_at).toLocaleString() : "-"}
                </td>
                <td className="row-actions">
                  <button onClick={() => navigate(`/workspace/${t.id}`)} title="以管理员身份打开">
                    ▶ 使用
                  </button>
                  <button onClick={() => setEditing(t)}>✏ 编辑</button>
                  <button className="danger" onClick={() => setConfirmDelete(t)}>
                    🗑 删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editing && (
        <TaskEditModal
          task={editing}
          agents={agents}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await reload();
          }}
        />
      )}
      <ConfirmModal
        open={!!confirmDelete}
        title={`确认删除任务「${confirmDelete?.name}」？`}
        body="该任务的对话历史、文件、工具调用都会从磁盘删除，无法恢复。"
        danger
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}

interface EditModalProps {
  task: TaskDetail;
  agents: AgentCard[];
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

function TaskEditModal({ task, agents, onClose, onSaved }: EditModalProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [form, setForm] = useState({
    name: task.name || "",
    description: task.description || "",
    visibility: (task.visibility as "private" | "public") || "private",
    status: (task.status as "active" | "archived") || "active",
    agent_id: task.agent_id || "",
    initial_prompt: task.initial_prompt || "",
  });
  const [saving, setSaving] = useState(false);

  const original = useMemo(
    () => ({
      name: task.name || "",
      description: task.description || "",
      visibility: task.visibility,
      status: task.status,
      agent_id: task.agent_id || "",
      initial_prompt: task.initial_prompt || "",
    }),
    [task],
  );

  const save = async () => {
    if (!form.name.trim()) {
      return pushToast("warning", "任务名不能为空");
    }
    const patch: EditPatch = {};
    if (form.name !== original.name) patch.name = form.name;
    if (form.description !== original.description) patch.description = form.description;
    if (form.visibility !== original.visibility) patch.visibility = form.visibility;
    if (form.status !== original.status) patch.status = form.status;
    if (form.agent_id !== original.agent_id) patch.agent_id = form.agent_id || null;
    if (form.initial_prompt !== original.initial_prompt)
      patch.initial_prompt = form.initial_prompt;
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }
    setSaving(true);
    try {
      await adminApi.updateTask(task.id, patch);
      pushToast("success", "已保存");
      await onSaved();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const backdrop = useBackdropClose(onClose);
  return (
    <div className="cm-overlay" {...backdrop}>
      <div className="cm-card" style={{ minWidth: 560, maxWidth: 720 }}>
        <h3>编辑任务「{task.name}」</h3>
        <div className="cm-body">
          <div className="adm-form-grid">
            <label style={{ gridColumn: "span 2" }}>
              任务名
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              Agent
              <select
                value={form.agent_id}
                onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
              >
                <option value="">— 不绑定 —</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.icon ? `${a.icon} ` : ""}
                    {a.name}（{a.id}）
                  </option>
                ))}
              </select>
            </label>
            <label>
              可见性
              <select
                value={form.visibility}
                onChange={(e) =>
                  setForm({ ...form, visibility: e.target.value as "private" | "public" })
                }
              >
                <option value="private">🔒 私有</option>
                <option value="public">🌐 公共</option>
              </select>
            </label>
            <label>
              状态
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as "active" | "archived" })}
              >
                <option value="active">活跃</option>
                <option value="archived">归档</option>
              </select>
            </label>
            <label style={{ gridColumn: "span 2" }}>
              描述
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                style={{ resize: "vertical" }}
              />
            </label>
            <label style={{ gridColumn: "span 2" }}>
              初始 Prompt（已生效的对话不受影响）
              <textarea
                rows={3}
                value={form.initial_prompt}
                onChange={(e) => setForm({ ...form, initial_prompt: e.target.value })}
                style={{ resize: "vertical", fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
            </label>
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>
            任务 ID：<code>{task.id}</code>
            <span style={{ marginLeft: 12 }}>
              范式：<code>{task.paradigm}</code>
            </span>
          </div>
        </div>
        <div className="cm-actions">
          <button className="btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn-primary" disabled={saving} onClick={save}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
