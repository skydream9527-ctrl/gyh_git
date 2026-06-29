import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { adminApi } from "@/api/endpoints";
import type { AdminUser } from "@/api/endpoints";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { Skeleton } from "@/components/feedback/Skeleton";
import { useBackdropClose } from "@/hooks/useBackdropClose";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

export function AdminUsers() {
  const me = useAuthStore((s) => s.user);
  const isSuper = me?.auth_role === "super_admin";
  const pushToast = useUIStore((s) => s.pushToast);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [items, setItems] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [role, setRole] = useState<string>("");
  // 从 URL ?status=pending 进入时（概览页"立即审批"入口），默认筛选待审批列表
  const [statusFilter, setStatusFilter] = useState<string>(
    searchParams.get("status") || "",
  );
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<AdminUser | null>(null);
  const [rejecting, setRejecting] = useState<AdminUser | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const rejectBackdrop = useBackdropClose(() => {
    setRejecting(null);
    setRejectReason("");
  }, !!rejecting);
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

  // 审批通过/驳回后跳回 /admin/users（清掉 ?status=pending 与本地筛选），
  // 让管理员看到完整用户列表，包含刚处理的这一条。
  const goBackToUserList = () => {
    setStatusFilter("");
    navigate("/admin/users", { replace: true });
  };

  const handleApprove = async (u: AdminUser) => {
    setReviewBusy(u.id);
    try {
      await adminApi.reviewRegistration(u.id, "approved");
      pushToast("success", `已批准 ${u.name}，该账号可以登录`);
      goBackToUserList();
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
      goBackToUserList();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setReviewBusy(null);
    }
  };

  return (
    <>
      <header className="v6-page-header">
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "8px" }}>用户管理 (Users)</h1>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <div style={{ position: "relative" }}>
            <i className="ph ph-magnifying-glass" style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }}></i>
            <input
              type="text"
              placeholder="搜索邮箱 / 姓名..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && reload()}
              style={{
                padding: "8px 16px 8px 36px", border: "1px solid var(--border-strong)", borderRadius: "8px", fontSize: "14px", outline: "none", width: "256px", boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)"
              }}
            />
          </div>
          {isSuper && (
            <button
              onClick={() => setShowCreate(true)}
              style={{
                background: "var(--primary)", color: "var(--primary-on)", padding: "8px 16px", borderRadius: "8px", fontSize: "14px", fontWeight: 700, border: "none", cursor: "pointer", boxShadow: "0 1px 2px 0 var(--primary-glow)", display: "flex", alignItems: "center", gap: "8px"
              }}
            >
              <i className="ph-bold ph-plus"></i> 新建用户
            </button>
          )}
        </div>
      </header>

      <div className="v6-page-content">
        <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
          <button
            onClick={() => { setStatusFilter(""); setRole(""); reload(); }}
            style={{
              padding: "6px 16px", borderRadius: "999px", fontSize: "14px", fontWeight: 700,
              background: statusFilter === "" && role === "" ? "var(--text)" : "var(--surface)",
              color: statusFilter === "" && role === "" ? "var(--surface)" : "var(--text-dim)",
              border: statusFilter === "" && role === "" ? "none" : "1px solid var(--border)",
              cursor: "pointer"
            }}
          >
            全部 (All)
          </button>
          <button
            onClick={() => { setStatusFilter("pending"); setRole(""); reload(); }}
            style={{
              padding: "6px 16px", borderRadius: "999px", fontSize: "14px", fontWeight: 700,
              background: statusFilter === "pending" ? "var(--text)" : "var(--surface)",
              color: statusFilter === "pending" ? "var(--surface)" : "var(--text-dim)",
              border: statusFilter === "pending" ? "none" : "1px solid var(--border)",
              cursor: "pointer", display: "flex", alignItems: "center", gap: "4px"
            }}
          >
            待审批
            {pendingCount > 0 && (
               <span style={{ background: "var(--error)", color: "var(--primary-on)", fontSize: "10px", padding: "0 6px", borderRadius: "99px" }}>
                 {pendingCount}
               </span>
            )}
          </button>
          <button
            onClick={() => { setRole("super_admin"); setStatusFilter(""); reload(); }}
            style={{
              padding: "6px 16px", borderRadius: "999px", fontSize: "14px", fontWeight: 700,
              background: role === "super_admin" ? "var(--text)" : "var(--surface)",
              color: role === "super_admin" ? "var(--surface)" : "var(--text-dim)",
              border: role === "super_admin" ? "none" : "1px solid var(--border)",
              cursor: "pointer"
            }}
          >
            Super Admins
          </button>
        </div>

        <div className="v6-card" style={{ padding: 0, overflow: "hidden" }}>
          {loading ? (
            <div style={{ padding: 24 }}><Skeleton lines={6} /></div>
          ) : (
            <table style={{ width: "100%", textAlign: "left", fontSize: "14px", borderCollapse: "collapse" }}>
              <thead style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textTransform: "uppercase", fontSize: "12px", fontWeight: 700, letterSpacing: "0.05em" }}>
                <tr>
                  <th style={{ padding: "16px 24px" }}>用户信息</th>
                  <th style={{ padding: "16px 24px" }}>角色权限</th>
                  <th style={{ padding: "16px 24px" }}>状态</th>
                  <th style={{ padding: "16px 24px" }}>飞书绑定</th>
                  <th style={{ padding: "16px 24px", textAlign: "right" }}>操作</th>
                </tr>
              </thead>
              <tbody style={{ color: "var(--text-dim)" }}>
                {items.map((u) => {
                  const isPending = u.status === "pending";
                  const isMe = u.id === me?.id;
                  return (
                    <tr 
                      key={u.id} 
                      style={{ 
                        borderBottom: "1px solid var(--surface-2)", 
                        background: isPending ? "rgba(254, 242, 242, 0.5)" : "var(--surface)",
                        transition: "background 0.2s"
                      }}
                    >
                      <td style={{ padding: "16px 24px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div style={{ width: "32px", height: "32px", borderRadius: "16px", background: isPending ? "var(--error)" : "var(--info)", color: "var(--primary-on)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "14px" }}>
                            {u.name?.[0]?.toUpperCase() || u.email[0].toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: "4px" }}>
                              {u.email}
                              {isMe && <span style={{ background: "var(--warning-soft)", color: "var(--warning)", fontSize: "10px", padding: "2px 4px", borderRadius: "4px" }}>You</span>}
                            </div>
                            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{u.name || "未设置姓名"} {u.team && `· ${u.team}`}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: "16px 24px" }}>
                        {u.auth_role === "super_admin" ? (
                          <span style={{ background: "var(--warning-soft)", color: "var(--warning)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, border: "1px solid var(--warning-soft)" }}>Super Admin</span>
                        ) : u.auth_role === "admin" ? (
                          <span style={{ background: "var(--p-gray-soft)", color: "var(--p-gray)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, border: "1px solid var(--p-gray-soft)" }}>Admin</span>
                        ) : (
                          <span style={{ background: "var(--surface-2)", color: "var(--text-dim)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, border: "1px solid var(--border)" }}>User</span>
                        )}
                      </td>
                      <td style={{ padding: "16px 24px" }}>
                        {isPending ? (
                          <span style={{ background: "var(--error-soft)", color: "var(--error)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, border: "1px solid var(--error-soft)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                            <i className="ph-bold ph-clock"></i> 待审批 (Pending)
                          </span>
                        ) : u.status === "active" ? (
                          <span style={{ background: "var(--success-soft)", color: "var(--success)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, border: "1px solid var(--success-soft)" }}>已激活 (Active)</span>
                        ) : (
                          <span style={{ background: "var(--surface-2)", color: "var(--text-muted)", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 700 }} title={u.reject_reason || ""}>{u.status}</span>
                        )}
                      </td>
                      <td style={{ padding: "16px 24px" }}>
                        {u.feishu_bound ? (
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--success)", fontSize: "12px", fontWeight: 700, background: "var(--success-soft)", padding: "4px 8px", borderRadius: "4px", border: "1px solid var(--success-soft)" }}>
                            <i className="ph-fill ph-check-circle"></i> 已绑定
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: "12px", fontWeight: 700 }}>未绑定</span>
                        )}
                      </td>
                      <td style={{ padding: "16px 24px", textAlign: "right" }}>
                        {isPending && isSuper ? (
                          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                            <button disabled={reviewBusy === u.id} onClick={() => { setRejecting(u); setRejectReason(""); }} style={{ background: "var(--surface)", border: "1px solid var(--error-soft)", color: "var(--error)", padding: "6px 12px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}>拒绝</button>
                            <button disabled={reviewBusy === u.id} onClick={() => handleApprove(u)} style={{ background: "var(--success)", border: "none", color: "var(--primary-on)", padding: "6px 12px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, cursor: "pointer", boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)" }}>通过 (Approve)</button>
                          </div>
                        ) : (
                          <div style={{ display: "flex", gap: "4px", justifyContent: "flex-end" }}>
                            {(isSuper || isMe) && (
                              <button onClick={() => setEditing(u)} title="编辑" style={{ background: "transparent", border: "none", color: "var(--text-muted)", padding: "6px", borderRadius: "4px", cursor: "pointer", fontSize: "18px" }} onMouseOver={e => {e.currentTarget.style.color="var(--primary)"; e.currentTarget.style.background="var(--primary-dim)"}} onMouseOut={e => {e.currentTarget.style.color="var(--text-muted)"; e.currentTarget.style.background="transparent"}}><i className="ph-bold ph-pencil-simple"></i></button>
                            )}
                            {isSuper && !isMe && (
                              <button onClick={() => setConfirmDelete(u)} title="删除" style={{ background: "transparent", border: "none", color: "var(--text-muted)", padding: "6px", borderRadius: "4px", cursor: "pointer", fontSize: "18px" }} onMouseOver={e => {e.currentTarget.style.color="var(--error)"; e.currentTarget.style.background="var(--error-soft)"}} onMouseOut={e => {e.currentTarget.style.color="var(--text-muted)"; e.currentTarget.style.background="transparent"}}><i className="ph-bold ph-trash"></i></button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                      无匹配数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

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
        <div className="cm-overlay" {...rejectBackdrop}>
          <div className="cm-card" style={{ minWidth: 440 }}>
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
    </>
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

  const backdrop = useBackdropClose(onClose);
  return (
    <div className="cm-overlay" {...backdrop}>
      <div className="cm-card" style={{ minWidth: 520 }}>
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
