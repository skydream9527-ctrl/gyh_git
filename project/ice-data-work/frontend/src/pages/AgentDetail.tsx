import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiGet } from "@/api/client";
import { useSkillStore, type AgentBindings, type RunResult, type Skill } from "@/stores/skillStore";

interface AgentDetailData {
  id: string;
  name: string;
  description?: string;
  type?: string;
  skills?: string[];
  capabilities?: string[];
  version?: number;
  agent_md?: string;
}

export default function AgentDetail() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const { fetchAgentBindings, fetchMine, mySkills, testRun, rollback } = useSkillStore();
  const [agent, setAgent] = useState<AgentDetailData | null>(null);
  const [bindings, setBindings] = useState<AgentBindings | null>(null);
  const [runResults, setRunResults] = useState<Record<string, RunResult>>({});
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (!agentId) return;
    apiGet<AgentDetailData>(`/agents/${agentId}`).then(setAgent).catch(() => {});
    fetchAgentBindings(agentId).then(setBindings);
    fetchMine();
  }, [agentId]);

  if (!agent) return <div className="page"><p>加载 Agent 中…</p></div>;

  const builtin = bindings?.builtin_skills ?? agent.skills ?? [];
  const teamSkills = bindings?.team_skills ?? [];
  const knowledge = bindings?.skill_knowledge ?? {};
  const boundDraftIds = new Set((bindings?.user_skills ?? []).map((b) => b.skill_id));
  const myDrafts: Skill[] = mySkills.filter((s) => boundDraftIds.has(s.id));

  const doTest = async (sid: string) => {
    setBusy(sid);
    try {
      const r = await testRun(sid);
      setRunResults((p) => ({ ...p, [sid]: r }));
    } finally {
      setBusy("");
    }
  };

  const doRollback = async (s: Skill) => {
    if (s.version <= 1) return;
    if (!window.confirm(`回滚 ${s.name} 到 v${s.version - 1}？将生成新版本，不删历史。`)) return;
    setBusy(s.id);
    try {
      await rollback(s.id, s.version - 1);
      await fetchMine();
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="crumb"><button className="link-btn" onClick={() => navigate("/agents")}>Agent Hub</button> / {agent.name}</div>
          <div className="eyebrow">Agent Card · {agent.id}</div>
          <h1>{agent.name}</h1>
          <p className="subtle">{agent.description}</p>
        </div>
      </div>

      <div className="wb-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="card">
          <h3>能力 / 技能</h3>
          <div className="kv">
            <b>类型</b><span>{agent.type === "builtin" ? "内置（服务端运行时）" : agent.type}</span>
            <b>版本</b><span>v{bindings?.agent_version ?? agent.version ?? 1}</span>
            <b>能力</b><span>{(agent.capabilities || []).join(" · ") || "—"}</span>
          </div>
        </div>

        <div className="card">
          <h3>记忆分区（D-06）</h3>
          <div className="mem-partition">
            <div className="partition-box">
              <span className="pill slate">by-user / 我（私有）</span>
              <p className="subtle">我的使用经验，仅我可见，默认隔离不泄漏给同事。</p>
            </div>
            <div className="partition-box">
              <span className="pill green">by-team / 团队（共享）</span>
              <p className="subtle">经"贡献给团队"审核后的口径与方法，团队成员调用本 Agent 时受益。</p>
            </div>
          </div>
        </div>
      </div>

      {/* Skills D-13：内置 + 团队共享 + 我的草稿 */}
      <div className="card">
        <div className="card-head"><h3>技能 Skills（D-13）</h3><span className="pill green">自演进</span></div>

        <div className="wb-list">
          {builtin.map((s) => (
            <div className="wb-item" key={`b-${s}`}>
              <div className="wb-item-main">
                <strong>{s}</strong>
                <span className="task-meta">内置工具</span>
              </div>
              <span className="pill slate">builtin</span>
            </div>
          ))}
          {teamSkills.map((sid) => (
            <div className="wb-item" key={`t-${sid}`}>
              <div className="wb-item-main">
                <strong>{sid}</strong>
                <span className="task-meta">团队共享{knowledge[sid] ? ` · 何时用：${knowledge[sid]}` : ""}</span>
              </div>
              <div className="wb-item-actions">
                <button className="btn-sm" disabled={busy === sid} onClick={() => doTest(sid)}>沙盒测试</button>
                <span className="pill green">team</span>
              </div>
            </div>
          ))}
          {builtin.length === 0 && teamSkills.length === 0 && <div className="lane-empty">暂无内置/团队技能</div>}
        </div>

        <div className="card-head" style={{ marginTop: 16 }}>
          <h4>我贡献的草稿 Skill（by-user，仅我可见）</h4>
        </div>
        <div className="wb-list">
          {myDrafts.map((s) => (
            <div className="wb-item" key={s.id}>
              <div className="wb-item-main">
                <strong>{s.name}</strong>
                <span className="task-meta">
                  {s.runtime} · v{s.version} · 入参 {s.input_schema.map((p) => p.name).join("/") || "无"}
                  {s.test_passed ? " · 沙盒已通过" : ""}
                </span>
                {runResults[s.id] && (
                  <span className={`task-meta ${runResults[s.id].ok ? "ok" : "err"}`}>
                    测试：{runResults[s.id].ok ? "成功" : runResults[s.id].error_code || "失败"}
                    {runResults[s.id].stdout ? ` · 输出 ${runResults[s.id].stdout!.slice(0, 60)}` : ""}
                  </span>
                )}
              </div>
              <div className="wb-item-actions">
                <button className="btn-sm" disabled={busy === s.id} onClick={() => doTest(s.id)}>沙盒测试</button>
                {s.version > 1 && (
                  <button className="btn-sm" disabled={busy === s.id} onClick={() => doRollback(s)}>回滚</button>
                )}
                {s.test_passed ? <span className="pill green">已通过</span> : <span className="pill amber">草稿</span>}
              </div>
            </div>
          ))}
          {myDrafts.length === 0 && (
            <div className="lane-empty">暂无绑定到本 Agent 的草稿 Skill（在任务里用 run_user_code 跑通后「贡献为 Skill」）</div>
          )}
        </div>
      </div>

      {agent.agent_md && (
        <div className="card">
          <div className="card-head"><h3>操作手册（agent.md）</h3></div>
          <pre className="agent-md">{agent.agent_md}</pre>
        </div>
      )}
    </div>
  );
}
