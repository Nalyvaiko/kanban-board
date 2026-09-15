import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { AppShell } from "@/components/app-shell";
import { Avatar } from "@/components/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { api } from "@/services";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Profile — Mini Jira" },
      { name: "description", content: "Your Mini Jira account details." },
      { property: "og:title", content: "Profile — Mini Jira" },
      { property: "og:description", content: "Update your display name and review your account." },
    ],
  }),
  component: () => (
    <AppShell>
      <ProfilePage />
    </AppShell>
  ),
});

function ProfilePage() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState("");

  useEffect(() => {
    if (user) setName(user.name);
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) return null;

  async function save() {
    try {
      await api.updateProfile({ name });
      await refresh();
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save");
    }
  }

  return (
    <div className="max-w-md space-y-6">
      <h1 className="font-display text-2xl font-semibold">Profile</h1>
      <div className="surface-card space-y-4 p-5">
        <div className="flex items-center gap-3">
          <Avatar user={user} size={48} />
          <div>
            <p className="font-medium">{user.name}</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
          </div>
        </div>
        <div className="space-y-1">
          <Label htmlFor="displayName">Display name</Label>
          <Input id="displayName" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <p className="text-xs text-muted-foreground">
          Signed in with {user.provider === "google" ? "Google" : "email and password"}.
        </p>
        <Button onClick={save} disabled={!name.trim()}>
          Save changes
        </Button>
      </div>
    </div>
  );
}
