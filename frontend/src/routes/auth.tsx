import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { KanbanSquare } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Mini Jira" },
      { name: "description", content: "Sign in or create a Mini Jira account to manage your projects." },
      { property: "og:title", content: "Sign in — Mini Jira" },
      { property: "og:description", content: "Access your Kanban boards and team projects." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const { user, loading, signIn, signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("demo@minijira.app");
  const [password, setPassword] = useState("password");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) void navigate({ to: "/dashboard", replace: true });
  }, [loading, user, navigate]);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try {
      await fn();
      void navigate({ to: "/dashboard", replace: true });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="surface-card w-full max-w-sm p-6">
        <div className="mb-6 flex items-center gap-2">
          <span className="brand-gradient flex size-8 items-center justify-center rounded-md text-primary-foreground">
            <KanbanSquare className="size-4" />
          </span>
          <h1 className="font-display text-lg font-semibold">
            {mode === "login" ? "Sign in to Mini Jira" : "Create your account"}
          </h1>
        </div>

        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() =>
              mode === "login" ? signIn(email, password) : signUp(name, email, password),
            );
          }}
        >
          {mode === "register" && (
            <div className="space-y-1">
              <Label htmlFor="name">Full name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
          )}
          <div className="space-y-1">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={busy}>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" />
        </div>

        <Button
          variant="outline"
          className="w-full"
          disabled={busy}
          onClick={() => void run(signInWithGoogle)}
        >
          Continue with Google
        </Button>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          {mode === "login" ? "New here?" : "Already have an account?"}{" "}
          <button
            className="font-medium text-primary hover:underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Demo account: demo@minijira.app / password
        </p>
      </div>
    </div>
  );
}
