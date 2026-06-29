import { useCallback, useEffect, useMemo, useState } from "react";
import { diagnosticsApi } from "@/api/endpoints";
import type {
  DiagEventRecord,
  DiagLevel,
  DiagTaskEntry,
  DiagTimelineRow,
} from "@/api/endpoints";
import { Skeleton } from "@/components/feedback/Skeleton";

type Mode = "by-task" | "by-request";

const LEVEL_BADGE: Record<DiagLevel, string> = {
  INFO: "var(--text-muted)",
  WARN: "var(--warning)",
  ERROR: "var(--error)",
};

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function copyToClipboard(text: string) {
  if (!text) return;
  void navigator.clipboard?.writeText(text).catch(() => {});
}

export function AdminDiagnostics() {
  const [mode, setMode] = useState<Mode>("by-task");

  // by-task / by-conv 模式
  const [taskList, setTaskList] = useState<DiagTaskEntry[]>([]);
  const [taskListLoading, setTaskListLoading] = useState(true);
  const [taskId, setTaskId] = useState("");
  const [convId, setConvId] = useState("");
  const [filterLevel, setFilterLevel] = useState<DiagLevel | "">("");
  const [filterSource, setFilterSource] = useState("");
  const [filterEvent, setFilterEvent] = useState("");
  const [events, setEvents] = useState<DiagEventRecord[]>([]);
  const [timeline, setTimeline] = useState<DiagTimelineRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<DiagEventRecord | DiagTimelineRow | null>(
    null,
  );
  const [showTimeline, setShowTimeline] = useState(false);

  // by-request 模式
  const [reqId, setReqId] = useState("");
  const [reqRows, setReqRows] = useState<DiagTimelineRow[]>([]);
  const [reqLoading, setReqLoading] = useState(false);

  // 初始化加载有事件的任务列表
  useEffect(() => {
    diagnosticsApi
      .taskList(50)
      .then((r) => setTaskList(r.items))
      .catch((e) => setError(e?.message || "加载任务列表失败"))
      .finally(() => setTaskListLoading(false));
  }, []);

  const loadEvents = useCallback(async () => {
    if (!taskId.trim()) {
      setEvents([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const r = await diagnosticsApi.events({
        task_id: taskId.trim(),
        conv_id: convId.trim() || undefined,
        level: filterLevel || undefined,
        source: filterSource.trim() || undefined,
        event_type: filterEvent.trim() || undefined,
        limit: 500,
      });
      setEvents(r.items);
    } catch (e) {
      setError((e as Error)?.message || "加载事件失败");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [taskId, convId, filterLevel, filterSource, filterEvent]);

  const loadTimeline = useCallback(async () => {
    if (!taskId.trim() || !convId.trim()) {
      setTimeline([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const r = await diagnosticsApi.timeline(taskId.trim(), convId.trim(), 500);
      setTimeline(r.items);
    } catch (e) {
      setError((e as Error)?.message || "加载时间轴失败");
      setTimeline([]);
    } finally {
      setLoading(false);
    }
  }, [taskId, convId]);

  const lookupRequest = useCallback(async () => {
    if (!reqId.trim()) return;
    setReqLoading(true);
    setError(null);
    try {
      const r = await diagnosticsApi.byRequest(reqId.trim(), 200);
      setReqRows(r.items);
    } catch (e) {
      setError((e as Error)?.message || "请求查询失败");
      setReqRows([]);
    } finally {
      setReqLoading(false);
    }
  }, [reqId]);

  // 仅在 task / conv 切换时自动刷新；filterLevel/filterSource/filterEvent 是
  // 自由输入，留给「查询」按钮触发，避免每按一个键打一次后端。
  useEffect(() => {
    if (mode === "by-task" && !showTimeline && taskId.trim()) {
      void loadEvents();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, showTimeline, taskId, convId]);

  useEffect(() => {
    if (mode === "by-task" && showTimeline) {
      void loadTimeline();
    }
  }, [mode, showTimeline, loadTimeline]);

  const sources = useMemo(() => {
    const set = new Set<string>();
    events.forEach((e) => set.add(e.source));
    return Array.from(set).sort();
  }, [events]);

  return (
    <div>
      <div className="adm-page-head">
        <h1>🩺 任务诊断 · 日志</h1>
        <p>
          按任务 / 会话 / 请求 ID 查看运维事件流。事件落在
          <code style={codeInline}>tasks/&lt;tid&gt;/events/&lt;YYYY-MM&gt;.jsonl</code>
          ，与 conversation / tool_calls 共用一条时间轴。
        </p>
      </div>

      <div style={tabBar}>
        <button
          className={mode === "by-task" ? "btn-primary" : "btn-secondary"}
          onClick={() => setMode("by-task")}
          style={tabBtn}
        >
          按任务 / 会话
        </button>
        <button
          className={mode === "by-request" ? "btn-primary" : "btn-secondary"}
          onClick={() => setMode("by-request")}
          style={tabBtn}
        >
          按 Request ID
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: 10,
            margin: "10px 0",
            borderRadius: 4,
            background: "rgba(220,38,38,0.08)",
            color: "var(--error)",
            fontSize: 12,
          }}
        >
          {error}
        </div>
      )}

      {mode === "by-task" ? (
        <>
          <div style={toolbar}>
            <input
              placeholder="task_id"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              style={inputCss}
            />
            <input
              placeholder="conv_id（可选）"
              value={convId}
              onChange={(e) => setConvId(e.target.value)}
              style={inputCss}
            />
            <select
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value as DiagLevel | "")}
              style={inputCss}
            >
              <option value="">全部级别</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
            </select>
            <input
              placeholder="source（如 ws / agent_runtime）"
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              style={inputCss}
            />
            <input
              placeholder="event_type"
              value={filterEvent}
              onChange={(e) => setFilterEvent(e.target.value)}
              style={inputCss}
            />
            <button
              className="btn-primary"
              onClick={() => (showTimeline ? loadTimeline() : loadEvents())}
              disabled={!taskId.trim()}
              style={{ padding: "6px 14px", fontSize: 12 }}
            >
              查询
            </button>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontSize: 12,
                color: "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showTimeline}
                onChange={(e) => setShowTimeline(e.target.checked)}
                disabled={!taskId.trim() || !convId.trim()}
              />
              合并消息 / 工具调用（需要 conv_id）
            </label>
          </div>

          {!taskId.trim() ? (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  marginBottom: 6,
                }}
              >
                最近有事件的任务（点击载入）
              </div>
              {taskListLoading ? (
                <Skeleton lines={4} />
              ) : taskList.length === 0 ? (
                <div style={emptyHint}>暂无任务事件</div>
              ) : (
                <div className="adm-audit-log">
                  {taskList.map((t) => (
                    <div
                      key={t.task_id}
                      className="adm-audit-row"
                      style={{ cursor: "pointer", padding: "8px 10px" }}
                      onClick={() => setTaskId(t.task_id)}
                    >
                      <div
                        style={{
                          display: "flex",
                          gap: 12,
                          alignItems: "center",
                          fontSize: 12,
                        }}
                      >
                        <span style={{ color: "var(--text-muted)", minWidth: 160 }}>
                          {fmtTs(t.last_event_at)}
                        </span>
                        <span style={{ fontFamily: "var(--font-mono)" }}>
                          {t.task_id.slice(0, 12)}…
                        </span>
                        <span style={{ flex: 1 }}>{t.task_name || "（未命名）"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : loading ? (
            <Skeleton lines={6} />
          ) : showTimeline ? (
            <TimelineList rows={timeline} onSelect={setActive} />
          ) : (
            <EventList rows={events} sources={sources} onSelect={setActive} />
          )}
        </>
      ) : (
        <>
          <div style={toolbar}>
            <input
              placeholder="request_id（如 a1b2c3d4 或 ws-...）"
              value={reqId}
              onChange={(e) => setReqId(e.target.value)}
              style={{ ...inputCss, minWidth: 280 }}
            />
            <button
              className="btn-primary"
              onClick={() => void lookupRequest()}
              disabled={!reqId.trim()}
              style={{ padding: "6px 14px", fontSize: 12 }}
            >
              查询
            </button>
          </div>
          {reqLoading ? (
            <Skeleton lines={4} />
          ) : reqRows.length === 0 ? (
            <div style={emptyHint}>
              输入 request_id 后查询；当前月内匹配的事件会列出来
            </div>
          ) : (
            <TimelineList rows={reqRows} onSelect={setActive} />
          )}
        </>
      )}

      {active && (
        <div
          onClick={() => setActive(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--surface-1)",
              padding: 16,
              maxWidth: 880,
              maxHeight: "80vh",
              overflow: "auto",
              borderRadius: 6,
              minWidth: 480,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <h3 style={{ margin: 0, fontSize: 14 }}>事件详情</h3>
              <button
                className="btn-ghost"
                style={{ padding: "2px 10px" }}
                onClick={() => setActive(null)}
              >
                关闭
              </button>
            </div>
            <pre
              style={{
                background: "var(--surface-2)",
                padding: 10,
                margin: 0,
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                borderRadius: 4,
                overflow: "auto",
              }}
            >
              {JSON.stringify(active, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

function EventList({
  rows,
  sources,
  onSelect,
}: {
  rows: DiagEventRecord[];
  sources: string[];
  onSelect: (r: DiagEventRecord) => void;
}) {
  if (rows.length === 0) {
    return <div style={emptyHint}>无匹配事件</div>;
  }
  return (
    <>
      <div
        style={{
          fontSize: 11,
          color: "var(--text-muted)",
          margin: "8px 0",
        }}
      >
        共 {rows.length} 条 · sources: {sources.join(", ") || "—"}
      </div>
      <div className="adm-audit-log">
        {rows.map((r, i) => (
          <div
            key={`${r.ts}-${i}`}
            className="adm-audit-row"
            style={{ cursor: "pointer", padding: "8px 10px" }}
            onClick={() => onSelect(r)}
          >
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                fontSize: 12,
                flexWrap: "wrap",
              }}
            >
              <span
                style={{ color: LEVEL_BADGE[r.level], fontWeight: 600, minWidth: 50 }}
              >
                {r.level}
              </span>
              <span style={{ color: "var(--text-muted)", minWidth: 170 }}>
                {fmtTs(r.ts)}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-muted)",
                  minWidth: 90,
                }}
              >
                {r.source}
              </span>
              <span style={{ minWidth: 160, fontWeight: 500 }}>{r.event_type}</span>
              {r.code && (
                <span style={{ ...badge, color: "var(--error)" }}>{r.code}</span>
              )}
              {r.request_id && (
                <span
                  style={{ ...badge, cursor: "copy" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    copyToClipboard(r.request_id || "");
                  }}
                  title="点击复制 request_id"
                >
                  rid:{r.request_id.slice(0, 8)}
                </span>
              )}
              <span style={{ flex: 1, minWidth: 200 }}>{r.message}</span>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function TimelineList({
  rows,
  onSelect,
}: {
  rows: DiagTimelineRow[];
  onSelect: (r: DiagTimelineRow) => void;
}) {
  if (rows.length === 0) {
    return <div style={emptyHint}>无匹配记录</div>;
  }
  return (
    <div className="adm-audit-log">
      {rows.map((r, i) => {
        const lvl = (r.level as DiagLevel | undefined) || undefined;
        const color = lvl ? LEVEL_BADGE[lvl] : "var(--text-muted)";
        const kindLabel =
          r.kind === "event"
            ? "EVT"
            : r.kind === "message"
            ? r.role === "user"
              ? "USR"
              : "AST"
            : "TOL";
        return (
          <div
            key={`${r.ts}-${i}`}
            className="adm-audit-row"
            style={{ cursor: "pointer", padding: "8px 10px" }}
            onClick={() => onSelect(r)}
          >
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                fontSize: 12,
                flexWrap: "wrap",
              }}
            >
              <span style={{ color, fontWeight: 600, minWidth: 40 }}>
                {kindLabel}
              </span>
              <span style={{ color: "var(--text-muted)", minWidth: 170 }}>
                {fmtTs(r.ts)}
              </span>
              {r.source && (
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-muted)",
                    minWidth: 90,
                  }}
                >
                  {r.source}
                </span>
              )}
              {r.event_type && (
                <span style={{ minWidth: 160, fontWeight: 500 }}>
                  {r.event_type}
                </span>
              )}
              {r.code && (
                <span style={{ ...badge, color: "var(--error)" }}>{r.code}</span>
              )}
              {r.task_id && (
                <span style={{ ...badge }}>{r.task_id.slice(0, 8)}</span>
              )}
              <span style={{ flex: 1, minWidth: 200 }}>{r.summary}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

const codeInline: React.CSSProperties = {
  background: "var(--surface-2)",
  padding: "1px 6px",
  borderRadius: 3,
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  margin: "0 4px",
};

const tabBar: React.CSSProperties = {
  display: "flex",
  gap: 6,
  marginBottom: 12,
};
const tabBtn: React.CSSProperties = { padding: "6px 14px", fontSize: 12 };

const toolbar: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
  alignItems: "center",
  margin: "10px 0",
};
const inputCss: React.CSSProperties = {
  background: "var(--surface-2)",
  border: "1px solid var(--border-1)",
  borderRadius: 4,
  padding: "6px 10px",
  fontSize: 12,
  minWidth: 160,
  color: "inherit",
};
const badge: React.CSSProperties = {
  background: "var(--surface-2)",
  padding: "1px 6px",
  borderRadius: 3,
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  color: "var(--text-muted)",
};
const emptyHint: React.CSSProperties = {
  padding: 24,
  textAlign: "center",
  color: "var(--text-muted)",
  fontSize: 12,
};
