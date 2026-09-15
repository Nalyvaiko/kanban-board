import { useQuery } from "@tanstack/react-query";

import { api } from "@/services";

export const qk = {
  dashboard: ["dashboard"] as const,
  projects: ["projects"] as const,
  project: (id: string) => ["project", id] as const,
  role: (id: string) => ["project", id, "role"] as const,
  members: (id: string) => ["project", id, "members"] as const,
  invitations: (id: string) => ["project", id, "invitations"] as const,
  labels: (id: string) => ["project", id, "labels"] as const,
  boards: (id: string) => ["project", id, "boards"] as const,
  boardData: (boardId: string) => ["board", boardId] as const,
  tasks: (id: string) => ["project", id, "tasks"] as const,
  activity: (id: string) => ["project", id, "activity"] as const,
  task: (id: string) => ["task", id] as const,
  comments: (id: string) => ["task", id, "comments"] as const,
  attachments: (id: string) => ["task", id, "attachments"] as const,
  relations: (id: string) => ["task", id, "relations"] as const,
  taskActivity: (id: string) => ["task", id, "activity"] as const,
};

export function useProject(projectId: string) {
  return useQuery({ queryKey: qk.project(projectId), queryFn: () => api.getProject(projectId) });
}

export function useMyRole(projectId: string) {
  return useQuery({ queryKey: qk.role(projectId), queryFn: () => api.getMyRole(projectId) });
}

export function useMembers(projectId: string) {
  return useQuery({ queryKey: qk.members(projectId), queryFn: () => api.listMembers(projectId) });
}

export function useLabels(projectId: string) {
  return useQuery({ queryKey: qk.labels(projectId), queryFn: () => api.listLabels(projectId) });
}

export function useBoards(projectId: string) {
  return useQuery({ queryKey: qk.boards(projectId), queryFn: () => api.listBoards(projectId) });
}

export function useCanWrite(projectId: string) {
  const { data: role } = useMyRole(projectId);
  return role === "admin" || role === "member";
}
