import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { invitationApi } from "@/api/endpoints";
import type { MyInviteEntry } from "@/api/endpoints";
import { useUIStore } from "@/stores/uiStore";
import "./InviteInbox.css";

/**
 * 顶部右侧的邀请收件箱：未读数 badge + 弹层 + accept / decline。
 * 每 60s 轻量轮询一次，保证不打断用户但能及时看到新邀请。
 */
export function InviteInbox() {
  const pushToast = useUIStore((s) => s.pushToast);
  const navigate = useNavigate();
  const [items, setItems] = useState<MyInviteEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [declineFor, setDeclineFor] = useState<string | null>(null);
  const [declineReason, setDeclineReason] = useState("");
  const popRef = useRef<HTMLDivElement>(null);

  const load = async () => {
    try {
      const r = await invitationApi.mine();
      setItems(r.items);
    } catch {
      // 静默：未登录 / 网络抖动不打扰
    }
  };

  useEffect(() => {
    void load();
    const t = window.setInterval(load, 60000);
    return () => window.clearInterval(t);
  }, []);

  // 点外部关闭
  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) {
        setOpen(false);
        setDeclineFor(null);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const accept = async (inv: MyInviteEntry) => {
    setBusyId(inv.invite_id);
    try {
      await invitationApi.accept(inv.invite_id);
      pushToast("success", `已接受「${inv.task_name}」邀请`);
      setItems((arr) => arr.filter((x) => x.invite_id !== inv.invite_id));
      navigate(`/workspace/${inv.task_id}`);
      setOpen(false);
    } catch (err) {
      pushToast("error", (err as Error).message || "接受失败");
    } finally {
      setBusyId(null);
    }
  };

  const decline = async (inv: MyInviteEntry, reason?: string) => {
    setBusyId(inv.invite_id);
    try {
      await invitationApi.decline(inv.invite_id, reason);
      pushToast("info", `已拒绝「${inv.task_name}」邀请`);
      setItems((arr) => arr.filter((x) => x.invite_id !== inv.invite_id));
      setDeclineFor(null);
      setDeclineReason("");
    } catch (err) {
      pushToast("error", (err as Error).message || "拒绝失败");
    } finally {
      setBusyId(null);
    }
  };

  const count = items.length;

  return (
    <div className="ii-wrap" ref={popRef}>
      <button
        className="icon-btn ii-btn"
        onClick={() => {
          setOpen((v) => !v);
          if (!open) void load();
        }}
        aria-label={`协作邀请${count ? ` (${count})` : ""}`}
        title={count ? `${count} 条待处理协作邀请` : "暂无协作邀请"}
      >
        📨
        {count > 0 && <span className="ii-badge">{count > 99 ? "99+" : count}</span>}
      </button>
      {open && (
        <div className="ii-pop" role="menu">
          <div className="ii-head">
            <span>协作邀请</span>
            <button className="ii-refresh" onClick={load} title="刷新">
              ↻
            </button>
          </div>
          {items.length === 0 ? (
            <div className="ii-empty">暂无待处理邀请</div>
          ) : (
            <ul className="ii-list">
              {items.map((inv) => {
                const isDeclining = declineFor === inv.invite_id;
                const busy = busyId === inv.invite_id;
                return (
                  <li key={inv.invite_id} className="ii-item">
                    <div className="ii-item-head">
                      <span className="ii-from">
                        <span className="ii-avatar">{inv.inviter_name?.[0] || "U"}</span>
                        <span className="ii-from-name">{inv.inviter_name}</span>
                      </span>
                      <span className="ii-role">
                        {inv.role === "owner"
                          ? "所有者"
                          : inv.role === "editor"
                            ? "编辑"
                            : "只看"}
                      </span>
                    </div>
                    <div className="ii-task">
                      邀请你协作「<strong>{inv.task_name}</strong>」
                    </div>
                    {inv.message && <div className="ii-msg">{inv.message}</div>}
                    {!isDeclining ? (
                      <div className="ii-actions">
                        <button
                          className="btn-primary ii-act-accept"
                          onClick={() => accept(inv)}
                          disabled={busy}
                        >
                          {busy ? "…" : "✓ 接受"}
                        </button>
                        <button
                          className="btn-secondary ii-act-decline"
                          onClick={() => setDeclineFor(inv.invite_id)}
                          disabled={busy}
                        >
                          拒绝
                        </button>
                      </div>
                    ) : (
                      <div className="ii-decline-row">
                        <input
                          type="text"
                          className="ii-input"
                          placeholder="拒绝理由（可留空）"
                          value={declineReason}
                          onChange={(e) => setDeclineReason(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") decline(inv, declineReason.trim());
                            else if (e.key === "Escape") setDeclineFor(null);
                          }}
                          autoFocus
                          maxLength={200}
                          disabled={busy}
                        />
                        <button
                          className="btn-primary ii-act-decline-confirm"
                          onClick={() => decline(inv, declineReason.trim())}
                          disabled={busy}
                        >
                          {busy ? "…" : "确认拒绝"}
                        </button>
                        <button
                          className="btn-ghost"
                          onClick={() => setDeclineFor(null)}
                          disabled={busy}
                        >
                          取消
                        </button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
