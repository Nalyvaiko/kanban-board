import type {
  Activity,
  Attachment,
  Board,
  Column,
  Comment,
  Invitation,
  Label,
  Project,
  ProjectMember,
  Task,
  TaskRelation,
  User,
} from "../types";

export interface Database {
  users: User[];
  passwords: Record<string, string>;
  projects: Project[];
  members: ProjectMember[];
  boards: Board[];
  columns: Column[];
  labels: Label[];
  tasks: Task[];
  comments: Comment[];
  attachments: Attachment[];
  relations: TaskRelation[];
  activities: Activity[];
  invitations: Invitation[];
  counters: Record<string, number>;
  sessionUserId: string | null;
}

export const STORAGE_KEY = "mini-jira-db-v1";

let seq = 0;
export function uid(prefix = "id"): string {
  seq += 1;
  return `${prefix}_${Date.now().toString(36)}_${seq.toString(36)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

function daysFromNow(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(12, 0, 0, 0);
  return d.toISOString();
}

const AVATAR_COLORS = [
  "oklch(0.62 0.17 250)",
  "oklch(0.62 0.16 150)",
  "oklch(0.68 0.16 60)",
  "oklch(0.60 0.19 20)",
  "oklch(0.60 0.13 300)",
];

export function avatarColor(seed: string): string {
  let n = 0;
  for (const ch of seed) n = (n + ch.charCodeAt(0)) % 997;
  return AVATAR_COLORS[n % AVATAR_COLORS.length] as string;
}

const DEFAULT_COLUMNS = ["To Do", "In Progress", "Review", "Done"];

export function createColumnsForBoard(boardId: string, names = DEFAULT_COLUMNS): Column[] {
  return names.map((name, i) => ({ id: uid("col"), boardId, name, position: i }));
}

/** Deterministic demo dataset so the app is useful on first load. */
export function seedDatabase(): Database {
  const demo: User = {
    id: "user_demo",
    name: "Demo User",
    email: "demo@minijira.app",
    avatarColor: avatarColor("demo@minijira.app"),
    provider: "password",
    createdAt: nowIso(),
  };
  const john: User = {
    id: "user_john",
    name: "John Smith",
    email: "john@example.com",
    avatarColor: avatarColor("john@example.com"),
    provider: "password",
    createdAt: nowIso(),
  };
  const sarah: User = {
    id: "user_sarah",
    name: "Sarah Chen",
    email: "sarah@example.com",
    avatarColor: avatarColor("sarah@example.com"),
    provider: "password",
    createdAt: nowIso(),
  };

  const project: Project = {
    id: "proj_web",
    key: "WEB",
    name: "Website Redesign",
    description: "Marketing site rebuild with a new design system.",
    createdBy: demo.id,
    createdAt: nowIso(),
  };
  const project2: Project = {
    id: "proj_app",
    key: "APP",
    name: "Mobile App",
    description: "iOS and Android client for the platform.",
    createdBy: demo.id,
    createdAt: nowIso(),
  };

  const board: Board = {
    id: "board_web",
    projectId: project.id,
    name: "Main Board",
    createdAt: nowIso(),
  };
  const board2: Board = {
    id: "board_app",
    projectId: project2.id,
    name: "Main Board",
    createdAt: nowIso(),
  };

  const columns = [...createColumnsForBoard(board.id), ...createColumnsForBoard(board2.id)];
  const webCols = columns.filter((c) => c.boardId === board.id);

  const labels: Label[] = [
    { id: "lab_fe", projectId: project.id, name: "frontend", color: "oklch(0.62 0.17 250)" },
    { id: "lab_be", projectId: project.id, name: "backend", color: "oklch(0.62 0.16 150)" },
    { id: "lab_auth", projectId: project.id, name: "authentication", color: "oklch(0.60 0.19 20)" },
    { id: "lab_db", projectId: project.id, name: "database", color: "oklch(0.68 0.16 60)" },
  ];

  const mk = (
    n: number,
    title: string,
    col: number,
    extra: Partial<Task> & { type?: Task["type"] } = {},
  ): Task => ({
    id: `task_${n}`,
    key: `${project.key}-${n}`,
    projectId: project.id,
    boardId: board.id,
    columnId: (webCols[col] ?? webCols[0]!).id,
    title,
    description: "",
    type: "task",
    priority: "medium",
    assigneeId: null,
    labelIds: [],
    dueDate: null,
    position: n,
    createdBy: demo.id,
    createdAt: nowIso(),
    updatedAt: nowIso(),
    ...extra,
  });

  const tasks: Task[] = [
    mk(101, "Fix login validation", 1, {
      type: "bug",
      priority: "high",
      assigneeId: demo.id,
      labelIds: ["lab_fe", "lab_auth"],
      description: "Login validation fails when the email contains a plus sign.",
      dueDate: daysFromNow(4),
    }),
    mk(102, "Add global search", 0, {
      type: "feature",
      priority: "medium",
      assigneeId: sarah.id,
      labelIds: ["lab_fe"],
    }),
    mk(103, "Fix database connection pooling", 0, {
      type: "bug",
      priority: "urgent",
      assigneeId: demo.id,
      labelIds: ["lab_db", "lab_be"],
      dueDate: daysFromNow(-3),
    }),
    mk(104, "Update payment API client", 1, {
      priority: "high",
      assigneeId: john.id,
      labelIds: ["lab_be"],
    }),
    mk(105, "Payment validation rules", 2, {
      type: "feature",
      assigneeId: demo.id,
      labelIds: ["lab_be"],
      dueDate: daysFromNow(9),
    }),
    mk(106, "Polish empty states", 3, { priority: "low", assigneeId: sarah.id }),
  ];

  const relations: TaskRelation[] = [
    {
      id: uid("rel"),
      taskId: "task_101",
      relatedTaskId: "task_105",
      type: "blocks",
      createdAt: nowIso(),
    },
  ];

  const comments: Comment[] = [
    {
      id: uid("cmt"),
      taskId: "task_101",
      authorId: john.id,
      body: "I found the problem in the API — the regex rejects plus addressing.",
      createdAt: nowIso(),
      updatedAt: nowIso(),
    },
  ];

  const activities: Activity[] = tasks.map((t) => ({
    id: uid("act"),
    projectId: t.projectId,
    taskId: t.id,
    actorId: t.createdBy,
    message: `created ${t.key}`,
    createdAt: t.createdAt,
  }));

  return {
    users: [demo, john, sarah],
    passwords: { [demo.email]: "password", [john.email]: "password", [sarah.email]: "password" },
    projects: [project, project2],
    members: [
      {
        id: uid("pm"),
        projectId: project.id,
        userId: demo.id,
        role: "admin",
        createdAt: nowIso(),
      },
      { id: uid("pm"), projectId: project.id, userId: john.id, role: "member", createdAt: nowIso() },
      {
        id: uid("pm"),
        projectId: project.id,
        userId: sarah.id,
        role: "member",
        createdAt: nowIso(),
      },
      {
        id: uid("pm"),
        projectId: project2.id,
        userId: demo.id,
        role: "admin",
        createdAt: nowIso(),
      },
    ],
    boards: [board, board2],
    columns,
    labels,
    tasks,
    comments,
    attachments: [],
    relations,
    activities,
    invitations: [],
    counters: { [project.id]: 106, [project2.id]: 100 },
    sessionUserId: null,
  };
}

function isBrowser() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

let db: Database | null = null;

export function getDb(): Database {
  if (db) return db;
  if (isBrowser()) {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        db = JSON.parse(raw) as Database;
        return db;
      } catch {
        /* fall through to a fresh seed */
      }
    }
  }
  db = seedDatabase();
  persist();
  return db;
}

export function persist(): void {
  if (!db || !isBrowser()) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    /* storage full or unavailable — keep the in-memory copy */
  }
}

/** Test/helper hook: start over from the seeded dataset. */
export function resetDb(next?: Database): Database {
  db = next ?? seedDatabase();
  persist();
  return db;
}
