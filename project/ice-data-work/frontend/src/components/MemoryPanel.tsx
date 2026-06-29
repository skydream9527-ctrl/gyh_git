import { useEffect, useState } from "react";
import {
  useMemoryStore,
  SCOPE_LABELS,
  type Candidate,
  type MemoryScope,
} from "@/stores/memoryStore";
import type { Participant } from "@/stores/taskStore";

interface MemoryPanelProps {
  taskId: string;
  participants: Participant[];
  onClose: () => void;
}

// 单个记忆候选卡：展示内容 + scope 选择（含"贡献给团队"升级）+ 晋升/拒绝。
function CandidateCard({ cand, taskId, agentId }: { cand: Candidate; taskId: string; agentId: string }) {
  const { promote, reject } = useMemoryStore();
  const [scope, setScope] = useState<MemoryScope>(cand.proposed_scope);
  const [busy, setBusy] = useState(false);

  const done = cand.status !== "pending";

  // agent_user 可升级为 agent_team（贡献给团队）
  const canContribute = cand.proposed_scope === "agent_user" || cand.proposed_scope === "agent_team";

  const handlePromote = async () => {
    setBusy(true);
    try {
      await promote({
        task_id: taskId,
        candidate_id: cand.id,
        scope,
        aid: scope.startsWith("agent") ? agentId : undefined,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`mem-card ${done ? "done" : ""}`}>
      <div className="mem-card-top">
        <span className={`pill ${cand.needs_review ? "amber" : "blue"}`}>
          {SCOPE_LABELS[cand.proposed_scope]}
        </span>
        {cand.status === "approved" && <span className="pill green">已晋升{cand.mem_id ? ` · ${cand.mem_id}` : ""}</span>}
        {cand.status === "rejected" && <span className="pill red">已拒绝</span>}
      </div>
      <div className="mem-content">{cand.content}</div>
      {cand.source?.proposer && (
        <div className="task-meta">来源：{cand.source.proposer}</div>
      )}

      {!done && (
        <div className="mem-actions">
          <select value={scope} onChange={(e) => setScope(e.target.value as MemoryScope)} aria-label="晋升 scope">
            <option value={cand.proposed_scope}>{SCOPE_LABELS[cand.proposed_scope]}（默认）</option>
            {canContribute && cand.proposed_scope === "agent_user" && (
              <option value="agent_team">贡献给团队（agent_team）</option>
            )}
            {cand.proposed_scope !== "user_preference" && (
              <>
                <option value="project">项目共享</option>
                <option value="team">团队共享</option>
              </>
            )}
          </select>
          <button className="btn-sm primary" onClick={handlePromote} disabled={busy}>
            {busy ? "晋升中…" : "晋升"}
          </button>
          <button className="btn-sm" onClick={() => reject(taskId, cand.id)} disabled={busy}>拒绝</button>
        </div>
      )}
    </div>
  );
}

export default function MemoryPanel({ taskId, participants, onClose }: MemoryPanelProps) {
  const { candidates, approvals, fetchCandidates, fetchApprovals, decide } = useMemoryStore();
  const [tab, setTab] = useState<"memory" | "approvals">("memory");

  const agentId = participants.find((p) => p.ref_type === "agent")?.ref_id || "data-analysis";

  useEffect(() => {
    fetchCandidates(taskId);
    fetchApprovals(taskId);
  }, [taskId, fetchCandidates, fetchApprovals]);

  const pendingApprovals = approvals.filter((a) => a.status === "pending");

  return (
    <div className="ws-drawer">
      <div className="drawer-head">
        <div className="drawer-tabs">
          <button className={tab === "memory" ? "tab active" : "tab"} onClick={() => setTab("memory")}>
            记忆候选 {candidates.filter((c) => c.status === "pending").length > 0 && `· ${candidates.filter((c) => c.status === "pending").length}`}
          </button>
          <button className={tab === "approvals" ? "tab active" : "tab"} onClick={() => setTab("approvals")}>
            待确认 {pendingApprovals.length > 0 && `· ${pendingApprovals.length}`}
          </button>
        </div>
        <button className="link-btn" onClick={onClose}>关闭</button>
      </div>

      {tab === "memory" && (
        <div className="mem-list">
          {candidates.length === 0 && (
            <div className="lane-empty">暂无记忆候选。对话中 Agent/Twin 调 propose_memory 会在此出现。</div>
          )}
          {candidates.map((c) => (
            <CandidateCard key={c.id} cand={c} taskId={taskId} agentId={agentId} />
          ))}
        </div>
      )}

      {tab === "approvals" && (
        <div className="mem-list">
          {pendingApprovals.length === 0 && <div className="lane-empty">没有待确认事项</div>}
          {pendingApprovals.map((a) => (
            <div key={a.id} className="mem-card">
              <div className="mem-card-top">
                <span className={`pill ${a.risk_level === "high" ? "red" : "amber"}`}>{a.action_type || "确认"}</span>
              </div>
              <div className="mem-content">{a.summary}</div>
              <div className="mem-actions">
                <button className="btn-sm primary" onClick={() => decide(taskId, a.id, true)}>批准</button>
                <button className="btn-sm" onClick={() => decide(taskId, a.id, false)}>拒绝</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
