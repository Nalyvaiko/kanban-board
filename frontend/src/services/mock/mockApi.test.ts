import { beforeEach, describe, expect, it } from "vitest";

import { MockJiraApi } from "./mockApi";
import { resetDb } from "./store";
import { ApiError } from "../types";

let api: MockJiraApi;

/** Sign in as the seeded demo admin. */
async function asDemo() {
  await api.login({ email: "demo@minijira.app", password: "password" });
}

async function asJohn() {
  await api.login({ email: "john@example.com", password: "password" });
}

async function asSarah() {
  await api.login({ email: "sarah@example.com", password: "password" });
}

beforeEach(() => {
  resetDb();
  api = new MockJiraApi();
});

describe("authentication", () => {
  it("registers a new user and starts a session", async () => {
    const user = await api.register({
      name: "Ada Lovelace",
      email: "ada@example.com",
      password: "secret1",
    });
    expect(user.email).toBe("ada@example.com");
    expect(await api.getCurrentUser()).toMatchObject({ email: "ada@example.com" });
  });

  it("rejects duplicate registration", async () => {
    await expect(
      api.register({ name: "Copy", email: "demo@minijira.app", password: "secret1" }),
    ).rejects.toThrow(ApiError);
  });

  it("rejects wrong password", async () => {
    await expect(
      api.login({ email: "demo@minijira.app", password: "nope" }),
    ).rejects.toThrow("Incorrect email or password");
  });

  it("blocks all access when signed out", async () => {
    await expect(api.listProjects()).rejects.toThrow(ApiError);
  });

  it("logs out", async () => {
    await asDemo();
    await api.logout();
    expect(await api.getCurrentUser()).toBeNull();
  });
});

describe("projects & permissions", () => {
  it("creates a project with the creator as admin and a default board", async () => {
    await asDemo();
    const project = await api.createProject({ name: "Internal Tools", key: "IT" });
    expect(await api.getMyRole(project.id)).toBe("admin");
    const boards = await api.listBoards(project.id);
    expect(boards).toHaveLength(1);
    const data = await api.getBoardData(boards[0]!.id);
    expect(data.columns.map((c) => c.name)).toEqual(["To Do", "In Progress", "Review", "Done"]);
  });

  it("rejects duplicate project keys", async () => {
    await asDemo();
    await expect(api.createProject({ name: "Web 2", key: "WEB" })).rejects.toThrow(ApiError);
  });

  it("non-members cannot see the project", async () => {
    await api.register({ name: "Outsider", email: "out@example.com", password: "secret1" });
    await expect(api.getProject("proj_web")).rejects.toMatchObject({ status: 403 });
  });

  it("viewers cannot create tasks", async () => {
    await asDemo();
    await api.updateMemberRole("proj_web", "user_john", "viewer");
    await asJohn();
    const boards = await api.listBoards("proj_web");
    const data = await api.getBoardData(boards[0]!.id);
    await expect(
      api.createTask({
        projectId: "proj_web",
        boardId: data.board.id,
        columnId: data.columns[0]!.id,
        title: "Viewer attempt",
      }),
    ).rejects.toMatchObject({ status: 403 });
  });

  it("members cannot manage other members", async () => {
    await asJohn();
    await expect(api.removeMember("proj_web", "user_sarah")).rejects.toMatchObject({ status: 403 });
    await expect(api.createColumn("board_web", "QA")).rejects.toMatchObject({ status: 403 });
  });

  it("cannot demote the last admin", async () => {
    await asDemo();
    await expect(api.updateMemberRole("proj_web", "user_demo", "member")).rejects.toThrow(
      "at least one admin",
    );
  });
});

describe("invitations", () => {
  it("invited user joins automatically after registering", async () => {
    await asDemo();
    await api.inviteUser("proj_web", "new@example.com", "member");
    await api.logout();
    await api.register({ name: "New Hire", email: "new@example.com", password: "secret1" });
    const projects = await api.listProjects();
    expect(projects.map((p) => p.id)).toContain("proj_web");
    expect(await api.getMyRole("proj_web")).toBe("member");
  });

  it("existing user accepts an invitation from the dashboard list", async () => {
    await asDemo();
    await api.inviteUser("proj_app", "sarah@example.com", "member");
    await api.logout();
    await api.login({ email: "sarah@example.com", password: "password" });
    const [inv] = await api.listMyInvitations();
    await api.acceptInvitation(inv!.id);
    expect(await api.getMyRole("proj_app")).toBe("member");
  });
});

