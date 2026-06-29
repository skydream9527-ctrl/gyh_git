import { useEffect, useState } from "react";
import { apiGet, apiPut } from "@/api/client";

interface TwinData {
  user_id: string;
  name: string;
  level: number;
  persona: string;
  preferences: Record<string, string>;
  goals: string[];
}

interface MemoryEntry {
  mem_id: string;
  content: string;
  confidence: string;
  tags: string[];
  source: string;
}

interface TwinMemory {
  preferences: MemoryEntry[];
  pinned: MemoryEntry[];
}

const LEVEL_LABELS: Record<number, string> = {
  0: "L0 · 仅观察",
  1: "L1 · 建议",
  2: "L2 · 起草委托",
  3: "L3 · 请求执行",
  4: "L4 · 有界自治",
  5: "L5 · 完全自治",
};

export default function Twin() {
  const [twin, setTwin] = useState<TwinData | null>(null);
  const [memory, setMemory] = useState<TwinMemory>({ preferences: [], pinned: [] });
  const [editing, setEditing] = useState(false);
  const [persona, setPersona] = useState("");
  const [level, setLevel] = useState(2);

  useEffect(() => {
    apiGet<TwinData>("/twin").then((t) => {
      setTwin(t);
      setPersona(t.persona || "");
      setLevel(t.level);
    }).catch(() => {});
    apiGet<TwinMemory>("/twin/memory").then(setMemory).catch(() => {});
  }, []);

  const handleSave = async () => {
    const updated = await apiPut<TwinData>("/twin", { persona, level });
    setTwin(updated);
    setEditing(false);
  };

  if (!twin) {
    return <div className="page"><p>加载 Twin 中…</p></div>;
  }

  return (
    <div className="page">
      <div className="eyebrow">我的 Twin</div>
      <h1>{twin.name}</h1>
      <p className="subtle">Twin 是你的 AI 化身，代表你在平台中与 Agent 协作。</p>

      <div className="card">
        <div className="row">
          <b>权限等级</b>
          {editing ? (
            <select value={level} onChange={(e) => setLevel(Number(e.target.value))} aria-label="权限等级">
              {Object.entries(LEVEL_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          ) : (
            <span className="pill ok">{LEVEL_LABELS[twin.level]}</span>
          )}
        </div>

        <div className="row">
          <b>画像</b>
          {editing ? (
            <textarea
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              rows={3}
              style={{ flex: 1, marginLeft: 12 }}
              aria-label="Twin 画像"
            />
          ) : (
            <span className="subtle">{twin.persona || "未设置"}</span>
          )}
        </div>

        {twin.goals.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <b>目标</b>
            <ul>
              {twin.goals.map((g, i) => <li key={i}>{g}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        {editing ? (
          <>
            <button className="btn-primary" onClick={handleSave}>保存</button>{" "}
            <button className="link-btn" onClick={() => setEditing(false)}>取消</button>
          </>
        ) : (
          <button className="btn-primary" onClick={() => setEditing(true)}>编辑</button>
        )}
      </div>

      {/* 记忆管理 */}
      <h3 style={{ marginTop: 28 }}>记忆管理</h3>
      <p className="subtle">Twin 长期记忆。偏好/决策由任务中的记忆候选晋升而来（M3 闭环）。</p>

      <div className="card">
        <h4 className="mem-section-title">📌 Pinned 记忆（始终注入）</h4>
        {memory.pinned.length === 0 && <div className="lane-empty">暂无 pinned 记忆</div>}
        {memory.pinned.map((m) => (
          <div key={m.mem_id} className="mem-entry">
            <span className="mono">{m.mem_id}</span>
            <span>{m.content}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h4 className="mem-section-title">偏好记忆</h4>
        {memory.preferences.length === 0 && (
          <div className="lane-empty">暂无偏好记忆。在任务中晋升 user_preference 候选后出现在这里。</div>
        )}
        {memory.preferences.map((m) => (
          <div key={m.mem_id} className="mem-entry">
            <div>
              <span className="mono">{m.mem_id}</span>
              <span className={`pill ${m.confidence === "high" ? "green" : "slate"}`}>{m.confidence}</span>
            </div>
            <span>{m.content}</span>
            {m.tags.length > 0 && <span className="task-meta">tags: {m.tags.join(", ")}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
