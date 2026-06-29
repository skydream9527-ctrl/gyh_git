import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import Login from "@/pages/Login";
import Workbench from "@/pages/Workbench";
import Board from "@/pages/Board";
import NewMission from "@/pages/NewMission";
import Workspace from "@/pages/Workspace";
import Team from "@/pages/Team";
import Project from "@/pages/Project";
import Twin from "@/pages/Twin";
import Approvals from "@/pages/Approvals";
import Admin from "@/pages/Admin";
import Agents from "@/pages/Agents";
import AgentDetail from "@/pages/AgentDetail";
import Knowledge from "@/pages/Knowledge";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* 需认证的路由 */}
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/workbench" replace />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/board" element={<Board />} />
        <Route path="/new-mission" element={<NewMission />} />
        <Route path="/task/:taskId" element={<Workspace />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/agents/:agentId" element={<AgentDetail />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/team" element={<Team />} />
        <Route path="/project" element={<Project />} />
        <Route path="/twin" element={<Twin />} />
      </Route>

      <Route path="*" element={<div style={{ padding: 24 }}>404 · 该页面将于后续里程碑移植</div>} />
    </Routes>
  );
}
