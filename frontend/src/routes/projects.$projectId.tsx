import { createFileRoute, Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Columns3, ListTodo, Settings, Users } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { TaskDetailsDialog } from "@/components/task/task-dialog";
import { useProject } from "@/hooks/use-project-data";

export const Route = createFileRoute("/projects/$projectId")({
  validateSearch: (search: Record<string, unknown>): { task?: string | undefined } => ({
    task: typeof search["task"] === "string" ? (search["task"] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Project — Mini Jira" },
      { name: "description", content: "Kanban board, task list, members and project settings." },
      { property: "og:title", content: "Project — Mini Jira" },
      { property: "og:description", content: "Track tasks, team members and activity in this project." },
    ],
  }),
  component: () => (
    <AppShell>
      <ProjectLayout />
    </AppShell>
  ),
});

const TABS = [
  { to: "/projects/$projectId/board", label: "Board", icon: Columns3 },
  { to: "/projects/$projectId/list", label: "List", icon: ListTodo },
  { to: "/projects/$projectId/members", label: "Members", icon: Users },
  { to: "/projects/$projectId/settings", label: "Settings", icon: Settings },
] as const;

function ProjectLayout() {
  const { projectId } = Route.useParams();
  const { task } = Route.useSearch();
  const navigate = useNavigate();
  const { data: project } = useProject(projectId);

  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-xs text-muted-foreground">{project?.key}</p>
        <h1 className="font-display text-2xl font-semibold">{project?.name ?? "Project"}</h1>
        {project?.description && (
          <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
        )}
      </div>

      <nav className="flex gap-1 border-b border-border" aria-label="Project sections">
        {TABS.map(({ to, label, icon: Icon }) => (
          <Link
            key={label}
            to={to}
            params={{ projectId }}
            search={{}}
            className="flex items-center gap-2 border-b-2 border-transparent px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            activeProps={{ className: "border-primary text-foreground" }}
            activeOptions={{ exact: true }}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        ))}
      </nav>

      <Outlet />

      <TaskDetailsDialog
        taskId={task ?? null}
        projectId={projectId}
        onClose={() =>
          void navigate({ to: ".", search: {}, params: { projectId }, replace: true })
        }
      />
    </div>
  );
}
