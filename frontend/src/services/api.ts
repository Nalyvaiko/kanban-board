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
} from "./types";

/**
 * Single interface for every backend call in the application.
 * The UI never talks to a data source directly — only through this contract,
 * so the mock implementation can be swapped for a real HTTP client.
 */
export interface JiraApi {
  // Authentication
  register(input: { name: string; email: string; password: string }): Promise<User>;
  login(input: { email: string; password: string }): Promise<User>;
  loginWithGoogle(): Promise<User>;
  logout(): Promise<void>;
  getCurrentUser(): Promise<User | null>;
  updateProfile(input: { name: string }): Promise<User>;

  // Projects
  listProjects(): Promise<Project[]>;
  getProject(projectId: string): Promise<Project>;
  createProject(input: CreateProjectInput): Promise<Project>;
  updateProject(
    projectId: string,
    input: Partial<Pick<Project, "name" | "description">>,
  ): Promise<Project>;
  deleteProject(projectId: string): Promise<void>;
  getMyRole(projectId: string): Promise<Role>;

  // Members & invitations
  listMembers(projectId: string): Promise<MemberWithUser[]>;
  addMember(projectId: string, email: string, role: Role): Promise<MemberWithUser>;
  updateMemberRole(projectId: string, userId: string, role: Role): Promise<MemberWithUser>;
  removeMember(projectId: string, userId: string): Promise<void>;
  listInvitations(projectId: string): Promise<Invitation[]>;
  inviteUser(projectId: string, email: string, role: Role): Promise<Invitation>;
  revokeInvitation(invitationId: string): Promise<void>;
  listMyInvitations(): Promise<(Invitation & { project: Project })[]>;
  acceptInvitation(invitationId: string): Promise<void>;

  // Boards & columns
  listBoards(projectId: string): Promise<Board[]>;
  createBoard(projectId: string, name: string): Promise<Board>;
  deleteBoard(boardId: string): Promise<void>;
  getBoardData(boardId: string): Promise<BoardData>;
  createColumn(boardId: string, name: string): Promise<Column>;
  renameColumn(columnId: string, name: string): Promise<Column>;
  deleteColumn(columnId: string): Promise<void>;
  reorderColumn(columnId: string, position: number): Promise<Column[]>;

  // Tasks
  listTasks(projectId: string, filters?: TaskFilters): Promise<Task[]>;
  getTask(taskId: string): Promise<Task>;
  createTask(input: CreateTaskInput): Promise<Task>;
  updateTask(taskId: string, input: UpdateTaskInput): Promise<Task>;
  moveTask(taskId: string, columnId: string, position?: number): Promise<Task>;
  deleteTask(taskId: string): Promise<void>;

  // Comments
  listComments(taskId: string): Promise<CommentWithAuthor[]>;
  addComment(taskId: string, body: string): Promise<CommentWithAuthor>;
  updateComment(commentId: string, body: string): Promise<CommentWithAuthor>;
  deleteComment(commentId: string): Promise<void>;

  // Attachments
  listAttachments(taskId: string): Promise<Attachment[]>;
  uploadAttachment(taskId: string, file: File): Promise<Attachment>;
  deleteAttachment(attachmentId: string): Promise<void>;

  // Labels
  listLabels(projectId: string): Promise<Label[]>;
  createLabel(projectId: string, name: string, color?: string): Promise<Label>;
  renameLabel(labelId: string, name: string): Promise<Label>;
  deleteLabel(labelId: string): Promise<void>;

  // Relations
  listRelations(taskId: string): Promise<RelationWithTask[]>;
  addRelation(taskId: string, relatedTaskId: string, type: RelationType): Promise<TaskRelationView>;
  deleteRelation(relationId: string): Promise<void>;

  // Activity
  listTaskActivity(taskId: string): Promise<ActivityWithActor[]>;
  listProjectActivity(projectId: string): Promise<ActivityWithActor[]>;

  // Dashboard
  getDashboard(): Promise<DashboardData>;

  // Users
  listUsers(): Promise<User[]>;
}

export type TaskRelationView = RelationWithTask;
export type { Activity };
