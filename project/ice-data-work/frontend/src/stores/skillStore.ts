import { create } from "zustand";
import { apiGet, apiPost } from "@/api/client";

export interface SchemaParam {
  name: string;
  type?: string;
  required?: boolean;
  default?: unknown;
}

export type SkillScope = "by_user" | "by_team";

export interface SkillCandidate {
  id: string;
  name: string;
  description?: string;
  runtime: "python" | "sql";
  code: string;
  input_schema: SchemaParam[];
  knowledge?: string;
  agent_id?: string;
  proposed_scope: SkillScope;
  status: "pending" | "approved" | "rejected";
  needs_review?: boolean;
  skill_id?: string | null;
}

export interface Skill {
  id: string;
  name: string;
  description?: string;
  runtime: "python" | "sql";
  scope: SkillScope;
  owner?: { uid?: string; tid?: string };
  input_schema: SchemaParam[];
  knowledge?: string;
  version: number;
  test_passed?: boolean;
  versions?: { version: number; note?: string; created_at?: string }[];
}

export interface RunResult {
  ok: boolean;
  error_code?: string;
  message?: string;
  runtime?: string;
  stdout?: string;
  stderr?: string;
  exit_code?: number | null;
  timed_out?: boolean;
  duration_ms?: number;
  generated_files?: string[];
}

export interface UserSkillBinding {
  skill_id: string;
  knowledge?: string;
  bound_at?: string;
}

export interface AgentBindings {
  agent_id: string;
  builtin_skills: string[];
  team_skills: string[];
  user_skills: UserSkillBinding[];
  skill_knowledge: Record<string, string>;
  agent_version: number;
}

interface MaterializeArgs {
  task_id: string;
  candidate_id: string;
  bind?: boolean;
}

interface PromoteArgs {
  tid: string;
  skill_id: string;
  agent_id?: string;
  task_id?: string;
  approval_id?: string;
}

interface SkillState {
  mySkills: Skill[];
  teamSkills: Skill[];
  candidates: SkillCandidate[];
  loading: boolean;

  fetchMine: () => Promise<void>;
  fetchTeam: (tid?: string) => Promise<void>;
  fetchCandidates: (taskId: string) => Promise<void>;
  fetchAgentBindings: (agentId: string) => Promise<AgentBindings | null>;
  fetchSkill: (skillId: string) => Promise<Skill | null>;

  materialize: (args: MaterializeArgs) => Promise<void>;
  testRun: (skillId: string, sampleParams?: Record<string, unknown>) => Promise<RunResult>;
  promote: (args: PromoteArgs) => Promise<void>;
  bind: (args: { agent_id: string; skill_id: string; knowledge?: string }) => Promise<void>;
  rollback: (skillId: string, version: number) => Promise<void>;
}

export const useSkillStore = create<SkillState>((set, get) => ({
  mySkills: [],
  teamSkills: [],
  candidates: [],
  loading: false,

  fetchMine: async () => {
    set({ loading: true });
    try {
      set({ mySkills: await apiGet<Skill[]>("/skills/mine"), loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchTeam: async (tid = "") => {
    try {
      set({ teamSkills: await apiGet<Skill[]>(`/skills/team?tid=${encodeURIComponent(tid)}`) });
    } catch {
      /* ignore */
    }
  },

  fetchCandidates: async (taskId) => {
    try {
      set({ candidates: await apiGet<SkillCandidate[]>(`/skills/candidates?task_id=${encodeURIComponent(taskId)}`) });
    } catch {
      /* ignore */
    }
  },

  fetchAgentBindings: async (agentId) => {
    try {
      return await apiGet<AgentBindings>(`/skills/agent/${encodeURIComponent(agentId)}`);
    } catch {
      return null;
    }
  },

  fetchSkill: async (skillId) => {
    try {
      return await apiGet<Skill>(`/skills/${encodeURIComponent(skillId)}`);
    } catch {
      return null;
    }
  },

  materialize: async (args) => {
    await apiPost("/skills/materialize", { bind: true, ...args });
    set({
      candidates: get().candidates.map((c) =>
        c.id === args.candidate_id ? { ...c, status: "approved" } : c
      ),
    });
  },

  testRun: async (skillId, sampleParams) => {
    return await apiPost<RunResult>("/skills/test-run", {
      skill_id: skillId,
      sample_params: sampleParams ?? null,
    });
  },

  promote: async ({ tid, ...body }) => {
    await apiPost(`/skills/promote/${encodeURIComponent(tid)}`, body);
  },

  bind: async (args) => {
    await apiPost("/skills/bind", args);
  },

  rollback: async (skillId, version) => {
    await apiPost("/skills/rollback", { skill_id: skillId, version });
  },
}));
