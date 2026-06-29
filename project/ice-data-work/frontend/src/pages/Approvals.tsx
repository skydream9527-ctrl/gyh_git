import { useEffect } from "react";
import { useGovernanceStore } from "@/stores/governanceStore";

const RESULT_PILL: Record<string, string> = {
  ok: "green",
  blocked: "red",
  error: "red",
  pending: "amber",
};

const RESULT_LABEL: Record<string, string> = {
  ok: "Done",
  blocked: "Blocked",
  error: "Error",
  pending: "Pending",
};

export default function Approvals() {
  const {
    approvals, audit, control,
    fetchApprovals, fetchAudit, fetchControl, decide, pauseAll, resumeAll,
  } = useGovernanceStore();

  useEffect(() => {
    fetchApprovals();
    fetchAudit();
    fetchControl();
  }, [fetchApprovals, fetchAudit, fetchControl]);

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="eyebrow">Approvals &amp; Audit</div>
          <h1>高风险动作进确认队列；所有执行可追溯</h1>
          <p className="subtle">Twin 可请求，但最终确认权在你。审计用于复盘、回滚、权限优化、成本控制。</p>
        </div>
        {control.global_paused ? (
          <button className="btn-primary" onClick={resumeAll}>恢复全部执行</button>
        ) : (
          <button className="btn-danger" onClick={pauseAll}>一键暂停全部执行</button>
        )}
      </div>

      {control.global_paused && (
        <div className="card err">⏸ 全部执行已暂停{control.paused_by ? `（由 ${control.paused_by}）` : ""}。新回合将被拒绝，直到恢复。</div>
      )}

      <div className="wb-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {/* 待我确认 */}
        <div className="card">
          <div className="card-head">
            <h3>待我确认</h3>
            <span className="pill amber">{approvals.length} Pending</span>
          </div>
          <div className="wb-list">
            {approvals.length === 0 && <div className="lane-empty">没有待确认事项</div>}
            {approvals.map((a) => (
              <div className="wb-item" key={a.id}>
                <div className="wb-item-main">
                  <strong>{a.summary || a.action_type}</strong>
                  <span className="task-meta">
                    {a.task_title ? `${a.task_title} · ` : ""}风险：{a.risk_level}
                  </span>
                </div>
                <div className="task-actions">
                  <button className="btn-sm primary" onClick={() => decide(a.task_id!, a.id, true)}>确认</button>
                  <button className="btn-sm" onClick={() => decide(a.task_id!, a.id, false)}>拒绝</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 权限日志 / 工具调用 */}
        <div className="card">
          <div className="card-head">
            <h3>权限日志 / 工具调用</h3>
            <span className="pill blue">Audit</span>
          </div>
          <div className="wb-list">
            {audit.length === 0 && <div className="lane-empty">暂无审计记录</div>}
            {audit.slice(0, 20).map((e) => (
              <div className="wb-item compact" key={e.id}>
                <div className="wb-item-main">
                  <strong>{e.tool || e.action} · {e.actor}</strong>
                  <span className="task-meta">{e.summary}{e.task_title ? ` · ${e.task_title}` : ""}</span>
                </div>
                <span className={`pill ${RESULT_PILL[e.result] || "slate"}`}>
                  {RESULT_LABEL[e.result] || e.result}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 失败复盘 */}
      <div className="card" style={{ maxWidth: 1100, margin: "16px auto 0" }}>
        <div className="card-head">
          <h3>失败复盘</h3>
          <span className="pill slate">Structured</span>
        </div>
        <div className="wb-list">
          {audit.filter((e) => e.result === "error" || e.result === "blocked").length === 0 && (
            <div className="lane-empty">暂无失败/拦截记录</div>
          )}
          {audit
            .filter((e) => e.result === "error" || e.result === "blocked")
            .slice(0, 10)
            .map((e) => (
              <div className="wb-item compact" key={e.id}>
                <div className="wb-item-main">
                  <strong>{e.summary || e.action}</strong>
                  <span className="task-meta">{e.actor}{e.task_title ? ` · ${e.task_title}` : ""}</span>
                </div>
                <span className={`pill ${e.result === "blocked" ? "red" : "amber"}`}>
                  {e.result === "blocked" ? "已拦截" : "失败"}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
