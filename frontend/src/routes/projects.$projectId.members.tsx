import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { MailPlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Avatar } from "@/components/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { qk, useMembers, useMyRole } from "@/hooks/use-project-data";
import { useAuth } from "@/lib/auth";
import { api } from "@/services";
import type { Role } from "@/services";

export const Route = createFileRoute("/projects/$projectId/members")({
  head: () => ({
    meta: [
      { title: "Members — Mini Jira" },
      { name: "description", content: "Project members, roles and email invitations." },
      { property: "og:title", content: "Members — Mini Jira" },
      { property: "og:description", content: "Manage who can view and edit this project." },
    ],
  }),
  component: MembersPage,
});

const selectClass =
  "h-9 rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

function MembersPage() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { data: members = [] } = useMembers(projectId);
  const { data: role } = useMyRole(projectId);
  const { data: invitations = [] } = useQuery({
    queryKey: qk.invitations(projectId),
    queryFn: () => api.listInvitations(projectId),
  });
  const isAdmin = role === "admin";

  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("member");

  const invalidate = () => void queryClient.invalidateQueries();
  const onError = (e: Error) => toast.error(e.message);

  const invite = useMutation({
    mutationFn: () => api.inviteUser(projectId, email, inviteRole),
    onSuccess: () => {
      toast.success(`Invitation sent to ${email}`);
      setEmail("");
      invalidate();
    },
    onError,
  });
  const changeRole = useMutation({
    mutationFn: ({ userId, next }: { userId: string; next: Role }) =>
      api.updateMemberRole(projectId, userId, next),
    onSuccess: invalidate,
    onError,
  });
  const remove = useMutation({
    mutationFn: (userId: string) => api.removeMember(projectId, userId),
    onSuccess: invalidate,
    onError,
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api.revokeInvitation(id),
    onSuccess: invalidate,
    onError,
  });

  return (
    <div className="max-w-2xl space-y-6">
      <section className="surface-card p-4">
        <h2 className="mb-3 text-sm font-semibold">Members</h2>
        <ul className="divide-y divide-border">
          {members.map((m) => (
            <li key={m.id} className="flex items-center gap-3 py-2.5">
              <Avatar user={m.user} size={32} />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{m.user.name}</p>
                <p className="truncate text-xs text-muted-foreground">{m.user.email}</p>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <select
                  aria-label={`Role for ${m.user.name}`}
                  className={selectClass}
                  disabled={!isAdmin}
                  value={m.role}
                  onChange={(e) =>
                    changeRole.mutate({ userId: m.userId, next: e.target.value as Role })
                  }
                >
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
                {isAdmin && m.userId !== user?.id && (
                  <button
                    aria-label={`Remove ${m.user.name}`}
                    className="p-1 text-muted-foreground hover:text-destructive"
                    onClick={() => {
                      if (window.confirm(`Remove ${m.user.name} from the project?`))
                        remove.mutate(m.userId);
                    }}
                  >
                    <Trash2 className="size-4" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {isAdmin && (
        <section className="surface-card p-4">
          <h2 className="mb-3 text-sm font-semibold">Invite by email</h2>
          <form
            className="flex flex-wrap gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              invite.mutate();
            }}
          >
            <Input
              type="email"
              required
              aria-label="Invite email"
              placeholder="teammate@example.com"
              className="w-64"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <select
              aria-label="Invite role"
              className={selectClass}
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as Role)}
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
            <Button size="sm" type="submit" disabled={invite.isPending}>
              <MailPlus className="size-4" /> Invite
            </Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">
            If they already have an account, they join on their next visit to the dashboard. New
            users join automatically after registering with that email.
          </p>

          {invitations.filter((i) => i.status === "pending").length > 0 && (
            <ul className="mt-4 space-y-2">
              {invitations
                .filter((i) => i.status === "pending")
                .map((i) => (
                  <li key={i.id} className="flex items-center gap-2 text-sm">
                    <span>{i.email}</span>
                    <span className="rounded-full bg-secondary px-2 text-xs text-muted-foreground">
                      {i.role} · pending
                    </span>
                    <button
                      className="ml-auto text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => revoke.mutate(i.id)}
                    >
                      Revoke
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
