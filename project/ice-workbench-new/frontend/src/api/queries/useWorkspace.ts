/**
 * React Query hooks for Workspace data.
 *
 * These replace manual useState + useEffect patterns in WorkspacePage,
 * providing automatic caching, dedup, and background refetch.
 *
 * NOTE: Conversation history and WebSocket-driven state (streaming, partial,
 * tool calls) intentionally stay OUTSIDE React Query — they're real-time
 * push data, not request/response cacheable resources.
 */
import { useQuery } from "@tanstack/react-query";
import { agentApi, fileApi, kbApi, scheduledApi, skillApi, taskApi } from "@/api/endpoints";
import { queryKeys } from "./keys";

export function useTaskDetail(taskId: string) {
  return useQuery({
    queryKey: queryKeys.tasks.detail(taskId),
    queryFn: () => taskApi.detail(taskId),
    enabled: !!taskId,
  });
}

export function useTaskFiles(taskId: string) {
  return useQuery({
    queryKey: queryKeys.files.listTask(taskId),
    queryFn: () => fileApi.listTask(taskId).then((r) => r.items),
    enabled: !!taskId,
  });
}

export function useAgentDetail(agentId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.agents.detail(agentId || ""),
    queryFn: () => agentApi.get(agentId!),
    enabled: !!agentId,
  });
}

export function useTaskSkills() {
  return useQuery({
    queryKey: queryKeys.skills.list(),
    queryFn: () => skillApi.list().then((r) => r.items),
  });
}

export function useTaskScheduled(taskId: string) {
  return useQuery({
    queryKey: [...queryKeys.scheduled.all, "task", taskId] as const,
    queryFn: () => scheduledApi.listByTask(taskId).then((r) => r.items),
    enabled: !!taskId,
  });
}

export function useTaskKBs() {
  return useQuery({
    queryKey: queryKeys.kb.list(),
    queryFn: () => kbApi.list().then((r) => r.items),
  });
}

export function useTaskHitl(taskId: string) {
  return useQuery({
    queryKey: [...queryKeys.tasks.detail(taskId), "hitl"] as const,
    queryFn: () => taskApi.listHitl(taskId).then((r) => r.items),
    enabled: !!taskId,
  });
}
