import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { qk, useLabels, useMyRole, useProject } from "@/hooks/use-project-data";
import { formatDateTime } from "@/lib/task-meta";
import { api } from "@/services";

export const Route = createFileRoute("/projects/$projectId/settings")({
  head: () => ({
    meta: [
      { title: "Project settings — Mini Jira" },
      { name: "description", content: "Rename the project, manage labels and view activity history." },
      { property: "og:title", content: "Project settings — Mini Jira" },
      { property: "og:description", content: "Configure labels and project details." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const { projectId } = Route.useParams();
  const { data: role } = useMyRole(projectId);
  const isAdmin = role === "admin";

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <GeneralSection projectId={projectId} isAdmin={isAdmin} />
        <LabelsSection projectId={projectId} isAdmin={isAdmin} />
        {isAdmin && <DangerZone projectId={projectId} />}
      </div>
      <ActivitySection projectId={projectId} />
    </div>
  );
}

function GeneralSection({ projectId, isAdmin }: { projectId: string; isAdmin: boolean }) {
  const { data: project } = useProject(projectId);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (project) {
      setName(project.name);
      setDescription(project.description);
    }
  }, [project?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () => api.updateProject(projectId, { name, description }),
    onSuccess: () => {
      toast.success("Project updated");
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!project) return null;
  return (
    <section className="surface-card space-y-3 p-4">
      <h2 className="text-sm font-semibold">General</h2>
      <Input
        aria-label="Project name"
        value={name}
        disabled={!isAdmin}
        onChange={(e) => setName(e.target.value)}
      />
      <Textarea
        aria-label="Project description"
        value={description}
        disabled={!isAdmin}
        onChange={(e) => setDescription(e.target.value)}
      />
      {isAdmin && (
        <Button size="sm" disabled={!name.trim()} onClick={() => save.mutate()}>
          Save
        </Button>
      )}
    </section>
  );
}

function LabelsSection({ projectId, isAdmin }: { projectId: string; isAdmin: boolean }) {
  const { data: labels = [] } = useLabels(projectId);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const invalidate = () => void queryClient.invalidateQueries();
  const onError = (e: Error) => toast.error(e.message);

  const create = useMutation({
    mutationFn: () => api.createLabel(projectId, name),
    onSuccess: () => {
      setName("");
      invalidate();
    },
    onError,
  });
  const rename = useMutation({
    mutationFn: ({ id, next }: { id: string; next: string }) => api.renameLabel(id, next),
    onSuccess: invalidate,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteLabel(id),
    onSuccess: invalidate,
    onError,
  });

  return (
    <section className="surface-card space-y-3 p-4">
      <h2 className="text-sm font-semibold">Labels</h2>
      <div className="flex flex-wrap gap-2">
        {labels.map((l) => (
          <span
            key={l.id}
            className="flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium text-primary-foreground"
            style={{ backgroundColor: l.color }}
          >
            {l.name}
            {isAdmin && (
              <>
                <button
                  aria-label={`Rename ${l.name}`}
                  className="opacity-70 hover:opacity-100"
                  onClick={() => {
                    const next = window.prompt("Rename label", l.name);
                    if (next?.trim()) rename.mutate({ id: l.id, next });
                  }}
                >
                  ✎
                </button>
                <button
                  aria-label={`Delete ${l.name}`}
                  className="opacity-70 hover:opacity-100"
                  onClick={() => {
                    if (window.confirm(`Delete label "${l.name}"?`)) remove.mutate(l.id);
                  }}
                >
                  ×
                </button>
              </>
            )}
          </span>
        ))}
        {labels.length === 0 && <p className="text-sm text-muted-foreground">No labels yet.</p>}
      </div>
      {isAdmin && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <Input
            aria-label="New label name"
            placeholder="New label"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Button size="sm" type="submit" disabled={!name.trim()}>
            Add
          </Button>
        </form>
      )}
    </section>
  );
}

function DangerZone({ projectId }: { projectId: string }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => api.deleteProject(projectId),
    onSuccess: () => {
      toast.success("Project deleted");
      void queryClient.invalidateQueries();
      void navigate({ to: "/projects" });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <section className="rounded-lg border border-destructive/40 bg-destructive/5 p-4">
      <h2 className="text-sm font-semibold text-destructive">Danger zone</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Deleting a project removes its boards, tasks, comments and attachments.
      </p>
      <Button
        size="sm"
        variant="destructive"
        className="mt-3"
        onClick={() => {
          if (window.confirm("Delete this project? This cannot be undone.")) remove.mutate();
        }}
      >
        Delete project
      </Button>
    </section>
  );
}

function ActivitySection({ projectId }: { projectId: string }) {
  const { data: activity = [] } = useQuery({
    queryKey: qk.activity(projectId),
    queryFn: () => api.listProjectActivity(projectId),
  });
  return (
    <section className="surface-card p-4">
      <h2 className="mb-3 text-sm font-semibold">Activity history</h2>
      <ul className="space-y-2">
        {activity.map((a) => (
          <li key={a.id} className="text-sm">
            <span className="font-medium">{a.actor.name}</span> {a.message}
            <span className="ml-2 text-xs text-muted-foreground">{formatDateTime(a.createdAt)}</span>
          </li>
        ))}
        {activity.length === 0 && <li className="text-sm text-muted-foreground">No activity yet.</li>}
      </ul>
    </section>
  );
}
