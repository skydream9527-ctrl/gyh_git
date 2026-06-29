import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { useSpaceStore } from "@/stores/spaceStore";

interface SharedItem {
  name: string;
  size: number;
  updated_at: string;
  level: string;
  kind: string;
}

interface Assets {
  project: Record<string, SharedItem[]>;
  team: Record<string, SharedItem[]>;
}

type LevelFilter = "all" | "project" | "team";
type KindFilter = "all" | "files" | "knowledge" | "artifacts";

const KIND_LABELS: Record<string, string> = {
  files: "文件",
  knowledge: "知识",
  artifacts: "产物",
};

export default function Knowledge() {
  const { currentTeam, currentProject } = useSpaceStore();
  const [assets, setAssets] = useState<Assets | null>(null);
  const [level, setLevel] = useState<LevelFilter>("all");
  const [kind, setKind] = useState<KindFilter>("all");

  useEffect(() => {
    if (currentTeam && currentProject) {
      apiGet<Assets>(`/teams/${currentTeam.id}/projects/${currentProject.id}/assets`)
        .then(setAssets)
        .catch(() => setAssets({ project: {}, team: {} }));
    }
  }, [currentTeam, currentProject]);

  const rows: SharedItem[] = [];
  if (assets) {
    const levels: ("project" | "team")[] = level === "all" ? ["project", "team"] : [level];
    for (const lv of levels) {
      const kinds = kind === "all" ? ["files", "knowledge", "artifacts"] : [kind];
      for (const k of kinds) {
        for (const item of assets[lv][k] || []) rows.push(item);
      }
    }
  }

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <div className="eyebrow">Knowledge &amp; Artifacts</div>
          <h1>知识与产物</h1>
          <p className="subtle">按层级（个人 / 项目 / 团队）筛选共享资产。复用沉淀的口径、文档与产物。</p>
        </div>
      </div>

      {!currentProject && <div className="card">请先在侧边栏选择团队和项目。</div>}

      {currentProject && (
        <>
          <div className="toolbar">
            <select value={level} onChange={(e) => setLevel(e.target.value as LevelFilter)}>
              <option value="all">全部层级</option>
              <option value="project">项目级</option>
              <option value="team">团队级</option>
            </select>
            <select value={kind} onChange={(e) => setKind(e.target.value as KindFilter)}>
              <option value="all">全部类型</option>
              <option value="files">文件</option>
              <option value="knowledge">知识</option>
              <option value="artifacts">产物</option>
            </select>
            <span className="subtle" style={{ marginLeft: "auto", fontSize: 12 }}>
              {currentTeam?.name} · {currentProject.name}
            </span>
          </div>

          <div className="card">
            {rows.length === 0 && <div className="lane-empty">暂无共享资产。任务中"保存为产物（选层级）"后会出现在这里。</div>}
            {rows.map((item, i) => (
              <div className="row" key={`${item.level}-${item.kind}-${item.name}-${i}`}>
                <span>
                  <strong>{item.name}</strong>{" "}
                  <span className={`pill ${item.level === "team" ? "green" : "blue"}`}>
                    {item.level === "team" ? "团队" : "项目"}
                  </span>{" "}
                  <span className="pill slate">{KIND_LABELS[item.kind] || item.kind}</span>
                </span>
                <span className="task-meta">{(item.size / 1024).toFixed(1)} KB</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
