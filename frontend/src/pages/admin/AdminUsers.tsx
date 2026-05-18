import { useEffect, useState } from "react";
import { adminApi } from "@/api/endpoints";
import type { AdminUser } from "@/api/endpoints";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

export function AdminUsers() {
  const me = useAuthStore((s) => s.user);
  const isSuper = me?.auth_role === "super_admin";
  const pushToast = useUIStore((s) => s.pushToast);

  const [items, setItems] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [role, setRole] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<AdminUser | null>(null);
  const [rejecting, setRejecting] = useState<AdminUser | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);

  const reload = async () => {
    setLoading(true);
    try {
      const r = await adminApi.listUsers(
        q || undefined,
        role || undefined,
        statusFilter || undefined,
      );
      setItems(r.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, statusFilter]);

  const pendingCount = items.filter((u) => u.status === "pending").length;

  const handleDelete = async (u: AdminUser) => {
    try {
      await adminApi.deleteUser(u.id);
      pushToast("success", "已删除");
      setConfirmDelete(null);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    }
  };

  const handleApprove = async (u: AdminUser) => {
    setReviewBusy(u.id);
    try {
      await adminApi.reviewRegistration(u.id, "approved");
      pushToast("success", `已批准 ${u.name}，该账号可以登录`);
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setReviewBusy(null);
    }
  };

  const handleReject = async () => {
    if (!rejecting) return;
    setReviewBusy(rejecting.id);
    try {
      await adminApi.reviewRegistration(rejecting.id, "rejected", rejectReason || undefined);
      pushToast("success", `已驳回 ${rejecting.name}`);
      setRejecting(null);
      setRejectReason("");
      await reload();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setReviewBusy(null);
    }
  };

  return (
    <div>
      <div className="adm-page-head" style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <h1>👥 用户管理</h1>
          <p>三级角色：super_admin / admin / user</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          + 创建用户
        </button>
      </div>

      <div className="adm-toolbar">
        <input
          placeholder="🔍 搜索姓名 / 邮箱"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && reload()}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">全部角色</option>
          <option value="super_admin">super_admin</option>
          <option value="admin">admin</option>
          <option value="user">user</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">全部状态</option>
          <option value="pending">
            {pendingCount > 0 && statusFilter === "pending" ? `待审批（${pendingCount}）` : "待审批"}
          </option>
          <option value="active">已启用</option>
          <option value="rejected">已驳回</option>
          <option value="disabled">已禁用</option>
        </select>
        <button className="btn-secondary" onClick={reload}>
          搜索
        </button>
        {pendingCount > 0 && statusFilter !== "pending" && (
          <button
            className="btn-secondary"
            onClick={() => setStatusFilter("pending")}
            style={{ background: "#fef3c7", borderColor: "#fbbf24", color: "#92400e" }}
          >
            🕓 {pendingCount} 条账号申请待审批
          </button>
        )}
      </div>

      {loading ? (
        <Skeleton lines={6} />
      ) : (
        <table className="adm-table">
          <thead>
            <tr>
              <th>姓名</th>
              <th>邮箱</th>
              <th>角色</th>
              <th>飞书</th>
              <th>状态</th>
              <th>团队</th>
              <th>注册时间</th>
              <th style={{ width: 220 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{u.email}</td>
                <td>
                  <span className={`role-badge role-${u.auth_role}`}>{u.auth_role}</span>
                </td>
                <td>{u.feishu_bound ? "✅" : "—"}</td>
                <td>
                  <span
                    className={`adm-status-${u.status}`}
                    title={u.status === "rejected" && u.reject_reason ? u.reject_reason : undefined}
                  >
                    {u.status === "active"
                      ? "启用"
                      : u.status === "pending"
                      ? "🕓 待审批"
                      : u.status === "rejected"
                      ? "❌ 已驳回"
                      : "禁用"}
                  </span>
                </td>
                <td>{u.team || "-"}</td>
                <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                </td>
                <td className="row-actions">
                  {u.status === "pending" ? (
                    <>
                      <button
                        className="btn-primary"
                        disabled={reviewBusy === u.id}
                        onClick={() => handleApprove(u)}
                      >
                        ✓ 批准
                      </button>
                      <button
                        className="danger"
                        disabled={reviewBusy === u.id}
                        onClick={() => {
                          setRejecting(u);
                          setRejectReason("");
                        }}
                      >
                        ✕ 驳回
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => setEditing(u)}>✏ 编辑</button>
                      {u.status === "rejected" && (
                        <button
                          disabled={reviewBusy === u.id}
                          onClick={() => handleApprove(u)}
                          title="已驳回的账号可重新批准"
                        >
                          ✓ 批准
                        </button>
                      )}
                      {isSuper && u.id !== me?.id && (
                        <button className="danger" onClick={() => setConfirmDelete(u)}>
                          🗑 删除
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                  没有匹配的用户
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {(showCreate || editing) && (
        <UserModal
          existing={editing}
          isSuper={isSuper}
          selfId={me?.id}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
          onSaved={async () => {
            setShowCreate(false);
            setEditing(null);
            await reload();
          }}
        />
      )}
      <ConfirmModal
        open={!!confirmDelete}
        title={`确认删除用户 ${confirmDelete?.name}？`}
        body="该用户的所有任务、文件、对话历史都将被删除（仅清理 cache 索引；磁盘文件保留以便恢复）。"
        danger
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
        onCancel={() => setConfirmDelete(null)}
      />

      {rejecting && (
        <div
          className="cm-overlay"
          onClick={() => {
            setRejecting(null);
            setRejectReason("");
          }}
        >
          <div className="cm-card" style={{ minWidth: 440 }} onClick={(e) => e.stopPropagation()}>
            <h3>驳回账号申请</h3>
            <div className="cm-body">
              <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 10 }}>
                驳回 <b>{rejecting.name}</b>（{rejecting.email}）的注册申请。
                可选：填写原因——用户登录失败时会看到。
              </p>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="驳回原因（可选）"
                rows={3}
                style={{ width: "100%", fontSize: 13, padding: 8, resize: "vertical" }}
              />
            </div>
            <div className="cm-actions">
              <button
                className="btn-secondary"
                onClick={() => {
                  setRejecting(null);
                  setRejectReason("");
                }}
              >
                取消
              </button>
              <button
                className="danger"
                disabled={reviewBusy === rejecting.id}
                onClick={handleReject}
              >
                {reviewBusy === rejecting.id ? "处理中…" : "确认驳回"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface ModalProps {
  existing: AdminUser | null;
  isSuper: boolean;
  selfId?: string;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}

function UserModal({ existing, isSuper, selfId, onClose, onSaved }: ModalProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [form, setForm] = useState({
    email: existing?.email || "",
    name: existing?.name || "",
    auth_role: existing?.auth_role || "user",
    team: existing?.team || "",
    title: existing?.title || "",
    status: existing?.status || "active",
    password: "",
  });
  const [saving, setSaving] = useState(false);
  const isSelf = existing?.id === selfId;

  const save = async () => {
    if (!form.email || !form.name) {
      return pushToast("warning", "请填写邮箱和姓名");
    }
    setSaving(true);
    try {
      if (existing) {
        const patch: any = {
          name: form.name,
          team: form.team,
          title: form.title,
          status: form.status,
        };
        if (isSuper && form.auth_role !== existing.auth_role) {
          patch.auth_role = form.auth_role;
        }
        if (form.password) patch.password = form.password;
        await adminApi.updateUser(existing.id, patch);
      } else {
        await adminApi.createUser(form);
      }
      pushToast("success", "已保存");
      await onSaved();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="cm-overlay" onClick={onClose}>
      <div className="cm-card" style={{ minWidth: 520 }} onClick={(e) => e.stopPropagation()}>
        <h3>{existing ? "编辑用户" : "创建用户"}</h3>
        <div className="cm-body">
          <div className="adm-form-grid">
            <label>
              邮箱 / 用户名
              <input
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                disabled={!!existing}
              />
            </label>
            <label>
              姓名
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              角色
              {isSuper ? (
                <select
                  value={form.auth_role}
                  onChange={(e) => setForm({ ...form, auth_role: e.target.value as any })}
                  disabled={isSelf && form.auth_role === "super_admin"}
                >
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                  <option value="super_admin">super_admin</option>
                </select>
              ) : (
                <input value={form.auth_role} disabled />
              )}
            </label>
            <label>
              状态
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as any })}
              >
                <option value="active">启用</option>
                <option value="disabled">禁用</option>
              </select>
            </label>
            <label>
              团队
              <input value={form.team} onChange={(e) => setForm({ ...form, team: e.target.value })} />
            </label>
            <label>
              职务
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </label>
            <label style={{ gridColumn: "span 2" }}>
              {existing ? "重置密码（留空不改）" : "初始密码（留空则仅飞书登录）"}
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </label>
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
