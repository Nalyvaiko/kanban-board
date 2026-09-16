import type { JiraApi } from "../api";
import {
  ApiError,
  type Activity,
  type ActivityWithActor,
  type Attachment,
  type Board,
  type BoardData,
  type Column,
  type CommentWithAuthor,
  type CreateProjectInput,
  type CreateTaskInput,
  type DashboardData,
  type Invitation,
  type Label,
  type MemberWithUser,
  type Project,
  type RelationType,
  type RelationWithTask,
  type Role,
  type Task,
  type TaskFilters,
  type UpdateTaskInput,
  type User,
} from "../types";
import { avatarColor, createColumnsForBoard, getDb, nowIso, persist, uid } from "./store";

/** Simulated network latency (ms). Kept tiny so the UI stays snappy. */
const LATENCY = 40;

async function tick<T>(value: T): Promise<T> {
  if (LATENCY > 0) await new Promise((r) => setTimeout(r, LATENCY));
  persist();
  return value;
}

const LABEL_COLORS = [
  "oklch(0.62 0.17 250)",
  "oklch(0.62 0.16 150)",
  "oklch(0.68 0.16 60)",
  "oklch(0.60 0.19 20)",
  "oklch(0.60 0.13 300)",
];

function notFound(what: string): never {
  throw new ApiError(`${what} not found`, 404);
}

function forbidden(message = "You do not have permission to do that"): never {
  throw new ApiError(message, 403);
}

export class MockJiraApi implements JiraApi {
  /* ------------------------------------------------------------------ */
  /* internals                                                           */
  /* ------------------------------------------------------------------ */

  private db() {
    return getDb();
  }

  private session(): User {
    const db = this.db();
    const user = db.users.find((u) => u.id === db.sessionUserId);
    if (!user) throw new ApiError("You must be signed in", 401);
    return user;
  }

  private user(id: string): User {
    return this.db().users.find((u) => u.id === id) ?? notFound("User");
  }

  private role(projectId: string, userId = this.session().id): Role {
    const member = this.db().members.find(
      (m) => m.projectId === projectId && m.userId === userId,
    );
    if (!member) forbidden("You are not a member of this project");
    return member.role;
  }

  /** Any role may read; viewer cannot write; admin-only for configuration. */
  private requireWrite(projectId: string): Role {
    const role = this.role(projectId);
    if (role === "viewer") forbidden("Viewers cannot modify project data");
    return role;
  }

  private requireAdmin(projectId: string): Role {
    const role = this.role(projectId);
    if (role !== "admin") forbidden("Only project admins can do that");
    return role;
  }

  private project(projectId: string): Project {
    return this.db().projects.find((p) => p.id === projectId) ?? notFound("Project");
  }

  private task(taskId: string): Task {
    return this.db().tasks.find((t) => t.id === taskId) ?? notFound("Task");
  }

  private board(boardId: string): Board {
    return this.db().boards.find((b) => b.id === boardId) ?? notFound("Board");
  }

  private column(columnId: string): Column {
    return this.db().columns.find((c) => c.id === columnId) ?? notFound("Column");
  }

  private log(projectId: string, taskId: string | null, message: string): Activity {
    const activity: Activity = {
      id: uid("act"),
      projectId,
      taskId,
      actorId: this.session().id,
      message,
      createdAt: nowIso(),
    };
    this.db().activities.push(activity);
    return activity;
  }

  private withActor = (a: Activity): ActivityWithActor => ({ ...a, actor: this.user(a.actorId) });

  /* ------------------------------------------------------------------ */
  /* auth                                                                */
  /* ------------------------------------------------------------------ */

  async register(input: { name: string; email: string; password: string }): Promise<User> {
    const db = this.db();
    const email = input.email.trim().toLowerCase();
    if (!email.includes("@")) throw new ApiError("Enter a valid email address");
    if (input.password.length < 6) throw new ApiError("Password must be at least 6 characters");
    if (db.users.some((u) => u.email === email))
      throw new ApiError("An account with that email already exists", 409);

    const user: User = {
      id: uid("user"),
      name: input.name.trim() || email.split("@")[0] || "New user",
      email,
      avatarColor: avatarColor(email),
      provider: "password",
      createdAt: nowIso(),
    };
    db.users.push(user);
    db.passwords[email] = input.password;
    db.sessionUserId = user.id;
    this.claimInvitations(user);
    return tick(user);
  }

