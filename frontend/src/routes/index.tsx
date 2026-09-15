import { createFileRoute, Link } from "@tanstack/react-router";
import { KanbanSquare, ListChecks, MessagesSquare, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Mini Jira — Kanban boards for small teams" },
      {
        name: "description",
        content:
          "Create projects, customize Kanban columns, assign tasks, comment, attach files and follow activity history.",
      },
      { property: "og:title", content: "Mini Jira — Kanban boards for small teams" },
      {
        property: "og:description",
        content: "A focused Jira alternative for planning and tracking team work.",
      },
    ],
  }),
  component: Landing,
});

const FEATURES = [
  { icon: KanbanSquare, title: "Custom boards", text: "Columns you define, drag-and-drop cards." },
  { icon: Users, title: "Teams & roles", text: "Admins, members and viewers per project." },
  { icon: MessagesSquare, title: "Discussion", text: "Comments, attachments and task links." },
  { icon: ListChecks, title: "Kanban or list", text: "Switch views, search and filter instantly." },
];

function Landing() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex h-16 max-w-5xl items-center px-4">
        <span className="flex items-center gap-2 font-display font-semibold">
          <span className="brand-gradient flex size-7 items-center justify-center rounded-md text-primary-foreground">
            <KanbanSquare className="size-4" />
          </span>
          Mini Jira
        </span>
        <div className="ml-auto">
          <Button asChild size="sm" variant="outline">
            <Link to={user ? "/dashboard" : "/auth"}>{user ? "Open app" : "Sign in"}</Link>
          </Button>
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h1 className="font-display text-4xl font-semibold text-balance sm:text-5xl">
          Track your team's work without the Jira overhead
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Projects, boards, tasks, comments and activity history — everything a small team needs to
          ship, and nothing it doesn't.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Button asChild size="lg">
            <Link to={user ? "/dashboard" : "/auth"}>{user ? "Go to dashboard" : "Get started"}</Link>
          </Button>
        </div>
      </section>

      <section className="mx-auto grid max-w-5xl gap-4 px-4 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="surface-card p-5">
            <Icon className="size-5 text-primary" />
            <h2 className="mt-3 font-display text-base font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
