import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { qk } from "@/hooks/use-project-data";
import { api } from "@/services";

export const Route = createFileRoute("/projects/")({
  head: () => ({
    meta: [
      { title: "Projects — Mini Jira" },
      { name: "description", content: "All projects you belong to, and create new ones." },
      { property: "og:title", content: "Projects — Mini Jira" },
      { property: "og:description", content: "Browse and create Kanban projects for your team." },
    ],
  }),
  component: () => (
    <AppShell>
      <ProjectsPage />
    </AppShell>
  ),
});

function ProjectsPage() {
  const { data: projects = [] } = useQuery({ queryKey: qk.projects, queryFn: () => api.listProjects() });

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <h1 className="font-display text-2xl font-semibold">Projects</h1>
        <div className="ml-auto">
          <CreateProjectDialog />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => (
          <Link
            key={p.id}
            to="/projects/$projectId"
            params={{ projectId: p.id }}
            className="surface-card block p-4 transition-shadow hover:shadow-float"
          >
            <span className="font-mono text-xs text-muted-foreground">{p.key}</span>
            <h2 className="font-display text-base font-semibold">{p.name}</h2>
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
              {p.description || "No description"}
            </p>
          </Link>
        ))}
        {projects.length === 0 && (
          <p className="text-sm text-muted-foreground">No projects yet. Create your first one.</p>
        )}
      </div>
    </div>
  );
}

function CreateProjectDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const create = useMutation({
    mutationFn: () => api.createProject({ name, key, description }),
    onSuccess: (project) => {
      void queryClient.invalidateQueries();
      toast.success(`${project.name} created`);
      setOpen(false);
      setName("");
      setKey("");
      setDescription("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" /> New project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create project</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            aria-label="Project name"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            aria-label="Project key"
            placeholder="Key (e.g. WEB)"
            value={key}
            onChange={(e) => setKey(e.target.value.toUpperCase())}
            maxLength={6}
          />
          <Textarea
            aria-label="Project description"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button className="w-full" disabled={!name.trim()} onClick={() => create.mutate()}>
            Create project
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
