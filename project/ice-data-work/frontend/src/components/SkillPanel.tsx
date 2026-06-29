import { useEffect, useState } from "react";
import { useSkillStore, type SkillCandidate } from "@/stores/skillStore";
import type { Participant } from "@/stores/taskStore";

// 单个 Skill 候选卡（「贡献为 Skill」表单）：展示代码/入参/范围 + 沉淀按钮。
function CandidateCard({ cand, taskId }: { cand: SkillCandidate; taskId: string }) {
  const { materialize } = useSkillStore();
  const [busy, setBusy] = useState(false);
  const done = cand.status !== "pending";

  const handle = async () => {
    setBusy(true);
    try {
      await materialize({ task_id: taskId, candidate_id: cand.id, bind: true });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`mem-card ${done ? "done" : ""}`}>
      <div className="mem-card-top">
        <span className="pill blue">{cand.runtime}</span>
        {cand.proposed_scope === "by_team" && <span className="pill amber">贡献团队 · 需 test-run + 审核</span>}
        {cand.status === "approved" && (
          <span className="pill green">已沉淀{cand.skill_id ? ` · ${cand.skill_id}` : ""}</span>
        )}
        {cand.status === "rejected" && <span className="pill red">已拒绝</span>}
      </div>
      <div className="mem-content">
        <strong>{cand.name}</strong>
        {cand.description ? ` · ${cand.description}` : ""}
      </div>
      <pre className="tool-output">{cand.code.slice(0, 600)}</pre>
      <div className="task-meta">
        入参：{cand.input_schema.map((p) => p.name).join(" / ") || "无"}
        {cand.agent_id ? ` · 绑定 ${cand.agent_id}` : ""}
        {cand.knowledge ? ` · 何时用：${cand.knowledge}` : ""}
      </div>
      {!done && (
        <div className="mem-actions">
          <button className="btn-sm primary" onClick={handle} disabled={busy}>
            {busy ? "沉淀中…" : "沉淀为 Skill（个人草稿·立即可用）"}
          </button>
        </div>
      )}
      {cand.status === "approved" && cand.proposed_scope === "by_team" && (
        <div className="task-meta">已发起团队晋升审批，待 owner/admin 在审批页确认。</div>
      )}
    </div>
  );
}

export default function SkillPanel({ taskId, onClose }: { taskId: string; participants: Participant[]; onClose: () => void }) {
  const { candidates, fetchCandidates } = useSkillStore();

  useEffect(() => {
    fetchCandidates(taskId);
  }, [taskId, fetchCandidates]);

  return (
    <div className="ws-drawer">
      <div className="drawer-head">
        <h3>技能候选 Skill（D-13）</h3>
        <button className="link-btn" onClick={onClose}>关闭</button>
      </div>
      <div className="mem-list">
        {candidates.length === 0 && (
          <div className="lane-empty">暂无 Skill 候选。对话中用 run_user_code 跑通代码后，Agent 调 propose_skill 会在此出现。</div>
        )}
        {candidates.map((c) => (
          <CandidateCard key={c.id} cand={c} taskId={taskId} />
        ))}
      </div>
    </div>
  );
}
