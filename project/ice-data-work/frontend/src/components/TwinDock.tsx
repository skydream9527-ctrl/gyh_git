import { useState } from "react";
import { useNavigate } from "react-router-dom";

// TwinDock：常驻右下角的 Twin 入口 + 指令驱动导航（D-12）。
// 用户对 Twin 说"带我去看板" → 解析意图切页。
const NAV_INTENTS: { keywords: string[]; path: string; label: string }[] = [
  { keywords: ["看板", "board", "任务板"], path: "/board", label: "任务看板" },
  { keywords: ["工作台", "workbench", "主页"], path: "/workbench", label: "工作台" },
  { keywords: ["团队", "team"], path: "/team", label: "团队" },
  { keywords: ["项目", "project"], path: "/project", label: "项目" },
  { keywords: ["twin", "分身", "我的twin"], path: "/twin", label: "Twin" },
  { keywords: ["新建", "new", "建任务"], path: "/new-mission", label: "新建任务" },
];

export default function TwinDock() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [reply, setReply] = useState("");
  const navigate = useNavigate();

  const handleCommand = () => {
    const text = input.trim().toLowerCase();
    if (!text) return;
    const match = NAV_INTENTS.find((intent) =>
      intent.keywords.some((k) => text.includes(k.toLowerCase()))
    );
    if (match) {
      setReply(`好的，带你去${match.label}。`);
      setTimeout(() => {
        navigate(match.path);
        setOpen(false);
        setReply("");
        setInput("");
      }, 500);
    } else {
      setReply("我可以带你去：看板 / 工作台 / 团队 / 项目 / Twin / 新建任务。");
    }
  };

  return (
    <>
      <button className="twin-dock-fab" onClick={() => setOpen((v) => !v)} title="我的 Twin">
        TW
      </button>
      {open && (
        <div className="twin-dock-panel">
          <div className="twin-dock-head">
            <span className="ava twin">TW</span>
            <div>
              <strong>我的 Twin</strong>
              <span className="task-meta">编排协调 · 指令导航</span>
            </div>
          </div>
          {reply && <div className="twin-dock-reply">{reply}</div>}
          <div className="twin-dock-input">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleCommand(); }}
              placeholder="试试：带我去看板"
            />
            <button className="btn-sm primary" onClick={handleCommand}>发送</button>
          </div>
        </div>
      )}
    </>
  );
}