describe("tasks", () => {
  it("creates tasks with incrementing keys", async () => {
    await asDemo();
    const data = await api.getBoardData("board_web");
    const task = await api.createTask({
      projectId: "proj_web",
      boardId: "board_web",
      columnId: data.columns[0]!.id,
      title: "New work",
      type: "bug",
      priority: "high",
    });
    expect(task.key).toBe("WEB-107");
    expect(task.type).toBe("bug");
  });

  it("moves tasks between columns and logs activity", async () => {
    await asDemo();
    const data = await api.getBoardData("board_web");
    const review = data.columns.find((c) => c.name === "Review")!;
    const moved = await api.moveTask("task_101", review.id);
    expect(moved.columnId).toBe(review.id);
    const activity = await api.listTaskActivity("task_101");
    expect(activity.some((a) => a.message.includes("In Progress → Review"))).toBe(true);
  });

  it("updates fields and records history", async () => {
    await asDemo();
    await api.updateTask("task_101", { priority: "urgent", assigneeId: "user_sarah" });
    const task = await api.getTask("task_101");
    expect(task.priority).toBe("urgent");
    expect(task.assigneeId).toBe("user_sarah");
    const activity = await api.listTaskActivity("task_101");
    expect(activity.some((a) => a.message.includes("high → urgent"))).toBe(true);
    expect(activity.some((a) => a.message.includes("assigned"))).toBe(true);
  });

  it("searches by title, key and description", async () => {
    await asDemo();
    const results = await api.listTasks("proj_web", { search: "payment" });
    expect(results.map((t) => t.key).sort()).toEqual(["WEB-104", "WEB-105"]);
    const byKey = await api.listTasks("proj_web", { search: "WEB-101" });
    expect(byKey).toHaveLength(1);
  });

  it("filters by priority, type, assignee and label", async () => {
    await asDemo();
    const urgent = await api.listTasks("proj_web", { priority: "urgent" });
    expect(urgent.map((t) => t.key)).toEqual(["WEB-103"]);
    const bugs = await api.listTasks("proj_web", { type: "bug" });
    expect(bugs).toHaveLength(2);
    const mine = await api.listTasks("proj_web", { assigneeId: "user_demo" });
    expect(mine.length).toBeGreaterThan(0);
    const dbLabel = await api.listTasks("proj_web", { labelId: "lab_db" });
    expect(dbLabel.map((t) => t.key)).toEqual(["WEB-103"]);
  });
});

describe("comments", () => {
  it("adds and lists comments", async () => {
    await asDemo();
    await api.addComment("task_101", "On it");
    const comments = await api.listComments("task_101");
    expect(comments).toHaveLength(2);
  });

  it("only the author can edit a comment", async () => {
    await asDemo();
    const comments = await api.listComments("task_101");
    const johns = comments.find((c) => c.authorId === "user_john")!;
    await expect(api.updateComment(johns.id, "hijack")).rejects.toMatchObject({ status: 403 });
    await asJohn();
    const updated = await api.updateComment(johns.id, "Fixed the regex");
    expect(updated.body).toBe("Fixed the regex");
  });

  it("only the author or a project admin can delete a comment", async () => {
    await asDemo();
    const comments = await api.listComments("task_101");
    const johns = comments.find((c) => c.authorId === "user_john")!;
    await asSarah();
    await expect(api.deleteComment(johns.id)).rejects.toMatchObject({ status: 403 });
    await asJohn();
    await api.deleteComment(johns.id);
    expect(await api.listComments("task_101")).toHaveLength(0);
  });

  it("a project admin can delete another member's comment", async () => {
    await asJohn();
    const added = await api.addComment("task_101", "Draft note");
    await asDemo();
    await api.deleteComment(added.id);
    expect(await api.listComments("task_101")).not.toContainEqual(
      expect.objectContaining({ id: added.id }),
    );
  });
});

describe("columns & labels", () => {
  it("creates, renames, reorders and deletes columns", async () => {
    await asDemo();
    const qa = await api.createColumn("board_web", "QA");
    await api.renameColumn(qa.id, "QA / Verify");
    const reordered = await api.reorderColumn(qa.id, 0);
    expect(reordered[0]!.name).toBe("QA / Verify");
    await api.deleteColumn(qa.id);
    const data = await api.getBoardData("board_web");
    expect(data.columns.find((c) => c.id === qa.id)).toBeUndefined();
  });

  it("moving column tasks fall back when a column is deleted", async () => {
    await asDemo();
    const data = await api.getBoardData("board_web");
    const done = data.columns.find((c) => c.name === "Done")!;
    await api.deleteColumn(done.id);
    const task = await api.getTask("task_106");
    expect(task.columnId).not.toBe(done.id);
  });

  it("admins manage labels; deleting removes it from tasks", async () => {
    await asDemo();
    const label = await api.createLabel("proj_web", "ops");
    await api.updateTask("task_101", { labelIds: [label.id] });
    await api.deleteLabel(label.id);
    const task = await api.getTask("task_101");
    expect(task.labelIds).not.toContain(label.id);
  });

  it("members cannot create labels", async () => {
    await asJohn();
    await expect(api.createLabel("proj_web", "x")).rejects.toMatchObject({ status: 403 });
  });
});

describe("relations", () => {
  it("creates bidirectional links", async () => {
    await asDemo();
    await api.addRelation("task_101", "task_102", "blocks");
    const forward = await api.listRelations("task_101");
    const backward = await api.listRelations("task_102");
    expect(forward.some((r) => r.relatedTaskId === "task_102" && r.type === "blocks")).toBe(true);
    expect(backward.some((r) => r.relatedTaskId === "task_101" && r.type === "blocked_by")).toBe(
      true,
    );
  });

  it("rejects self-links and duplicates", async () => {
    await asDemo();
    await expect(api.addRelation("task_101", "task_101", "relates_to")).rejects.toThrow(
      "itself",
    );
    await expect(api.addRelation("task_101", "task_105", "relates_to")).rejects.toThrow(
      "already linked",
    );
  });
});

describe("dashboard", () => {
  it("shows assigned and overdue tasks", async () => {
    await asDemo();
    const dash = await api.getDashboard();
    expect(dash.projects.length).toBeGreaterThan(0);
    expect(dash.myTasks.every((t) => t.assigneeId === "user_demo")).toBe(true);
    expect(dash.overdueTasks.map((t) => t.key)).toContain("WEB-103");
  });
});