  async login(input: { email: string; password: string }): Promise<User> {
    const db = this.db();
    const email = input.email.trim().toLowerCase();
    const user = db.users.find((u) => u.email === email);
    if (!user || db.passwords[email] !== input.password)
      throw new ApiError("Incorrect email or password", 401);
    db.sessionUserId = user.id;
    return tick(user);
  }

  async loginWithGoogle(): Promise<User> {
    const db = this.db();
    const email = "demo@minijira.app";
    let user = db.users.find((u) => u.email === email);
    if (!user) {
      user = {
        id: uid("user"),
        name: "Demo User",
        email,
        avatarColor: avatarColor(email),
        provider: "google",
        createdAt: nowIso(),
      };
      db.users.push(user);
    }
    db.sessionUserId = user.id;
    return tick(user);
  }

  async logout(): Promise<void> {
    this.db().sessionUserId = null;
    return tick(undefined);
  }

  async getCurrentUser(): Promise<User | null> {
    const db = this.db();
    return db.users.find((u) => u.id === db.sessionUserId) ?? null;
  }

  async updateProfile(input: { name: string }): Promise<User> {
    const user = this.session();
    user.name = input.name.trim() || user.name;
    return tick(user);
  }

  /** Auto-join projects the new account was invited to. */
  private claimInvitations(user: User) {
    const db = this.db();
    for (const inv of db.invitations) {
      if (inv.status !== "pending" || inv.email !== user.email) continue;
      inv.status = "accepted";
      db.members.push({
        id: uid("pm"),
        projectId: inv.projectId,
        userId: user.id,
        role: inv.role,
        createdAt: nowIso(),
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /* projects                                                            */
  /* ------------------------------------------------------------------ */

  async listProjects(): Promise<Project[]> {
    const me = this.session();
    const db = this.db();
    const ids = db.members.filter((m) => m.userId === me.id).map((m) => m.projectId);
    return tick(db.projects.filter((p) => ids.includes(p.id)));
  }

  async getProject(projectId: string): Promise<Project> {
    this.role(projectId);
    return tick(this.project(projectId));
  }

  async getMyRole(projectId: string): Promise<Role> {
    return tick(this.role(projectId));
  }

  async createProject(input: CreateProjectInput): Promise<Project> {
    const me = this.session();
    const db = this.db();
    const name = input.name.trim();
    if (!name) throw new ApiError("Project name is required");
    const key = (input.key || name.slice(0, 3)).toUpperCase().replace(/[^A-Z0-9]/g, "") || "PRJ";
    if (db.projects.some((p) => p.key === key))
      throw new ApiError("That project key is already in use", 409);

    const project: Project = {
      id: uid("proj"),
      key,
      name,
      description: input.description?.trim() ?? "",
      createdBy: me.id,
      createdAt: nowIso(),
    };
    db.projects.push(project);
    db.members.push({
      id: uid("pm"),
      projectId: project.id,
      userId: me.id,
      role: "admin",
      createdAt: nowIso(),
    });
    db.counters[project.id] = 100;

    const board: Board = {
      id: uid("board"),
      projectId: project.id,
      name: "Main Board",
      createdAt: nowIso(),
    };
    db.boards.push(board);
    db.columns.push(...createColumnsForBoard(board.id));
    this.log(project.id, null, `created project ${project.name}`);
    return tick(project);
  }

  async updateProject(
    projectId: string,
    input: Partial<Pick<Project, "name" | "description">>,
  ): Promise<Project> {
    this.requireAdmin(projectId);
    const project = this.project(projectId);
    if (input.name !== undefined) project.name = input.name.trim() || project.name;
    if (input.description !== undefined) project.description = input.description;
    this.log(projectId, null, "updated project settings");
    return tick(project);
  }

  async deleteProject(projectId: string): Promise<void> {
    this.requireAdmin(projectId);
    const db = this.db();
    const boardIds = db.boards.filter((b) => b.projectId === projectId).map((b) => b.id);
    const taskIds = db.tasks.filter((t) => t.projectId === projectId).map((t) => t.id);
    db.projects = db.projects.filter((p) => p.id !== projectId);
    db.members = db.members.filter((m) => m.projectId !== projectId);
    db.boards = db.boards.filter((b) => b.projectId !== projectId);
    db.columns = db.columns.filter((c) => !boardIds.includes(c.boardId));
    db.labels = db.labels.filter((l) => l.projectId !== projectId);
    db.tasks = db.tasks.filter((t) => t.projectId !== projectId);
    db.comments = db.comments.filter((c) => !taskIds.includes(c.taskId));
    db.attachments = db.attachments.filter((a) => !taskIds.includes(a.taskId));
    db.relations = db.relations.filter(
      (r) => !taskIds.includes(r.taskId) && !taskIds.includes(r.relatedTaskId),
    );
    db.activities = db.activities.filter((a) => a.projectId !== projectId);
    db.invitations = db.invitations.filter((i) => i.projectId !== projectId);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* members & invitations                                               */
  /* ------------------------------------------------------------------ */

  async listMembers(projectId: string): Promise<MemberWithUser[]> {
    this.role(projectId);
    const members = this.db()
      .members.filter((m) => m.projectId === projectId)
      .map((m) => ({ ...m, user: this.user(m.userId) }));
    return tick(members);
  }

  async addMember(projectId: string, email: string, role: Role): Promise<MemberWithUser> {
    this.requireAdmin(projectId);
    const db = this.db();
    const normalized = email.trim().toLowerCase();
    const user = db.users.find((u) => u.email === normalized);
    if (!user) throw new ApiError("No account with that email — send an invitation instead", 404);
    if (db.members.some((m) => m.projectId === projectId && m.userId === user.id))
      throw new ApiError("That user is already a member", 409);
    const member = {
      id: uid("pm"),
      projectId,
      userId: user.id,
      role,
      createdAt: nowIso(),
    };
    db.members.push(member);
    this.log(projectId, null, `added ${user.name} as ${role}`);
    return tick({ ...member, user });
  }

  async updateMemberRole(projectId: string, userId: string, role: Role): Promise<MemberWithUser> {
    this.requireAdmin(projectId);
    const db = this.db();
    const member = db.members.find((m) => m.projectId === projectId && m.userId === userId);
    if (!member) notFound("Member");
    const admins = db.members.filter((m) => m.projectId === projectId && m.role === "admin");
    if (member.role === "admin" && role !== "admin" && admins.length === 1)
      throw new ApiError("A project needs at least one admin");
    member.role = role;
    this.log(projectId, null, `changed ${this.user(userId).name}'s role to ${role}`);
    return tick({ ...member, user: this.user(userId) });
  }

  async removeMember(projectId: string, userId: string): Promise<void> {
    this.requireAdmin(projectId);
    const db = this.db();
    const member = db.members.find((m) => m.projectId === projectId && m.userId === userId);
    if (!member) notFound("Member");
    const admins = db.members.filter((m) => m.projectId === projectId && m.role === "admin");
    if (member.role === "admin" && admins.length === 1)
      throw new ApiError("A project needs at least one admin");
    db.members = db.members.filter((m) => m.id !== member.id);
    for (const task of db.tasks) {
      if (task.projectId === projectId && task.assigneeId === userId) task.assigneeId = null;
    }
    this.log(projectId, null, `removed ${this.user(userId).name} from the project`);
    return tick(undefined);
  }

  async listInvitations(projectId: string): Promise<Invitation[]> {
    this.role(projectId);
    return tick(this.db().invitations.filter((i) => i.projectId === projectId));
  }

  async inviteUser(projectId: string, email: string, role: Role): Promise<Invitation> {
    this.requireAdmin(projectId);
    const db = this.db();
    const normalized = email.trim().toLowerCase();
    if (!normalized.includes("@")) throw new ApiError("Enter a valid email address");
    const existing = db.users.find((u) => u.email === normalized);
    if (existing && db.members.some((m) => m.projectId === projectId && m.userId === existing.id))
      throw new ApiError("That user is already a member", 409);
    if (
      db.invitations.some(
        (i) => i.projectId === projectId && i.email === normalized && i.status === "pending",
      )
    )
      throw new ApiError("An invitation is already pending for that email", 409);

    const invitation: Invitation = {
      id: uid("inv"),
      projectId,
      email: normalized,
      role,
      status: "pending",
      invitedBy: this.session().id,
      createdAt: nowIso(),
    };
    db.invitations.push(invitation);
    this.log(projectId, null, `invited ${normalized} as ${role}`);
    return tick(invitation);
  }

  async revokeInvitation(invitationId: string): Promise<void> {
    const db = this.db();
    const invitation = db.invitations.find((i) => i.id === invitationId);
    if (!invitation) notFound("Invitation");
    this.requireAdmin(invitation.projectId);
    invitation.status = "revoked";
    return tick(undefined);
  }

  async listMyInvitations(): Promise<(Invitation & { project: Project })[]> {
    const me = this.session();
    const db = this.db();
    const list = db.invitations
      .filter((i) => i.status === "pending" && i.email === me.email)
      .map((i) => ({ ...i, project: this.project(i.projectId) }));
    return tick(list);
  }

  async acceptInvitation(invitationId: string): Promise<void> {
    const me = this.session();
    const db = this.db();
    const invitation = db.invitations.find((i) => i.id === invitationId);
    if (!invitation) notFound("Invitation");
    if (invitation.email !== me.email) forbidden("That invitation is for another account");
    invitation.status = "accepted";
    if (!db.members.some((m) => m.projectId === invitation.projectId && m.userId === me.id)) {
      db.members.push({
        id: uid("pm"),
        projectId: invitation.projectId,
        userId: me.id,
        role: invitation.role,
        createdAt: nowIso(),
      });
    }
    this.log(invitation.projectId, null, `joined the project`);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* boards & columns                                                    */
  /* ------------------------------------------------------------------ */

  async listBoards(projectId: string): Promise<Board[]> {
    this.role(projectId);
    return tick(this.db().boards.filter((b) => b.projectId === projectId));
  }

  async createBoard(projectId: string, name: string): Promise<Board> {
    this.requireAdmin(projectId);
    const db = this.db();
    const board: Board = {
      id: uid("board"),
      projectId,
      name: name.trim() || "Board",
      createdAt: nowIso(),
    };
    db.boards.push(board);
    db.columns.push(...createColumnsForBoard(board.id));
    this.log(projectId, null, `created board ${board.name}`);
    return tick(board);
  }

  async deleteBoard(boardId: string): Promise<void> {
    const board = this.board(boardId);
    this.requireAdmin(board.projectId);
    const db = this.db();
    if (db.boards.filter((b) => b.projectId === board.projectId).length === 1)
      throw new ApiError("A project needs at least one board");
    const taskIds = db.tasks.filter((t) => t.boardId === boardId).map((t) => t.id);
    db.boards = db.boards.filter((b) => b.id !== boardId);
    db.columns = db.columns.filter((c) => c.boardId !== boardId);
    db.tasks = db.tasks.filter((t) => t.boardId !== boardId);
    db.comments = db.comments.filter((c) => !taskIds.includes(c.taskId));
    db.attachments = db.attachments.filter((a) => !taskIds.includes(a.taskId));
    return tick(undefined);
  }

  async getBoardData(boardId: string): Promise<BoardData> {
    const board = this.board(boardId);
    this.role(board.projectId);
    const db = this.db();
    return tick({
      board,
      columns: db.columns.filter((c) => c.boardId === boardId).sort((a, b) => a.position - b.position),
      tasks: db.tasks.filter((t) => t.boardId === boardId).sort((a, b) => a.position - b.position),
    });
  }

  async createColumn(boardId: string, name: string): Promise<Column> {
    const board = this.board(boardId);
    this.requireAdmin(board.projectId);
    const db = this.db();
    const siblings = db.columns.filter((c) => c.boardId === boardId);
    const column: Column = {
      id: uid("col"),
      boardId,
      name: name.trim() || "New column",
      position: siblings.length,
    };
    db.columns.push(column);
    this.log(board.projectId, null, `added column "${column.name}"`);
    return tick(column);
  }

  async renameColumn(columnId: string, name: string): Promise<Column> {
    const column = this.column(columnId);
    const board = this.board(column.boardId);
    this.requireAdmin(board.projectId);
    const previous = column.name;
    column.name = name.trim() || column.name;
    this.log(board.projectId, null, `renamed column "${previous}" to "${column.name}"`);
    return tick(column);
  }

  async deleteColumn(columnId: string): Promise<void> {
    const column = this.column(columnId);
    const board = this.board(column.boardId);
    this.requireAdmin(board.projectId);
    const db = this.db();
    const siblings = db.columns
      .filter((c) => c.boardId === column.boardId)
      .sort((a, b) => a.position - b.position);
    if (siblings.length === 1) throw new ApiError("A board needs at least one column");
    const fallback = siblings.find((c) => c.id !== columnId);
    for (const task of db.tasks) {
      if (task.columnId === columnId && fallback) task.columnId = fallback.id;
    }
    db.columns = db.columns.filter((c) => c.id !== columnId);
    db.columns
      .filter((c) => c.boardId === column.boardId)
      .sort((a, b) => a.position - b.position)
      .forEach((c, i) => (c.position = i));
    this.log(board.projectId, null, `deleted column "${column.name}"`);
    return tick(undefined);
  }

  async reorderColumn(columnId: string, position: number): Promise<Column[]> {
    const column = this.column(columnId);
    const board = this.board(column.boardId);
    this.requireAdmin(board.projectId);
    const db = this.db();
    const ordered = db.columns
      .filter((c) => c.boardId === column.boardId)
      .sort((a, b) => a.position - b.position)
      .filter((c) => c.id !== columnId);
    const target = Math.max(0, Math.min(position, ordered.length));
    ordered.splice(target, 0, column);
    ordered.forEach((c, i) => (c.position = i));
    return tick(ordered);
  }

  /* ------------------------------------------------------------------ */
  /* tasks                                                               */
  /* ------------------------------------------------------------------ */

  async listTasks(projectId: string, filters: TaskFilters = {}): Promise<Task[]> {
    this.role(projectId);
    const search = filters.search?.trim().toLowerCase();
    const tasks = this.db()
      .tasks.filter((t) => t.projectId === projectId)
      .filter((t) => (filters.columnId ? t.columnId === filters.columnId : true))
      .filter((t) =>
        filters.assigneeId
          ? filters.assigneeId === "unassigned"
            ? t.assigneeId === null
            : t.assigneeId === filters.assigneeId
          : true,
      )
      .filter((t) => (filters.priority ? t.priority === filters.priority : true))
      .filter((t) => (filters.type ? t.type === filters.type : true))
      .filter((t) => (filters.labelId ? t.labelIds.includes(filters.labelId) : true))
      .filter((t) =>
        search
          ? t.title.toLowerCase().includes(search) ||
            t.key.toLowerCase().includes(search) ||
            t.description.toLowerCase().includes(search)
          : true,
      )
      .sort((a, b) => a.position - b.position);
    return tick(tasks);
  }

  async getTask(taskId: string): Promise<Task> {
    const task = this.task(taskId);
    this.role(task.projectId);
    return tick(task);
  }

  async createTask(input: CreateTaskInput): Promise<Task> {
    this.requireWrite(input.projectId);
    const db = this.db();
    const project = this.project(input.projectId);
    const title = input.title.trim();
    if (!title) throw new ApiError("Task title is required");
    const next = (db.counters[project.id] ?? 100) + 1;
    db.counters[project.id] = next;

    const task: Task = {
      id: uid("task"),
      key: `${project.key}-${next}`,
      projectId: input.projectId,
      boardId: input.boardId,
      columnId: input.columnId,
      title,
      description: input.description?.trim() ?? "",
      type: input.type ?? "task",
      priority: input.priority ?? "medium",
      assigneeId: input.assigneeId ?? null,
      labelIds: input.labelIds ?? [],
      dueDate: input.dueDate ?? null,
      position: db.tasks.filter((t) => t.columnId === input.columnId).length,
      createdBy: this.session().id,
      createdAt: nowIso(),
      updatedAt: nowIso(),
    };
    db.tasks.push(task);
    this.log(task.projectId, task.id, `created ${task.key}`);
    if (task.assigneeId)
      this.log(task.projectId, task.id, `assigned ${task.key} to ${this.user(task.assigneeId).name}`);
    return tick(task);
  }

  async updateTask(taskId: string, input: UpdateTaskInput): Promise<Task> {
    const task = this.task(taskId);
    this.requireWrite(task.projectId);
    const db = this.db();

    if (input.title !== undefined && input.title.trim() && input.title !== task.title) {
      task.title = input.title.trim();
      this.log(task.projectId, task.id, `updated the title of ${task.key}`);
    }
    if (input.description !== undefined && input.description !== task.description) {
      task.description = input.description;
      this.log(task.projectId, task.id, `updated the description of ${task.key}`);
    }
    if (input.type !== undefined && input.type !== task.type) {
      this.log(task.projectId, task.id, `changed type ${task.type} → ${input.type}`);
      task.type = input.type;
    }
    if (input.priority !== undefined && input.priority !== task.priority) {
      this.log(task.projectId, task.id, `changed priority ${task.priority} → ${input.priority}`);
      task.priority = input.priority;
    }
    if (input.assigneeId !== undefined && input.assigneeId !== task.assigneeId) {
      task.assigneeId = input.assigneeId;
      this.log(
        task.projectId,
        task.id,
        input.assigneeId
          ? `assigned ${task.key} to ${this.user(input.assigneeId).name}`
          : `unassigned ${task.key}`,
      );
    }
    if (input.dueDate !== undefined && input.dueDate !== task.dueDate) {
      task.dueDate = input.dueDate;
      this.log(
        task.projectId,
        task.id,
        input.dueDate
          ? `set the due date to ${new Date(input.dueDate).toLocaleDateString()}`
          : `removed the due date`,
      );
    }
    if (input.labelIds !== undefined) {
      const before = new Set(task.labelIds);
      const after = new Set(input.labelIds);
      for (const id of after)
        if (!before.has(id))
          this.log(task.projectId, task.id, `added label "${this.labelName(id)}"`);
      for (const id of before)
        if (!after.has(id))
          this.log(task.projectId, task.id, `removed label "${this.labelName(id)}"`);
      task.labelIds = [...after];
    }
    if (input.columnId !== undefined && input.columnId !== task.columnId) {
      const from = this.column(task.columnId).name;
      const to = this.column(input.columnId).name;
      task.columnId = input.columnId;
      task.position = db.tasks.filter((t) => t.columnId === input.columnId).length;
      this.log(task.projectId, task.id, `moved ${task.key} from ${from} → ${to}`);
    }
    task.updatedAt = nowIso();
    return tick(task);
  }

  private labelName(labelId: string): string {
    return this.db().labels.find((l) => l.id === labelId)?.name ?? "label";
  }

  async moveTask(taskId: string, columnId: string, position?: number): Promise<Task> {
    const task = this.task(taskId);
    this.requireWrite(task.projectId);
    const db = this.db();
    const target = this.column(columnId);
    const changedColumn = task.columnId !== columnId;
    const fromName = this.column(task.columnId).name;

    const siblings = db.tasks
      .filter((t) => t.columnId === columnId && t.id !== taskId)
      .sort((a, b) => a.position - b.position);
    const index = position === undefined ? siblings.length : Math.max(0, Math.min(position, siblings.length));
    task.columnId = columnId;
    siblings.splice(index, 0, task);
    siblings.forEach((t, i) => (t.position = i));
    task.updatedAt = nowIso();

    if (changedColumn)
      this.log(task.projectId, task.id, `moved ${task.key} from ${fromName} → ${target.name}`);
    return tick(task);
  }

  async deleteTask(taskId: string): Promise<void> {
    const task = this.task(taskId);
    this.requireWrite(task.projectId);
    const db = this.db();
    db.tasks = db.tasks.filter((t) => t.id !== taskId);
    db.comments = db.comments.filter((c) => c.taskId !== taskId);
    db.attachments = db.attachments.filter((a) => a.taskId !== taskId);
    db.relations = db.relations.filter((r) => r.taskId !== taskId && r.relatedTaskId !== taskId);
    this.log(task.projectId, null, `deleted ${task.key}`);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* comments                                                            */
  /* ------------------------------------------------------------------ */

  async listComments(taskId: string): Promise<CommentWithAuthor[]> {
    const task = this.task(taskId);
    this.role(task.projectId);
    const comments = this.db()
      .comments.filter((c) => c.taskId === taskId)
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
      .map((c) => ({ ...c, author: this.user(c.authorId) }));
    return tick(comments);
  }

  async addComment(taskId: string, body: string): Promise<CommentWithAuthor> {
    const task = this.task(taskId);
    this.requireWrite(task.projectId);
    const text = body.trim();
    if (!text) throw new ApiError("Comment cannot be empty");
    const me = this.session();
    const comment = {
      id: uid("cmt"),
      taskId,
      authorId: me.id,
      body: text,
      createdAt: nowIso(),
      updatedAt: nowIso(),
    };
    this.db().comments.push(comment);
    this.log(task.projectId, taskId, `commented on ${task.key}`);
    return tick({ ...comment, author: me });
  }

  async updateComment(commentId: string, body: string): Promise<CommentWithAuthor> {
    const db = this.db();
    const comment = db.comments.find((c) => c.id === commentId);
    if (!comment) notFound("Comment");
    const me = this.session();
    const task = this.task(comment.taskId);
    this.role(task.projectId);
    if (comment.authorId !== me.id) forbidden("You can only edit your own comments");
    const text = body.trim();
    if (!text) throw new ApiError("Comment cannot be empty");
    comment.body = text;
    comment.updatedAt = nowIso();
    return tick({ ...comment, author: me });
  }

  async deleteComment(commentId: string): Promise<void> {
    const db = this.db();
    const comment = db.comments.find((c) => c.id === commentId);
    if (!comment) notFound("Comment");
    const me = this.session();
    if (comment.authorId !== me.id) forbidden("You can only delete your own comments");
    db.comments = db.comments.filter((c) => c.id !== commentId);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* attachments                                                         */
  /* ------------------------------------------------------------------ */

  async listAttachments(taskId: string): Promise<Attachment[]> {
    const task = this.task(taskId);
    this.role(task.projectId);
    return tick(this.db().attachments.filter((a) => a.taskId === taskId));
  }

  async uploadAttachment(taskId: string, file: File): Promise<Attachment> {
    const task = this.task(taskId);
    this.requireWrite(task.projectId);
    const MAX = 5 * 1024 * 1024;
    if (file.size > MAX) throw new ApiError("Files must be 5 MB or smaller");
    if (!file.name.trim()) throw new ApiError("Invalid file");

    const attachment: Attachment = {
      id: uid("att"),
      taskId,
      filename: file.name,
      fileType: file.type || "application/octet-stream",
      fileSize: file.size,
      uploadedBy: this.session().id,
      uploadedAt: nowIso(),
      storageUrl: `mock-storage://tasks/${taskId}/${file.name}`,
    };
    this.db().attachments.push(attachment);
    this.log(task.projectId, taskId, `attached ${file.name} to ${task.key}`);
    return tick(attachment);
  }

  async deleteAttachment(attachmentId: string): Promise<void> {
    const db = this.db();
    const attachment = db.attachments.find((a) => a.id === attachmentId);
    if (!attachment) notFound("Attachment");
    const task = this.task(attachment.taskId);
    this.requireWrite(task.projectId);
    db.attachments = db.attachments.filter((a) => a.id !== attachmentId);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* labels                                                              */
  /* ------------------------------------------------------------------ */

  async listLabels(projectId: string): Promise<Label[]> {
    this.role(projectId);
    return tick(this.db().labels.filter((l) => l.projectId === projectId));
  }

  async createLabel(projectId: string, name: string, color?: string): Promise<Label> {
    this.requireAdmin(projectId);
    const db = this.db();
    const clean = name.trim().toLowerCase();
    if (!clean) throw new ApiError("Label name is required");
    if (db.labels.some((l) => l.projectId === projectId && l.name === clean))
      throw new ApiError("That label already exists", 409);
    const label: Label = {
      id: uid("lab"),
      projectId,
      name: clean,
      color: color ?? LABEL_COLORS[db.labels.length % LABEL_COLORS.length] ?? LABEL_COLORS[0]!,
    };
    db.labels.push(label);
    this.log(projectId, null, `created label "${label.name}"`);
    return tick(label);
  }

  async renameLabel(labelId: string, name: string): Promise<Label> {
    const db = this.db();
    const label = db.labels.find((l) => l.id === labelId);
    if (!label) notFound("Label");
    this.requireAdmin(label.projectId);
    label.name = name.trim().toLowerCase() || label.name;
    return tick(label);
  }

  async deleteLabel(labelId: string): Promise<void> {
    const db = this.db();
    const label = db.labels.find((l) => l.id === labelId);
    if (!label) notFound("Label");
    this.requireAdmin(label.projectId);
    db.labels = db.labels.filter((l) => l.id !== labelId);
    for (const task of db.tasks) task.labelIds = task.labelIds.filter((id) => id !== labelId);
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* relations                                                           */
  /* ------------------------------------------------------------------ */

  async listRelations(taskId: string): Promise<RelationWithTask[]> {
    const task = this.task(taskId);
    this.role(task.projectId);
    const list = this.db()
      .relations.filter((r) => r.taskId === taskId)
      .map((r) => ({ ...r, relatedTask: this.task(r.relatedTaskId) }));
    return tick(list);
  }

  async addRelation(
    taskId: string,
    relatedTaskId: string,
    type: RelationType,
  ): Promise<RelationWithTask> {
    const task = this.task(taskId);
    const related = this.task(relatedTaskId);
    this.requireWrite(task.projectId);
    if (taskId === relatedTaskId) throw new ApiError("A task cannot be linked to itself");
    if (task.projectId !== related.projectId)
      throw new ApiError("Tasks must belong to the same project");
    const db = this.db();
    if (db.relations.some((r) => r.taskId === taskId && r.relatedTaskId === relatedTaskId))
      throw new ApiError("Those tasks are already linked", 409);

    const relation = { id: uid("rel"), taskId, relatedTaskId, type, createdAt: nowIso() };
    db.relations.push(relation);
    const inverse: RelationType =
      type === "blocks" ? "blocked_by" : type === "blocked_by" ? "blocks" : "relates_to";
    db.relations.push({
      id: uid("rel"),
      taskId: relatedTaskId,
      relatedTaskId: taskId,
      type: inverse,
      createdAt: nowIso(),
    });
    this.log(task.projectId, taskId, `linked ${task.key} ${type.replace("_", " ")} ${related.key}`);
    return tick({ ...relation, relatedTask: related });
  }

  async deleteRelation(relationId: string): Promise<void> {
    const db = this.db();
    const relation = db.relations.find((r) => r.id === relationId);
    if (!relation) notFound("Relation");
    const task = this.task(relation.taskId);
    this.requireWrite(task.projectId);
    db.relations = db.relations.filter(
      (r) =>
        r.id !== relationId &&
        !(r.taskId === relation.relatedTaskId && r.relatedTaskId === relation.taskId),
    );
    return tick(undefined);
  }

  /* ------------------------------------------------------------------ */
  /* activity & dashboard                                                */
  /* ------------------------------------------------------------------ */

  async listTaskActivity(taskId: string): Promise<ActivityWithActor[]> {
    const task = this.task(taskId);
    this.role(task.projectId);
    const list = this.db()
      .activities.filter((a) => a.taskId === taskId)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .map(this.withActor);
    return tick(list);
  }

  async listProjectActivity(projectId: string): Promise<ActivityWithActor[]> {
    this.role(projectId);
    const list = this.db()
      .activities.filter((a) => a.projectId === projectId)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, 50)
      .map(this.withActor);
    return tick(list);
  }

  async getDashboard(): Promise<DashboardData> {
    const me = this.session();
    const db = this.db();
    const projectIds = db.members.filter((m) => m.userId === me.id).map((m) => m.projectId);
    const projects = db.projects.filter((p) => projectIds.includes(p.id));
    const myTasks = db.tasks.filter(
      (t) => projectIds.includes(t.projectId) && t.assigneeId === me.id,
    );
    const now = Date.now();
    const overdueTasks = myTasks.filter((t) => t.dueDate && new Date(t.dueDate).getTime() < now);
    return tick({ projects, myTasks, overdueTasks });
  }

  async listUsers(): Promise<User[]> {
    this.session();
    return tick(this.db().users);
  }
}
