import { useEffect, useState } from "react";
import { useSpaceStore } from "@/stores/spaceStore";
import { apiGet } from "@/api/client";

interface TeamDetail {
  id: string;
  name: string;
  type: string;
  members: { user_id: string; role: string }[];
}

export default function Team() {
  const { currentTeam } = useSpaceStore();
  const [detail, setDetail] = useState<TeamDetail | null>(null);

  useEffect(() => {
    if (currentTeam) {
      apiGet<TeamDetail>(`/teams/${currentTeam.id}`).then(setDetail).catch(() => {});
    }
  }, [currentTeam]);

  if (!currentTeam) {
    return <div className="page"><p className="subtle">请选择一个团队</p></div>;
  }

  return (
    <div className="page">
      <div className="eyebrow">团队管理</div>
      <h1>{currentTeam.name}</h1>
      <p className="subtle">团队 ID：{currentTeam.id}</p>

      {detail && (
        <div className="card">
          <h3>成员 ({detail.members.length})</h3>
          <div className="member-list">
            {detail.members.map((m) => (
              <div key={m.user_id} className="row">
                <span>{m.user_id}</span>
                <span className="pill ok">{m.role}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
