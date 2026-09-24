import { test, expect, type Page } from "@playwright/test";

/**
 * This app's invite model is email-based, not a shareable URL: an admin
 * invites a teammate by email from the project's Members page, and that
 * teammate - once they've registered/signed in with that exact email -
 * sees the project on their dashboard's "Pending invitations" list and
 * clicks Join. There is no link to copy/share. This test drives that real
 * flow end to end, across two independent browser sessions, against the
 * actual docker-compose.yaml stack (see ../global-setup.ts).
 */

const ADMIN_EMAIL = "alice@example.com";
const ADMIN_PASSWORD = "password123";

async function signIn(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/auth");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
}

async function register(page: Page, name: string, email: string, password: string): Promise<void> {
  await page.goto("/auth");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/dashboard");
}

test("admin invites a teammate, teammate joins and edits a task, admin sees the change", async ({
  browser,
}) => {
  const stamp = Date.now();
  const memberEmail = `e2e-member-${stamp}@example.com`;
  const memberPassword = "password123";
  const projectName = `E2E Project ${stamp}`;
  const taskTitle = `E2E Task ${stamp}`;
  const editedTitle = `${taskTitle} (edited by teammate)`;

  // Two independent sessions, each with its own cookies/local storage -
  // the same way two different people in two different browsers would be.
  const adminContext = await browser.newContext();
  const memberContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const member = await memberContext.newPage();

  try {
    // 1. Log in as the admin (a seeded demo account).
    await signIn(admin, ADMIN_EMAIL, ADMIN_PASSWORD);

    // A fresh project keeps this test independent of the exact seed data.
    await admin.goto("/projects");
    await admin.getByRole("button", { name: "New project" }).click();
    await admin.getByLabel("Project name").fill(projectName);
    await admin.getByRole("button", { name: "Create project" }).click();
    await admin.getByRole("link", { name: new RegExp(projectName) }).click();
    await admin.waitForURL(/\/projects\/[^/]+\/board/);

    // 2. Create a task.
    await admin.getByRole("button", { name: "New task" }).click();
    await admin.getByLabel("Task title").fill(taskTitle);
    await admin.getByRole("button", { name: "Create task" }).click();
    await expect(admin.locator('article[role="button"]', { hasText: taskTitle })).toBeVisible();

    // 3. "Share the join link" -> invite the teammate by email (see the
    // module docstring for why this is the real equivalent here).
    await admin.getByRole("link", { name: "Members" }).click();
    await admin.getByLabel("Invite email").fill(memberEmail);
    await admin.getByRole("button", { name: "Invite" }).click();
    // exact: true, since a loose match also catches the (transient) toast
    // notification's "Invitation sent to <email>" text.
    await expect(admin.getByText(memberEmail, { exact: true })).toBeVisible();

    // 4. Join from a separate client as the teammate (session 2).
    await register(member, "E2E Teammate", memberEmail, memberPassword);
    await member.getByRole("button", { name: "Join" }).click();
    await member.getByRole("link", { name: new RegExp(projectName) }).click();
    await member.waitForURL(/\/projects\/[^/]+\/board/);

    // 5. Change the task as the teammate.
    await member.locator('article[role="button"]', { hasText: taskTitle }).click();
    const titleInput = member.getByLabel("Task title");
    await expect(titleInput).toHaveValue(taskTitle);
    await titleInput.fill(editedTitle);
    await member.keyboard.press("Tab"); // blur - the field saves on blur
    await expect(member.getByLabel("Task title")).toHaveValue(editedTitle);
    await member.keyboard.press("Escape"); // close the task dialog

    // 6. The admin sees the change (this app has no live push sync, so a
    // real user would need to refresh too). The admin is still on the
    // Members tab from step 3, so navigate back to the board first.
    // exact: true - a loose match also catches the "Dashboard" nav link.
    await admin.getByRole("link", { name: "Board", exact: true }).click();
    await admin.waitForURL(/\/projects\/[^/]+\/board/);
    await admin.reload();
    await expect(admin.locator('article[role="button"]', { hasText: editedTitle })).toBeVisible();
  } finally {
    await adminContext.close();
    await memberContext.close();
  }
});
