import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { conversationApi } from "@/api/endpoints";
import { ConfirmModal } from "@/components/feedback/ConfirmModal";
import { useUIStore } from "@/stores/uiStore";
import type { ConversationSummary } from "@/types/api";
import "./ConversationTab.css";

export interface ConversationTabProps {
  taskId: string;
  currentConvId: string | null;
  onSelect: (convId: string) => void;
  canWrite: boolean;
  reloadKey?: number;
  /** 列表加载/轮询完成后回调；父组件用它推导「当前 conv 是否还在后台生成」 */
  onItemsLoaded?: (items: ConversationSummary[]) => void;
}

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

function extractErrMsg(err: unknown, fallback: string): string {
  const e = err as { response?: { data?: { message?: string; error_code?: string } } };
  return e?.response?.data?.message || fallback;
}

function ConversationTab({
  taskId,
  currentConvId,
  onSelect,
  canWrite,
  reloadKey,
  onItemsLoaded,
}: ConversationTabProps) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 内联新建：展开输入框替代 window.prompt
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  // 内联重命名：点 ✎ 把对应 li 切到编辑态
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  // 删除确认弹窗：替代 window.confirm
  const [confirmDelete, setConfirmDelete] = useState<ConversationSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const newInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    if (!taskId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await conversationApi.list(taskId);
      const sorted = [...res.items].sort((a, b) => {
        const ta = new Date(a.last_message_at).getTime() || 0;
        const tb = new Date(b.last_message_at).getTime() || 0;
        return tb - ta;
      });
      setItems(sorted);
      onItemsLoaded?.(sorted);
    } catch (err: unknown) {
      setError(extractErrMsg(err, "加载对话失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, reloadKey]);

  // 任意 conv 处于 inflight（后台还在跑回复）时，每 5s 轮询一次拉刷新——
  // 切走对话后，仅靠 reloadKey 不会再 bump（finalized 不变），但用户希望能
  // 看到「⏳ 后台正在生成」实时变化以及完成后的最终消息数。
  const hasInflight = items.some((c) => c.inflight);
  useEffect(() => {
    if (!hasInflight) return;
    const t = window.setInterval(() => {
      load();
    }, 5000);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasInflight, taskId]);

  useEffect(() => {
    if (creating) newInputRef.current?.focus();
  }, [creating]);

  useEffect(() => {
    if (renamingId) renameInputRef.current?.select();
  }, [renamingId]);

  const startCreate = () => {
    setNewTitle("");
    setCreating(true);
  };
  const cancelCreate = () => {
    setCreating(false);
    setNewTitle("");
  };
  const submitCreate = async () => {
    const title = newTitle.trim() || "新对话";
    try {
      const created = await conversationApi.create(taskId, title);
      setItems((arr) => [created, ...arr]);
      onSelect(created.id);
      setCreating(false);
      setNewTitle("");
    } catch (err: unknown) {
      pushToast("error", extractErrMsg(err, "创建对话失败"));
    }
  };
  const onCreateKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitCreate();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelCreate();
    }
  };

  const startRename = (conv: ConversationSummary) => {
    setRenamingId(conv.id);
    setRenameValue(conv.title);
  };
  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue("");
  };
  const submitRename = async (conv: ConversationSummary) => {
    const title = renameValue.trim();
    if (!title || title === conv.title) {
      cancelRename();
      return;
    }
    try {
      const updated = await conversationApi.rename(taskId, conv.id, title);
      setItems((arr) => arr.map((c) => (c.id === conv.id ? updated : c)));
      cancelRename();
    } catch (err: unknown) {
      pushToast("error", extractErrMsg(err, "重命名失败"));
    }
  };
  const onRenameKey = (e: KeyboardEvent<HTMLInputElement>, conv: ConversationSummary) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitRename(conv);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelRename();
    }
  };

  const requestDelete = (conv: ConversationSummary) => setConfirmDelete(conv);
  const performDelete = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      await conversationApi.remove(taskId, confirmDelete.id);
      setItems((arr) => arr.filter((c) => c.id !== confirmDelete.id));
      setConfirmDelete(null);
    } catch (err: unknown) {
      pushToast("error", extractErrMsg(err, "删除失败"));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="conv-tab">
      <div className="conv-tab-head">
        <span className="conv-tab-title">对话</span>
        {canWrite && !creating && (
          <button type="button" className="conv-tab-new" onClick={startCreate}>
            + 新对话
          </button>
        )}
      </div>

      {creating && (
        <div className="conv-create-row">
          <input
            ref={newInputRef}
            className="conv-inline-input"
            placeholder="新对话标题（留空用默认）"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={onCreateKey}
            onBlur={() => {
              // 失焦不立刻关闭，留给 ✕ / Enter / Esc 决定
            }}
            maxLength={80}
          />
          <button type="button" className="conv-inline-confirm" onClick={submitCreate}>
            创建
          </button>
          <button type="button" className="conv-inline-cancel" onClick={cancelCreate}>
            取消
          </button>
        </div>
      )}

      {loading && <div className="conv-tab-loading">加载中…</div>}
      {error && <div className="conv-tab-error">{error}</div>}

      {!loading && !error && items.length === 0 && !creating && (
        <div className="conv-tab-empty">暂无对话，点击新建开始</div>
      )}

      <ul className="conv-list">
        {items.map((c) => {
          const active = c.id === currentConvId;
          const isRenaming = renamingId === c.id;
          return (
            <li
              key={c.id}
              className={`conv-item${active ? " is-active" : ""}`}
              onClick={() => {
                if (!isRenaming) onSelect(c.id);
              }}
            >
              <div className="conv-item-main">
                {isRenaming ? (
                  <input
                    ref={renameInputRef}
                    className="conv-inline-input conv-inline-rename"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => onRenameKey(e, c)}
                    onClick={(e) => e.stopPropagation()}
                    onBlur={() => submitRename(c)}
                    maxLength={80}
                  />
                ) : (
                  <div className="conv-item-title" title={c.title}>
                    {c.inflight && (
                      <span
                        className="conv-inflight-badge"
                        title="后台正在生成回复"
                        aria-label="后台正在生成回复"
                      >
                        ⏳
                      </span>
                    )}
                    {c.title || "未命名对话"}
                  </div>
                )}
                <div className="conv-item-meta">
                  <span>{formatRelative(c.last_message_at)}</span>
                  <span className="conv-dot">·</span>
                  <span>{c.message_count} 条</span>
                  {c.created_by_name && (
                    <>
                      <span className="conv-dot">·</span>
                      <span
                        className="conv-item-creator"
                        title={`由 ${c.created_by_name} 创建`}
                      >
                        👤 {c.created_by_name}
                      </span>
                    </>
                  )}
                </div>
              </div>
              {canWrite && !isRenaming && (
                <div className="conv-item-actions">
                  <button
                    type="button"
                    className="conv-icon-btn"
                    title="重命名"
                    onClick={(e) => {
                      e.stopPropagation();
                      startRename(c);
                    }}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    className="conv-icon-btn conv-icon-danger"
                    title="删除"
                    onClick={(e) => {
                      e.stopPropagation();
                      requestDelete(c);
                    }}
                  >
                    🗑
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <ConfirmModal
        open={!!confirmDelete}
        title="删除对话"
        body={
          confirmDelete && (
            <>
              确定删除对话 <strong>{confirmDelete.title || "未命名对话"}</strong>？此操作不可撤销。
            </>
          )
        }
        confirmText={deleting ? "删除中…" : "删除"}
        cancelText="取消"
        danger
        onConfirm={performDelete}
        onCancel={() => !deleting && setConfirmDelete(null)}
      />
    </div>
  );
}

export default ConversationTab;
