// Domain types shared by the services layer and the UI.

export type Role = "admin" | "member" | "viewer";
export type TaskType = "task" | "bug" | "feature";
export type Priority = "low" | "medium" | "high" | "urgent";
export type RelationType = "blocks" | "blocked_by" | "relates_to";
export type InvitationStatus = "pending" | "accepted" | "revoked";

export interface User {
  id: string;
  name: string;
  email: string;
  avatarColor: string;
  provider: "password" | "google";
  createdAt: string;
}

export interface Project {
  id: string;
  key: string;
  name: string;
  description: string;
  createdBy: string;
  createdAt: string;
}

export interface ProjectMember {
  id: string;
  projectId: string;
  userId: string;
  role: Role;
  createdAt: string;
}

export interface Board {
  id: string;
  projectId: string;
  name: string;
  createdAt: string;
}

export interface Column {
  id: string;
  boardId: string;
  name: string;
  position: number;
}

export interface Label {
  id: string;
  projectId: string;
  name: string;
  color: string;
}

export interface Task {
  id: string;
  key: string;
  projectId: string;
  boardId: string;
  columnId: string;
  title: string;
  description: string;
  type: TaskType;
  priority: Priority;
  assigneeId: string | null;
  labelIds: string[];
  dueDate: string | null;
  position: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  taskId: string;
  authorId: string;
  body: string;
  createdAt: string;
  updatedAt: string;
}

export interface Attachment {
  id: string;
  taskId: string;
  filename: string;
  fileType: string;
  fileSize: number;
  uploadedBy: string;
  uploadedAt: string;
  storageUrl: string;
}

export interface TaskRelation {
  id: string;
  taskId: string;
  relatedTaskId: string;
  type: RelationType;
  createdAt: string;
}

export interface Activity {
  id: string;
  projectId: string;
  taskId: string | null;
  actorId: string;
  message: string;
  createdAt: string;
}

export interface Invitation {
  id: string;
  projectId: string;
  email: string;
  role: Role;
  status: InvitationStatus;
  invitedBy: string;
  createdAt: string;
}

/* ---- view models ---- */

export interface MemberWithUser extends ProjectMember {
  user: User;
}

export interface CommentWithAuthor extends Comment {
  author: User;
}

export interface ActivityWithActor extends Activity {
  actor: User;
}

export interface RelationWithTask extends TaskRelation {
  relatedTask: Task;
}

export interface BoardData {
  board: Board;
  columns: Column[];
  tasks: Task[];
}

export interface TaskFilters {
  search?: string | undefined;
  columnId?: string | undefined;
  assigneeId?: string | undefined;
  priority?: Priority | undefined;
  type?: TaskType | undefined;
  labelId?: string | undefined;
}

export interface DashboardData {
  projects: Project[];
  myTasks: Task[];
  overdueTasks: Task[];
}

/* ---- inputs ---- */

export interface CreateProjectInput {
  name: string;
  key: string;
  description?: string;
}

export interface CreateTaskInput {
  projectId: string;
  boardId: string;
  columnId: string;
  title: string;
  description?: string;
  type?: TaskType;
  priority?: Priority;
  assigneeId?: string | null;
  labelIds?: string[];
  dueDate?: string | null;
}

export type UpdateTaskInput = Partial<
  Pick<
    Task,
    | "title"
    | "description"
    | "type"
    | "priority"
    | "assigneeId"
    | "labelIds"
    | "dueDate"
    | "columnId"
  >
>;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
