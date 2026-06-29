/**
 * React Query hooks for the Dashboard page.
 *
 * Replaces the manual useEffect + useState pattern with declarative queries.
 * Benefits: automatic dedup (StrictMode won't double-fire), stale-while-revalidate
 * caching (navigate away and back instantly shows cached data), and built-in
 * loading/error states.
 */
import { useQuery } from "@tanstack/react-query";
import { agentApi, fileApi, kbApi, scheduledApi, skillApi, taskApi } from "@/api/endpoints";
import { queryKeys } from "./keys";

export function useAgentList() {
  return useQuery({
    queryKey: queryKeys.agents.list(),
    queryFn: () => agentApi.list().then((r) => r.items),
  });
}

export function useSkillList() {
  return useQuery({
    queryKey: queryKeys.skills.list(),
    queryFn: () => skillApi.list().then((r) => r.items),
  });
}

export function useMyTasks() {
  return useQuery({
    queryKey: queryKeys.tasks.list(),
    queryFn: () => taskApi.list().then((r) => r.items),
  });
}

export function usePublicTasks() {
  return useQuery({
    queryKey: queryKeys.tasks.listPublic(),
    queryFn: () => taskApi.listPublic().then((r) => r.items),
  });
}

export function usePublicFiles() {
  return useQuery({
    queryKey: queryKeys.files.listPublic(),
    queryFn: () => fileApi.listPublic().then((r) => r.items),
  });
}

export function useKBList() {
  return useQuery({
    queryKey: queryKeys.kb.list(),
    queryFn: () => kbApi.list().then((r) => r.items),
  });
}

export function useMyScheduled() {
  return useQuery({
    queryKey: queryKeys.scheduled.listMine(),
    queryFn: () => scheduledApi.listMine().then((r) => r.items),
  });
}
