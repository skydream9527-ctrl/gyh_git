import { create } from "zustand";
import { apiGet, apiPost } from "@/api/client";
import type { Approval } from "@/stores/memoryStore";

export interface AuditEvent {
  id: string;
  ts: string;
  actor: string;
  action: string;
  tool?: string;
  result: "ok" | "blocked" | "error" | "pending";
  summary: string;
  task_id?: string;
  task_title?: string;
}

interface ControlState {
  global_paused: boolean;
  paused_by?: string;
  paused_at?: string;
}

interface GovernanceState {
  approvals: Approval[];
  audit: AuditEvent[];
  control: ControlState;
  loading: boolean;

  fetchApprovals: () => Promise<void>;
  fetchAudit: () => Promise<void>;
  fetchControl: () => Promise<void>;
  decide: (taskId: string, approvalId: string, approved: boolean) => Promise<void>;
  pauseAll: () => Promise<void>;
  resumeAll: () => Promise<void>;
}

export const useGovernanceStore = create<GovernanceState>((set, get) => ({
  approvals: [],
  audit: [],
  control: { global_paused: false },
  loading: false,

  fetchApprovals: async () => {
    set({ loading: true });
    try {
      const approvals = await apiGet<Approval[]>("/approvals");
      set({ approvals, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchAudit: async () => {
    try {
      const audit = await apiGet<AuditEvent[]>("/audit");
      set({ audit });
    } catch {
      /* ignore */
    }
  },

  fetchControl: async () => {
    try {
      const control = await apiGet<ControlState>("/control");
      set({ control });
    } catch {
      /* ignore */
    }
  },

  decide: async (taskId, approvalId, approved) => {
    await apiPost("/approvals/decide", { task_id: taskId, approval_id: approvalId, approved });
    set({ approvals: get().approvals.filter((a) => a.id !== approvalId) });
  },

  pauseAll: async () => {
    await apiPost("/control/pause");
    set({ control: { ...get().control, global_paused: true } });
  },

  resumeAll: async () => {
    await apiPost("/control/resume");
    set({ control: { ...get().control, global_paused: false } });
  },
}));
