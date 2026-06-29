import { create } from "zustand";
import { apiGet, apiPost, apiPut } from "@/api/client";

export type TaskStatus = "todo" | "doing" | "await" | "done" | "error" | "paused";

export interface Participant {
  ref_type: "user" | "twin" | "agent";
  ref_id: string;
  role: string;
  permission_level?: string;
  joined_at?: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  type: "data" | "general";
  status: TaskStatus;
  assignee: { type: string; id: string } | null;
  participants?: Participant[];
  participant_count?: number;
  artifact_count?: number;
  created_at?: string;
  updated_at?: string;
  error_reason?: string;
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "待办",
  doing: "执行中",
  await: "待确认",
  done: "已完成",
  error: "报错",
  paused: "已暂停",
};

export const STATUS_PILL: Record<TaskStatus, string> = {
  todo: "slate",
  doing: "blue",
  await: "amber",
  done: "green",
  error: "red",
  paused: "slate",
};

interface TaskState {
  tasks: Task[];
  loading: boolean;

  fetchTasks: (projectId?: string) => Promise<void>;
  createTask: (data: { title: string; project_id?: string; type?: string }) => Promise<Task>;
  setStatus: (taskId: string, status: TaskStatus, reason?: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  loading: false,

  fetchTasks: async (projectId) => {
    set({ loading: true });
    try {
      const q = projectId ? `?project_id=${projectId}` : "";
      const tasks = await apiGet<Task[]>(`/tasks${q}`);
      set({ tasks, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  createTask: async (data) => {
    const task = await apiPost<Task>("/tasks", data);
    set({ tasks: [task, ...get().tasks] });
    return task;
  },

  setStatus: async (taskId, status, reason) => {
    await apiPut(`/tasks/${taskId}/status`, { status, reason: reason || "" });
    set({
      tasks: get().tasks.map((t) => (t.id === taskId ? { ...t, status } : t)),
    });
  },
}));
