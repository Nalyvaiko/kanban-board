import type { JiraApi, TaskRelationView } from "../api";
import { ApiError } from "../types";
import type {
  Activity,
  ActivityWithActor,
  Attachment,
  Board,
  BoardData,
  Column,
  CommentWithAuthor,
  CreateProjectInput,
  CreateTaskInput,
  DashboardData,
  Invitation,
  Label,
  MemberWithUser,
  Project,
  RelationType,
  RelationWithTask,
  Role,
  Task,
  TaskFilters,
  UpdateTaskInput,
  User,
} from "../types";

const BASE_URL = import.meta.env["VITE_API_BASE_URL"] ?? "http://localhost:8000/api";
const TOKEN_KEY = "kanban_auth_token";

function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function setToken(token: string | null): void {
  try {
    if (typeof window === "undefined") return;
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore storage failures (private browsing, disabled storage, etc.)
  }
}

type Query = Record<string, string | undefined>;

async function request<T>(
  method: string,
  path: string,
  opts: { body?: unknown; query?: Query } = {},
): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  for (const [key, value] of Object.entries(opts.query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, value);
  }

  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | null = null;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const response = await fetch(url, { method, headers, body });
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = (data && (data.detail ?? data)) || {};
    const message =
      typeof detail.message === "string" ? detail.message : response.statusText || "Request failed";
    throw new ApiError(message, response.status);
  }
  return data as T;
}

/** HTTP-backed implementation of `JiraApi`, talking to the FastAPI backend. */
export class HttpJiraApi implements JiraApi {
  // Authentication
  async register(input: { name: string; email: string; password: string }): Promise<User> {
    const { token, user } = await request<{ token: string; user: User }>("POST", "/auth/register", {
      body: input,
    });
    setToken(token);
    return user;
  }

  async login(input: { email: string; password: string }): Promise<User> {
    const { token, user } = await request<{ token: string; user: User }>("POST", "/auth/login", {
      body: input,
    });
    setToken(token);
    return user;
  }

  async loginWithGoogle(): Promise<User> {
    throw new ApiError("Google sign-in is not wired up in this environment", 501);
  }

  async logout(): Promise<void> {
    await request<void>("POST", "/auth/logout");
    setToken(null);
  }

  async getCurrentUser(): Promise<User | null> {
    if (!getToken()) return null;
    return request<User | null>("GET", "/auth/me");
  }

  async updateProfile(input: { name: string }): Promise<User> {
    return request<User>("PATCH", "/auth/me", { body: input });
  }

  // Projects
  listProjects(): Promise<Project[]> {
    return request("GET", "/projects");
  }

  getProject(projectId: string): Promise<Project> {
    return request("GET", `/projects/${projectId}`);
  }

  createProject(input: CreateProjectInput): Promise<Project> {
    return request("POST", "/projects", { body: input });
  }

  updateProject(
    projectId: string,
    input: Partial<Pick<Project, "name" | "description">>,
  ): Promise<Project> {
    return request("PATCH", `/projects/${projectId}`, { body: input });
  }

  deleteProject(projectId: string): Promise<void> {
    return request("DELETE", `/projects/${projectId}`);
  }

  async getMyRole(projectId: string): Promise<Role> {
    const { role } = await request<{ role: Role }>("GET", `/projects/${projectId}/my-role`);
    return role;
  }

  // Members & invitations
  listMembers(projectId: string): Promise<MemberWithUser[]> {
    return request("GET", `/projects/${projectId}/members`);
  }

  addMember(projectId: string, email: string, role: Role): Promise<MemberWithUser> {
    return request("POST", `/projects/${projectId}/members`, { body: { email, role } });
  }

  updateMemberRole(projectId: string, userId: string, role: Role): Promise<MemberWithUser> {
    return request("PATCH", `/projects/${projectId}/members/${userId}`, { body: { role } });
  }

  removeMember(projectId: string, userId: string): Promise<void> {
    return request("DELETE", `/projects/${projectId}/members/${userId}`);
  }

  listInvitations(projectId: string): Promise<Invitation[]> {
    return request("GET", `/projects/${projectId}/invitations`);
  }

  inviteUser(projectId: string, email: string, role: Role): Promise<Invitation> {
    return request("POST", `/projects/${projectId}/invitations`, { body: { email, role } });
  }

  revokeInvitation(invitationId: string): Promise<void> {
    return request("DELETE", `/invitations/${invitationId}`);
  }

  listMyInvitations(): Promise<(Invitation & { project: Project })[]> {
    return request("GET", "/invitations/mine");
  }

  acceptInvitation(invitationId: string): Promise<void> {
    return request("POST", `/invitations/${invitationId}/accept`);
  }

  // Boards & columns
  listBoards(projectId: string): Promise<Board[]> {
    return request("GET", `/projects/${projectId}/boards`);
  }

