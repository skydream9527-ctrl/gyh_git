import { create } from "zustand";
import { apiGet } from "@/api/client";

export interface Team {
  id: string;
  name: string;
  type: string;
  member_count: number;
}

export interface Project {
  id: string;
  name: string;
  team_id: string;
  type: string;
  member_count: number;
}

interface SpaceState {
  teams: Team[];
  projects: Project[];
  currentTeam: Team | null;
  currentProject: Project | null;
  loading: boolean;

  fetchTeams: () => Promise<void>;
  fetchProjects: (teamId: string) => Promise<void>;
  selectTeam: (team: Team) => void;
  selectProject: (project: Project) => void;
}

export const useSpaceStore = create<SpaceState>((set, get) => ({
  teams: [],
  projects: [],
  currentTeam: null,
  currentProject: null,
  loading: false,

  fetchTeams: async () => {
    set({ loading: true });
    try {
      const teams = await apiGet<Team[]>("/teams");
      set({ teams, loading: false });
      // 自动选中第一个非个人团队，否则选个人空间
      if (!get().currentTeam && teams.length > 0) {
        const nonPersonal = teams.find((t) => t.type !== "personal");
        set({ currentTeam: nonPersonal || teams[0] });
      }
    } catch {
      set({ loading: false });
    }
  },

  fetchProjects: async (teamId: string) => {
    set({ loading: true });
    try {
      const projects = await apiGet<Project[]>(`/teams/${teamId}/projects`);
      set({ projects, loading: false });
      // 自动选中第一个项目
      if (projects.length > 0 && !get().currentProject) {
        set({ currentProject: projects[0] });
      }
    } catch {
      set({ loading: false });
    }
  },

  selectTeam: (team) => {
    set({ currentTeam: team, currentProject: null, projects: [] });
  },

  selectProject: (project) => {
    set({ currentProject: project });
  },
}));
