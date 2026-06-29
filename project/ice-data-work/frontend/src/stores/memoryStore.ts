import { create } from "zustand";
import { apiGet, apiPost } from "@/api/client";

export type MemoryScope =
  | "user_preference"
  | "agent_user"
  | "agent_team"
  | "project"
  | "team";

export const SCOPE_LABELS: Record<MemoryScope, string> = {
  user_preference: "用户偏好",
  agent_user: "Agent · 我的经验",
  agent_team: "Agent · 团队共享",
  project: "项目共享",
  team: "团队共享",
};

export interface Candidate {
  id: string;
  proposed_scope: MemoryScope;
  content: string;
  tags?: string[];
  status: "pending" | "approved" | "rejected";
  needs_review?: boolean;
  source?: { task?: string; proposer?: string };
  mem_id?: string;
}

export interface Approval {
  id: string;
  task_id?: string;
  task_title?: string;
  action_type: string;
  summary: string;
  risk_level: string;
  status: "pending" | "approved" | "rejected";
  requester?: string;
}

interface PromoteArgs {
  task_id: string;
  candidate_id: string;
  scope?: MemoryScope;
  aid?: string;
  uid?: string;
  tid?: string;
  pid?: string;
}

interface MemoryState {
  candidates: Candidate[];
  approvals: Approval[];
  loading: boolean;

  fetchCandidates: (taskId: string) => Promise<void>;
  promote: (args: PromoteArgs) => Promise<void>;
  reject: (taskId: string, candidateId: string, reason?: string) => Promise<void>;

  fetchApprovals: (taskId: string) => Promise<void>;
  decide: (taskId: string, approvalId: string, approved: boolean) => Promise<void>;
}

export const useMemoryStore = create<MemoryState>((set, get) => ({
  candidates: [],
  approvals: [],
  loading: false,

  fetchCandidates: async (taskId) => {
    set({ loading: true });
    try {
      const candidates = await apiGet<Candidate[]>(`/memory/candidates?task_id=${taskId}`);
      set({ candidates, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  promote: async (args) => {
    await apiPost("/memory/promote", args);
    set({
      candidates: get().candidates.map((c) =>
        c.id === args.candidate_id ? { ...c, status: "approved" } : c
      ),
    });
  },

  reject: async (taskId, candidateId, reason) => {
    await apiPost("/memory/reject", { task_id: taskId, candidate_id: candidateId, reason: reason || "" });
    set({
      candidates: get().candidates.map((c) =>
        c.id === candidateId ? { ...c, status: "rejected" } : c
      ),
    });
  },

  fetchApprovals: async (taskId) => {
    try {
      const approvals = await apiGet<Approval[]>(`/approvals/${taskId}`);
      set({ approvals });
    } catch {
      /* ignore */
    }
  },

  decide: async (taskId, approvalId, approved) => {
    await apiPost("/approvals/decide", { task_id: taskId, approval_id: approvalId, approved });
    set({
      approvals: get().approvals.map((a) =>
        a.id === approvalId ? { ...a, status: approved ? "approved" : "rejected" } : a
      ),
    });
  },
}));
