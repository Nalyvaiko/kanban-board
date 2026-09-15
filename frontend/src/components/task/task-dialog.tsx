import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Paperclip, Trash2, Link2, Pencil, X } from "lucide-react";
import { toast } from "sonner";

import { Avatar } from "@/components/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { qk, useCanWrite, useLabels, useMembers } from "@/hooks/use-project-data";
import { useAuth } from "@/lib/auth";
import {
  PRIORITIES,
  TASK_TYPES,
  formatBytes,
  formatDateTime,
  isOverdue,
  toDateInput,
} from "@/lib/task-meta";
import { api } from "@/services";
import type { Priority, RelationType, TaskType } from "@/services";

const selectClass =
  "h-9 w-full rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

const RELATION_LABEL: Record<RelationType, string> = {
  blocks: "blocks",
  blocked_by: "is blocked by",
  relates_to: "relates to",
};

export function TaskDetailsDialog({
  taskId,
  projectId,
  onClose,
}: {
  taskId: string | null;
  projectId: string;
  onClose: () => void;
}) {
  const open = taskId !== null;
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        {taskId && <TaskDetails taskId={taskId} projectId={projectId} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function TaskDetails({
  taskId,
  projectId,
  onClose,
}: {
  taskId: string;
  projectId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const canWrite = useCanWrite(projectId);
  const { data: members = [] } = useMembers(projectId);
  const { data: labels = [] } = useLabels(projectId);
  const { data: task } = useQuery({ queryKey: qk.task(taskId), queryFn: () => api.getTask(taskId) });
  const { data: board } = useQuery({
    queryKey: qk.boardData(task?.boardId ?? "none"),
    queryFn: () => api.getBoardData(task!.boardId),
    enabled: !!task,
  });
  const { data: comments = [] } = useQuery({
    queryKey: qk.comments(taskId),
    queryFn: () => api.listComments(taskId),
  });
  const { data: attachments = [] } = useQuery({
    queryKey: qk.attachments(taskId),
    queryFn: () => api.listAttachments(taskId),
  });
  const { data: relations = [] } = useQuery({
    queryKey: qk.relations(taskId),
    queryFn: () => api.listRelations(taskId),
  });
  const { data: activity = [] } = useQuery({
    queryKey: qk.taskActivity(taskId),
    queryFn: () => api.listTaskActivity(taskId),
  });
  const { data: projectTasks = [] } = useQuery({
    queryKey: qk.tasks(projectId),
    queryFn: () => api.listTasks(projectId),
  });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  useEffect(() => {
    if (task) {
      setTitle(task.title);
      setDescription(task.description);
    }
  }, [task?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  function invalidate() {
    void queryClient.invalidateQueries();
  }

  const update = useMutation({
    mutationFn: (patch: Parameters<typeof api.updateTask>[1]) => api.updateTask(taskId, patch),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteTask(taskId),
    onSuccess: () => {
      invalidate();
      toast.success("Task deleted");
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!task) return <p className="p-6 text-sm text-muted-foreground">Loading task…</p>;

  const assignee = members.find((m) => m.userId === task.assigneeId)?.user ?? null;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{task.key}</span>
          <span>·</span>
          <span>created {formatDateTime(task.createdAt)}</span>
          {canWrite && (
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto text-destructive"
              onClick={() => remove.mutate()}
            >
              <Trash2 className="size-4" /> Delete
            </Button>
          )}
        </div>
        <DialogTitle asChild>
          <input
            aria-label="Task title"
            className="mt-1 w-full border-0 bg-transparent font-display text-xl font-semibold focus:outline-none"
            value={title}
            disabled={!canWrite}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={() => title !== task.title && update.mutate({ title })}
          />
        </DialogTitle>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_260px]">
        <div className="space-y-6">
          <section>
            <h3 className="mb-2 text-sm font-semibold">Description</h3>
            <Textarea
              value={description}
              disabled={!canWrite}
              placeholder="Add a description…"
              onChange={(e) => setDescription(e.target.value)}
              onBlur={() => description !== task.description && update.mutate({ description })}
            />
          </section>

          <RelationsSection
            taskId={taskId}
            canWrite={canWrite}
            relations={relations}
            options={projectTasks.filter((t) => t.id !== taskId)}
            onChanged={invalidate}
          />

          <AttachmentsSection
            taskId={taskId}
            canWrite={canWrite}
            attachments={attachments}
            members={members}
            onChanged={invalidate}
          />

          <CommentsSection taskId={taskId} canWrite={canWrite} comments={comments} onChanged={invalidate} />

          <section>
            <h3 className="mb-2 text-sm font-semibold">Activity</h3>
            <ul className="space-y-2">
              {activity.map((a) => (
                <li key={a.id} className="flex items-start gap-2 text-sm">
                  <Avatar user={a.actor} size={22} />
                  <span>
                    <span className="font-medium">{a.actor.name}</span> {a.message}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {formatDateTime(a.createdAt)}
                    </span>
                  </span>
                </li>
              ))}
              {activity.length === 0 && (
                <li className="text-sm text-muted-foreground">No activity yet.</li>
              )}
            </ul>
          </section>
        </div>

        <aside className="space-y-3 rounded-lg border border-border bg-surface p-3">
          <Field label="Status">
            <select
              aria-label="Status"
              className={selectClass}
              disabled={!canWrite}
              value={task.columnId}
              onChange={(e) => update.mutate({ columnId: e.target.value })}
            >
              {(board?.columns ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Type">
            <select
              aria-label="Type"
              className={selectClass}
              disabled={!canWrite}
              value={task.type}
              onChange={(e) => update.mutate({ type: e.target.value as TaskType })}
            >
              {TASK_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Priority">
            <select
              aria-label="Priority"
              className={selectClass}
              disabled={!canWrite}
              value={task.priority}
              onChange={(e) => update.mutate({ priority: e.target.value as Priority })}
            >
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Assignee">
            <select
              aria-label="Assignee"
              className={selectClass}
              disabled={!canWrite}
              value={task.assigneeId ?? ""}
              onChange={(e) => update.mutate({ assigneeId: e.target.value || null })}
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.userId} value={m.userId}>
                  {m.user.name}
                </option>
              ))}
            </select>
            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <Avatar user={assignee} size={20} />
              {assignee?.name ?? "Unassigned"}
            </div>
          </Field>
          <Field label="Due date">
            <Input
              type="date"
              aria-label="Due date"
              disabled={!canWrite}
              className={isOverdue(task.dueDate) ? "border-destructive" : ""}
              value={toDateInput(task.dueDate)}
              onChange={(e) =>
                update.mutate({
                  dueDate: e.target.value ? new Date(e.target.value).toISOString() : null,
                })
              }
            />
          </Field>
          <Field label="Labels">
            <div className="flex flex-wrap gap-1">
              {labels.map((l) => {
                const on = task.labelIds.includes(l.id);
                return (
                  <button
                    key={l.id}
                    type="button"
                    disabled={!canWrite}
                    onClick={() =>
                      update.mutate({
                        labelIds: on
                          ? task.labelIds.filter((id) => id !== l.id)
                          : [...task.labelIds, l.id],
                      })
                    }
                    className={`rounded-full px-2 py-0.5 text-[11px] transition-opacity ${on ? "text-primary-foreground" : "border border-border text-muted-foreground opacity-70"}`}
                    style={on ? { backgroundColor: l.color } : undefined}
                  >
                    {l.name}
                  </button>
                );
              })}
              {labels.length === 0 && (
                <span className="text-xs text-muted-foreground">No labels in this project yet.</span>
              )}
            </div>
          </Field>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </p>
      {children}
    </div>
  );
}

function CommentsSection({
  taskId,
  canWrite,
  comments,
  onChanged,
}: {
  taskId: string;
  canWrite: boolean;
  comments: Awaited<ReturnType<typeof api.listComments>>;
  onChanged: () => void;
}) {
  const { user } = useAuth();
  const [body, setBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const add = useMutation({
    mutationFn: () => api.addComment(taskId, body),
    onSuccess: () => {
      setBody("");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const edit = useMutation({
    mutationFn: (id: string) => api.updateComment(id, draft),
    onSuccess: () => {
      setEditingId(null);
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (id: string) => api.deleteComment(id),
    onSuccess: onChanged,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">Comments</h3>
      <ul className="space-y-3">
        {comments.map((c) => (
          <li key={c.id} className="flex gap-2">
            <Avatar user={c.author} size={26} />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{c.author.name}</span>{" "}
                {formatDateTime(c.createdAt)}
              </p>
              {editingId === c.id ? (
                <div className="mt-1 space-y-2">
                  <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => edit.mutate(c.id)}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{c.body}</p>
              )}
              {user?.id === c.authorId && editingId !== c.id && (
                <div className="mt-1 flex gap-2">
                  <button
                    className="text-xs text-muted-foreground hover:text-foreground"
                    onClick={() => {
                      setEditingId(c.id);
                      setDraft(c.body);
                    }}
                  >
                    <Pencil className="mr-1 inline size-3" />
                    Edit
                  </button>
                  <button
                    className="text-xs text-muted-foreground hover:text-destructive"
                    onClick={() => del.mutate(c.id)}
                  >
                    <Trash2 className="mr-1 inline size-3" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          </li>
        ))}
        {comments.length === 0 && <li className="text-sm text-muted-foreground">No comments yet.</li>}
      </ul>
      {canWrite && (
        <div className="mt-3 space-y-2">
          <Textarea
            aria-label="Add a comment"
            placeholder="Add a comment…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <Button size="sm" disabled={!body.trim()} onClick={() => add.mutate()}>
            Comment
          </Button>
        </div>
      )}
    </section>
  );
}

function AttachmentsSection({
  taskId,
  canWrite,
  attachments,
  members,
  onChanged,
}: {
  taskId: string;
  canWrite: boolean;
  attachments: Awaited<ReturnType<typeof api.listAttachments>>;
  members: Awaited<ReturnType<typeof api.listMembers>>;
  onChanged: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadAttachment(taskId, file),
    onSuccess: () => {
      toast.success("File attached");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (id: string) => api.deleteAttachment(id),
    onSuccess: onChanged,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">Attachments</h3>
      <ul className="space-y-2">
        {attachments.map((a) => (
          <li
            key={a.id}
            className="flex items-center gap-2 rounded-md border border-border px-2 py-1.5 text-sm"
          >
            <Paperclip className="size-4 text-muted-foreground" />
            <span className="truncate">{a.filename}</span>
            <span className="text-xs text-muted-foreground">
              {formatBytes(a.fileSize)} · {members.find((m) => m.userId === a.uploadedBy)?.user.name ?? "someone"}
            </span>
            {canWrite && (
              <button
                className="ml-auto text-muted-foreground hover:text-destructive"
                aria-label={`Remove ${a.filename}`}
                onClick={() => del.mutate(a.id)}
              >
                <X className="size-4" />
              </button>
            )}
          </li>
        ))}
        {attachments.length === 0 && (
          <li className="text-sm text-muted-foreground">No attachments.</li>
        )}
      </ul>
      {canWrite && (
        <>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              e.target.value = "";
            }}
          />
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => fileRef.current?.click()}
          >
            <Paperclip className="size-4" /> Upload file
          </Button>
        </>
      )}
    </section>
  );
}

function RelationsSection({
  taskId,
  canWrite,
  relations,
  options,
  onChanged,
}: {
  taskId: string;
  canWrite: boolean;
  relations: Awaited<ReturnType<typeof api.listRelations>>;
  options: Awaited<ReturnType<typeof api.listTasks>>;
  onChanged: () => void;
}) {
  const [type, setType] = useState<RelationType>("blocks");
  const [related, setRelated] = useState("");

  const add = useMutation({
    mutationFn: () => api.addRelation(taskId, related, type),
    onSuccess: () => {
      setRelated("");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (id: string) => api.deleteRelation(id),
    onSuccess: onChanged,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">Linked tasks</h3>
      <ul className="space-y-2">
        {relations.map((r) => (
          <li key={r.id} className="flex items-center gap-2 text-sm">
            <Link2 className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">{RELATION_LABEL[r.type]}</span>
            <span className="font-mono text-xs">{r.relatedTask.key}</span>
            <span className="truncate">{r.relatedTask.title}</span>
            {canWrite && (
              <button
                className="ml-auto text-muted-foreground hover:text-destructive"
                aria-label="Remove link"
                onClick={() => del.mutate(r.id)}
              >
                <X className="size-4" />
              </button>
            )}
          </li>
        ))}
        {relations.length === 0 && <li className="text-sm text-muted-foreground">No links.</li>}
      </ul>
      {canWrite && (
        <div className="mt-2 flex flex-wrap gap-2">
          <select
            aria-label="Link type"
            className={`${selectClass} w-auto`}
            value={type}
            onChange={(e) => setType(e.target.value as RelationType)}
          >
            <option value="blocks">blocks</option>
            <option value="blocked_by">is blocked by</option>
            <option value="relates_to">relates to</option>
          </select>
          <select
            aria-label="Task to link"
            className={`${selectClass} w-auto max-w-[240px]`}
            value={related}
            onChange={(e) => setRelated(e.target.value)}
          >
            <option value="">Select a task…</option>
            {options.map((t) => (
              <option key={t.id} value={t.id}>
                {t.key} — {t.title}
              </option>
            ))}
          </select>
          <Button size="sm" variant="outline" disabled={!related} onClick={() => add.mutate()}>
            Link
          </Button>
        </div>
      )}
    </section>
  );
}
