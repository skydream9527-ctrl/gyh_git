import { useEffect, useMemo, useState } from "react";
import type { TodoItem } from "@/hooks/useChatSocket";
import "./TodoPanel.css";

interface TodoPanelProps {
  taskId: string;
  items: TodoItem[];
  updatedAt: string | null;
}

function formatRelative(iso: string | null): string {
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

function statusIcon(status: TodoItem["status"]): string {
  if (status === "completed") return "✓";
  if (status === "in_progress") return "◐";
  return "○";
}

/** Shows the agent's self-maintained todo list for this task. Populates from
 * REST on first mount (so a page refresh restores state), then keeps updating
 * in place as `todos_updated` WS events arrive. */
function TodoPanel({ taskId, items, updatedAt }: TodoPanelProps) {
  const [seedItems, setSeedItems] = useState<TodoItem[]>([]);
  const [seedAt, setSeedAt] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/todos`, {
          credentials: "include",
        });
        const j = await r.json();
        if (alive && j && j.data) {
          setSeedItems(Array.isArray(j.data.items) ? j.data.items : []);
          setSeedAt(j.data.updated_at || null);
        }
      } catch {
        /* silent — first render with no data is fine */
      } finally {
        if (alive) setLoaded(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, [taskId]);

  // WS items take precedence once we've seen at least one update, otherwise
  // fall back to the REST snapshot.
  const list = items.length > 0 ? items : seedItems;
  const stamp = updatedAt || seedAt;

  const counts = useMemo(() => {
    const c = { pending: 0, in_progress: 0, completed: 0 };
    for (const it of list) c[it.status] += 1;
    return c;
  }, [list]);

  if (!loaded) {
    return (
      <div className="todo-panel">
        <div className="todo-panel__header">待办跟踪</div>
        <div className="todo-panel__empty">加载中…</div>
      </div>
    );
  }

  if (list.length === 0) {
    return (
      <div className="todo-panel">
        <div className="todo-panel__header">待办跟踪</div>
        <div className="todo-panel__empty">
          Agent 会在多步任务中主动维护一份 todo 列表。触发条件：用户请求 ≥ 3 个步骤时。
        </div>
      </div>
    );
  }

  return (
    <div className="todo-panel">
      <div className="todo-panel__header">
        <span>待办跟踪</span>
        <span className="meta">
          {counts.completed}/{list.length} 已完成 · {formatRelative(stamp)}
        </span>
      </div>
      <div className="todo-panel__list">
        {list.map((it) => (
          <div key={it.id} className={`todo-panel__item ${it.status}`}>
            <span className="todo-panel__icon">{statusIcon(it.status)}</span>
            <span className="todo-panel__text">
              {it.status === "in_progress" ? it.activeForm || it.content : it.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TodoPanel;