  createBoard(projectId: string, name: string): Promise<Board> {
    return request("POST", `/projects/${projectId}/boards`, { body: { name } });
  }

  deleteBoard(boardId: string): Promise<void> {
    return request("DELETE", `/boards/${boardId}`);
  }

  getBoardData(boardId: string): Promise<BoardData> {
    return request("GET", `/boards/${boardId}/data`);
  }

  createColumn(boardId: string, name: string): Promise<Column> {
    return request("POST", `/boards/${boardId}/columns`, { body: { name } });
  }

  renameColumn(columnId: string, name: string): Promise<Column> {
    return request("PATCH", `/columns/${columnId}`, { body: { name } });
  }

  deleteColumn(columnId: string): Promise<void> {
    return request("DELETE", `/columns/${columnId}`);
  }

  reorderColumn(columnId: string, position: number): Promise<Column[]> {
    return request("POST", `/columns/${columnId}/reorder`, { body: { position } });
  }

  // Tasks
  listTasks(projectId: string, filters?: TaskFilters): Promise<Task[]> {
    return request("GET", `/projects/${projectId}/tasks`, {
      query: {
        search: filters?.search,
        columnId: filters?.columnId,
        assigneeId: filters?.assigneeId,
        priority: filters?.priority,
        type: filters?.type,
        labelId: filters?.labelId,
      },
    });
  }

  getTask(taskId: string): Promise<Task> {
    return request("GET", `/tasks/${taskId}`);
  }

  createTask(input: CreateTaskInput): Promise<Task> {
    return request("POST", "/tasks", { body: input });
  }

  updateTask(taskId: string, input: UpdateTaskInput): Promise<Task> {
    return request("PATCH", `/tasks/${taskId}`, { body: input });
  }

  moveTask(taskId: string, columnId: string, position?: number): Promise<Task> {
    return request("POST", `/tasks/${taskId}/move`, { body: { columnId, position } });
  }

  deleteTask(taskId: string): Promise<void> {
    return request("DELETE", `/tasks/${taskId}`);
  }

  // Comments
  listComments(taskId: string): Promise<CommentWithAuthor[]> {
    return request("GET", `/tasks/${taskId}/comments`);
  }

  addComment(taskId: string, body: string): Promise<CommentWithAuthor> {
    return request("POST", `/tasks/${taskId}/comments`, { body: { body } });
  }

  updateComment(commentId: string, body: string): Promise<CommentWithAuthor> {
    return request("PATCH", `/comments/${commentId}`, { body: { body } });
  }

  deleteComment(commentId: string): Promise<void> {
    return request("DELETE", `/comments/${commentId}`);
  }

  // Attachments
  listAttachments(taskId: string): Promise<Attachment[]> {
    return request("GET", `/tasks/${taskId}/attachments`);
  }

  uploadAttachment(taskId: string, file: File): Promise<Attachment> {
    const form = new FormData();
    form.append("file", file);
    return request("POST", `/tasks/${taskId}/attachments`, { body: form });
  }

  deleteAttachment(attachmentId: string): Promise<void> {
    return request("DELETE", `/attachments/${attachmentId}`);
  }

  // Labels
  listLabels(projectId: string): Promise<Label[]> {
    return request("GET", `/projects/${projectId}/labels`);
  }

  createLabel(projectId: string, name: string, color?: string): Promise<Label> {
    return request("POST", `/projects/${projectId}/labels`, { body: { name, color } });
  }

  renameLabel(labelId: string, name: string): Promise<Label> {
    return request("PATCH", `/labels/${labelId}`, { body: { name } });
  }

  deleteLabel(labelId: string): Promise<void> {
    return request("DELETE", `/labels/${labelId}`);
  }

  // Relations
  listRelations(taskId: string): Promise<RelationWithTask[]> {
    return request("GET", `/tasks/${taskId}/relations`);
  }

  addRelation(taskId: string, relatedTaskId: string, type: RelationType): Promise<TaskRelationView> {
    return request("POST", `/tasks/${taskId}/relations`, { body: { relatedTaskId, type } });
  }

  deleteRelation(relationId: string): Promise<void> {
    return request("DELETE", `/relations/${relationId}`);
  }

  // Activity
  listTaskActivity(taskId: string): Promise<ActivityWithActor[]> {
    return request("GET", `/tasks/${taskId}/activity`);
  }

  listProjectActivity(projectId: string): Promise<ActivityWithActor[]> {
    return request("GET", `/projects/${projectId}/activity`);
  }

  // Dashboard
  getDashboard(): Promise<DashboardData> {
    return request("GET", "/dashboard");
  }

  // Users
  listUsers(): Promise<User[]> {
    return request("GET", "/users");
  }
}

export type { Activity };
