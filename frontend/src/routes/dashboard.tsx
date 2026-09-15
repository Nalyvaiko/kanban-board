import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, FolderKanban, ListChecks } from "lucide-react";
import { toast } from "sonner";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { qk } from "@/hooks/use-project-data";
import { formatDate, priorityStyles } from "@/lib/task-meta";
import { api } from "@/services";
import type { Task } from "@/services";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Mini Jira" },
      { name: "description", content: "Your projects, assigned tasks and overdue work at a glance." },
      { property: "og:title", content: "Dashboard — Mini Jira" },
      { property: "og:description", content: "See what is assigned to you and what is overdue." },
    ],
  }),
  component: () => (
    <AppShell>
      <DashboardPage />
    </AppShell>
  ),
});

function DashboardPage() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: qk.dashboard, queryFn: () => api.getDashboard() });
  const { data: invitations = [] } = useQuery({
    queryKey: ["my-invitations"],
    queryFn: () => api.listMyInvitations(),
  });

  const accept = useMutation({
    mutationFn: (id: string) => api.acceptInvitation(id),
    onSuccess: () => {
      toast.success("You joined the project");
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold">Dashboard</h1>

      {invitations.length > 0 && (
        <section className="surface-card p-4">
          <h2 className="mb-2 text-sm font-semibold">Pending invitations</h2>
          <ul className="space-y-2">
            {invitations.map((i) => (
              <li key={i.id} className="flex items-center gap-3 text-sm">
                <span>
                  <span className="font-medium">{i.project.name}</span> · {i.role}
                </span>
                <Button size="sm" className="ml-auto" onClick={() => accept.mutate(i.id)}>
                  Join
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="surface-card p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <FolderKanban className="size-4 text-primary" /> My projects
          </h2>
          <ul className="space-y-2">
            {(data?.projects ?? []).map((p) => (
              <li key={p.id}>
                <Link
                  to="/projects/$projectId"
                  params={{ projectId: p.id }}
                  className="block rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-secondary"
                >
                  <span className="font-mono text-xs text-muted-foreground">{p.key}</span>{" "}
                  {p.name}
                </Link>
              </li>
            ))}
            {data?.projects.length === 0 && (
              <li className="text-sm text-muted-foreground">
                No projects yet —{" "}
                <Link to="/projects" className="text-primary hover:underline">
                  create one
                </Link>
                .
              </li>
            )}
          </ul>
        </section>

        <TaskList
          title="My tasks"
          icon={<ListChecks className="size-4 text-primary" />}
          tasks={data?.myTasks ?? []}
          empty="Nothing assigned to you."
        />
        <TaskList
          title="Overdue"
          icon={<AlertTriangle className="size-4 text-destructive" />}
          tasks={data?.overdueTasks ?? []}
          empty="Nothing overdue. Nice."
          overdue
        />
      </div>
    </div>
  );
}

function TaskList({
  title,
  icon,
  tasks,
  empty,
  overdue = false,
}: {
  title: string;
  icon: React.ReactNode;
  tasks: Task[];
  empty: string;
  overdue?: boolean;
}) {
  return (
    <section className="surface-card p-4">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
        {icon} {title}
      </h2>
      <ul className="space-y-2">
        {tasks.map((t) => (
          <li key={t.id}>
            <Link
              to="/projects/$projectId"
              params={{ projectId: t.projectId }}
              search={{ task: t.id }}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-secondary"
            >
              <span className="font-mono text-xs text-muted-foreground">{t.key}</span>
              <span className="truncate">{t.title}</span>
              <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] ${priorityStyles[t.priority]}`}>
                {overdue ? formatDate(t.dueDate) : t.priority}
              </span>
            </Link>
          </li>
        ))}
        {tasks.length === 0 && <li className="text-sm text-muted-foreground">{empty}</li>}
      </ul>
    </section>
  );
}
