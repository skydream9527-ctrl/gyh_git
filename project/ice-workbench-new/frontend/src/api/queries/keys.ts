/**
 * Centralized query key factory.
 *
 * Convention: each domain gets a namespace array. Granularity increases
 * left-to-right so invalidation can target broad or narrow scopes.
 *
 * Example:
 *   queryClient.invalidateQueries({ queryKey: queryKeys.tasks.all })  // all task queries
 *   queryClient.invalidateQueries({ queryKey: queryKeys.tasks.detail(id) })  // single task
 */
export const queryKeys = {
  tasks: {
    all: ["tasks"] as const,
    list: () => [...queryKeys.tasks.all, "list"] as const,
    listPublic: () => [...queryKeys.tasks.all, "list-public"] as const,
    detail: (id: string) => [...queryKeys.tasks.all, "detail", id] as const,
  },
  agents: {
    all: ["agents"] as const,
    list: () => [...queryKeys.agents.all, "list"] as const,
    detail: (id: string) => [...queryKeys.agents.all, "detail", id] as const,
  },
  skills: {
    all: ["skills"] as const,
    list: () => [...queryKeys.skills.all, "list"] as const,
  },
  files: {
    all: ["files"] as const,
    listPublic: () => [...queryKeys.files.all, "list-public"] as const,
    listTask: (taskId: string) => [...queryKeys.files.all, "task", taskId] as const,
  },
  kb: {
    all: ["kb"] as const,
    list: () => [...queryKeys.kb.all, "list"] as const,
  },
  scheduled: {
    all: ["scheduled"] as const,
    listMine: () => [...queryKeys.scheduled.all, "mine"] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    list: () => [...queryKeys.notifications.all, "list"] as const,
  },
} as const;
