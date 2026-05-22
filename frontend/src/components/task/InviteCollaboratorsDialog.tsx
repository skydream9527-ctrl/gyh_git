import { useEffect, useMemo, useRef, useState } from "react";
import http, { api } from "@/api/client";
import { invitationApi } from "@/api/endpoints";
import type { TaskInvite } from "@/api/endpoints";
import { useUIStore } from "@/stores/uiStore";
import "./InviteCollaboratorsDialog.css";

interface UserHit {
  id: string;
  name: string;
  email: string;
  auth_role: string;
}

export interface InviteCollaboratorsDialogProps {
  open: boolean;
  taskId: string;
  taskName?: string;
  onClose: () => void;
}

/**
 * 任务协作邀请：搜索用户 → 多选 → 写留言 → 提交。
 * 同时下方展示当前任务"待响应 / 已接受 / 已拒绝 / 已撤回"的邀请；owner 可撤回 pending。
 */
export function InviteCollaboratorsDialog({
  open,
  taskId,
  taskName,
  onClose,
}: InviteCollaboratorsDialogProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<UserHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [picked, setPicked] = useState<UserHit[]>([]);
  const [role, setRole] = useState<"viewer" | "editor" | "owner">("editor");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [invites, setInvites] = useState<TaskInvite[]>([]);
  const [loadingInvites, setLoadingInvites] = useState(false);
  const debounceRef = useRef<number | null>(null);

  const reset = () => {
    setQuery("");
    setHits([]);
    setPicked([]);
    setMessage("");
    setRole("editor");
    setSubmitting(false);
  };

  useEffect(() => {
    if (!open) {
      reset();
      return;
    }
    void loadInvites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId]);

  // ESC 关闭
  useEffect(() => {
    if (!open) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, submitting, onClose]);

  // 防抖搜索
  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setHits([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = window.setTimeout(async () => {
      try {
        const r = await api<{ items: UserHit[]; total: number }>(
          http.get("/users/search", { params: { q: query.trim() } }),
        );
        setHits(r.items);
      } catch {
        setHits([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [query, open]);

  const loadInvites = async () => {
    setLoadingInvites(true);
    try {
      const r = await invitationApi.list(taskId);
      setInvites(r.items);
    } catch (err) {
      // 静默：列表非关键路径
    } finally {
      setLoadingInvites(false);
    }
  };

  const pickedIds = useMemo(() => new Set(picked.map((p) => p.id)), [picked]);
  const pendingIds = useMemo(
    () => new Set(invites.filter((i) => i.status === "pending").map((i) => i.invitee_id)),
    [invites],
  );

  const togglePick = (u: UserHit) => {
    if (pickedIds.has(u.id)) {
      setPicked((arr) => arr.filter((x) => x.id !== u.id));
    } else {
      setPicked((arr) => [...arr, u]);
    }
  };
  const removePick = (id: string) => {
    setPicked((arr) => arr.filter((x) => x.id !== id));
  };

  const submit = async () => {
    if (picked.length === 0) {
      pushToast("warning", "请至少选择一个被邀请人");
      return;
    }
    setSubmitting(true);
    try {
      const r = await invitationApi.create(taskId, {
        invitee_ids: picked.map((p) => p.id),
        role,
        message: message.trim(),
      });
      const okCount = r.created.length;
      const skippedCount = r.skipped.length;
      if (okCount > 0) {
        pushToast(
          "success",
          `已邀请 ${okCount} 人${skippedCount > 0 ? `（跳过 ${skippedCount}）` : ""}`,
        );
      }
      if (skippedCount > 0 && okCount === 0) {
        pushToast(
          "info",
          r.skipped.map((s) => s.reason).join("、") || "没有可邀请的成员",
        );
      }
      // 刷新已发送列表，清空选择
      await loadInvites();
      setPicked([]);
      setQuery("");
      setHits([]);
      setMessage("");
    } catch (err) {
      pushToast("error", (err as Error).message || "邀请失败");
    } finally {
      setSubmitting(false);
    }
  };

  const cancel = async (inv: TaskInvite) => {
    try {
      await invitationApi.cancel(taskId, inv.id);
      pushToast("success", "已撤回邀请");
      await loadInvites();
    } catch (err) {
      pushToast("error", (err as Error).message || "撤回失败");
    }
  };

  if (!open) return null;
  return (
    <div className="inv-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="inv-title"
      >
        <div className="inv-head">
          <h3 id="inv-title">邀请协作{taskName ? ` · ${taskName}` : ""}</h3>
          <button className="inv-close" onClick={onClose} aria-label="关闭" disabled={submitting}>
            ×
          </button>
        </div>

        <div className="inv-body">
          <div className="inv-field">
            <label>搜索用户</label>
            <input
              className="inv-input"
              placeholder="按姓名 / 邮箱搜索"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            {query.trim() && (
              <div className="inv-hits">
                {searching && <div className="inv-empty">搜索中…</div>}
                {!searching && hits.length === 0 && (
                  <div className="inv-empty">没有匹配的用户</div>
                )}
                {!searching &&
                  hits.map((u) => {
                    const isPicked = pickedIds.has(u.id);
                    const isPending = pendingIds.has(u.id);
                    return (
                      <button
                        key={u.id}
                        type="button"
                        className={`inv-hit${isPicked ? " is-picked" : ""}${
                          isPending ? " is-pending" : ""
                        }`}
                        onClick={() => !isPending && togglePick(u)}
                        disabled={isPending}
                        title={isPending ? "已邀请，待处理" : ""}
                      >
                        <span className="inv-hit-avatar">{u.name?.[0] || "U"}</span>
                        <span className="inv-hit-main">
                          <span className="inv-hit-name">{u.name}</span>
                          <span className="inv-hit-mail">{u.email}</span>
                        </span>
                        <span className="inv-hit-flag">
                          {isPending ? "已邀请" : isPicked ? "✓" : "+"}
                        </span>
                      </button>
                    );
                  })}
              </div>
            )}
          </div>

          {picked.length > 0 && (
            <div className="inv-field">
              <label>已选 {picked.length} 人</label>
              <div className="inv-picked">
                {picked.map((p) => (
                  <span key={p.id} className="inv-chip">
                    {p.name}
                    <button
                      type="button"
                      className="inv-chip-x"
                      onClick={() => removePick(p.id)}
                      aria-label={`移除 ${p.name}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="inv-row">
            <div className="inv-field inv-field-role">
              <label>权限</label>
              <select value={role} onChange={(e) => setRole(e.target.value as any)}>
                <option value="editor">编辑（可发消息、改文件）</option>
                <option value="viewer">只看（只读）</option>
                <option value="owner">所有者（含删除任务、调整协作者）</option>
              </select>
            </div>
            <div className="inv-field inv-field-msg">
              <label>留言（可选）</label>
              <textarea
                className="inv-input"
                rows={2}
                placeholder="给被邀请人留几句话"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={500}
              />
            </div>
          </div>
        </div>

        <div className="inv-actions">
          <button className="btn-secondary" onClick={onClose} disabled={submitting}>
            取消
          </button>
          <button
            className="btn-primary"
            onClick={submit}
            disabled={submitting || picked.length === 0}
          >
            {submitting ? "邀请中…" : `发出邀请 (${picked.length})`}
          </button>
        </div>

        {/* 已发出的邀请 */}
        <div className="inv-list-section">
          <div className="inv-list-head">
            <span>已发邀请</span>
            <button
              type="button"
              className="btn-ghost"
              onClick={loadInvites}
              disabled={loadingInvites}
              title="刷新"
            >
              ↻
            </button>
          </div>
          {loadingInvites ? (
            <div className="inv-empty">加载中…</div>
          ) : invites.length === 0 ? (
            <div className="inv-empty">还没有发过邀请</div>
          ) : (
            <ul className="inv-list">
              {invites.map((inv) => (
                <li key={inv.id} className={`inv-row-item inv-status-${inv.status}`}>
                  <div className="inv-row-main">
                    <div className="inv-row-name">{inv.invitee_name}</div>
                    <div className="inv-row-meta">
                      <span className={`inv-status inv-status-pill-${inv.status}`}>
                        {STATUS_TEXT[inv.status]}
                      </span>
                      <span>·</span>
                      <span>
                        {inv.role === "owner"
                          ? "所有者"
                          : inv.role === "editor"
                            ? "编辑"
                            : "只看"}
                      </span>
                      <span>·</span>
                      <span>{formatRelative(inv.created_at)}</span>
                    </div>
                  </div>
                  {inv.status === "pending" && (
                    <button
                      type="button"
                      className="btn-ghost inv-row-cancel"
                      onClick={() => cancel(inv)}
                      title="撤回邀请"
                    >
                      撤回
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

const STATUS_TEXT: Record<TaskInvite["status"], string> = {
  pending: "待响应",
  accepted: "已接受",
  declined: "已拒绝",
  cancelled: "已撤回",
};

function formatRelative(iso?: string): string {
  if (!iso) return "";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "";
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "刚刚";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} 天前`;
  return new Date(iso).toLocaleDateString();
}

export default InviteCollaboratorsDialog;
