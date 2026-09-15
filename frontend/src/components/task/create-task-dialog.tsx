import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

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
import { useLabels, useMembers } from "@/hooks/use-project-data";
import { PRIORITIES, TASK_TYPES } from "@/lib/task-meta";
import { api } from "@/services";
import type { Column, Priority, TaskType } from "@/services";

const selectClass =
  "h-9 w-full rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function CreateTaskDialog({
  projectId,
  boardId,
  columns,
  defaultColumnId,
  trigger,
}: {
  projectId: string;
  boardId: string;
  columns: Column[];
  defaultColumnId?: string;
  trigger?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<TaskType>("task");
  const [priority, setPriority] = useState<Priority>("medium");
  const [assigneeId, setAssigneeId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [labelIds, setLabelIds] = useState<string[]>([]);
  const [columnId, setColumnId] = useState(defaultColumnId ?? columns[0]?.id ?? "");

  const queryClient = useQueryClient();
  const { data: members = [] } = useMembers(projectId);
  const { data: labels = [] } = useLabels(projectId);

  const create = useMutation({
    mutationFn: () =>
      api.createTask({
        projectId,
        boardId,
        columnId: columnId || columns[0]?.id || "",
        title,
        description,
        type,
        priority,
        assigneeId: assigneeId || null,
        labelIds,
        dueDate: dueDate ? new Date(dueDate).toISOString() : null,
      }),
    onSuccess: (task) => {
      void queryClient.invalidateQueries();
      toast.success(`${task.key} created`);
      setOpen(false);
      setTitle("");
      setDescription("");
      setLabelIds([]);
      setDueDate("");
      setAssigneeId("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button size="sm">
            <Plus className="size-4" /> New task
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create task</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            autoFocus
            aria-label="Task title"
            placeholder="Task title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Textarea
            aria-label="Task description"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              aria-label="Column"
              className={selectClass}
              value={columnId}
              onChange={(e) => setColumnId(e.target.value)}
            >
              {columns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Type"
              className={selectClass}
              value={type}
              onChange={(e) => setType(e.target.value as TaskType)}
            >
              {TASK_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <select
              aria-label="Priority"
              className={selectClass}
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority)}
            >
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <select
              aria-label="Assignee"
              className={selectClass}
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.userId} value={m.userId}>
                  {m.user.name}
                </option>
              ))}
            </select>
          </div>
          <Input
            type="date"
            aria-label="Due date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
          <div className="flex flex-wrap gap-1">
            {labels.map((l) => {
              const on = labelIds.includes(l.id);
              return (
                <button
                  key={l.id}
                  type="button"
                  onClick={() =>
                    setLabelIds(on ? labelIds.filter((id) => id !== l.id) : [...labelIds, l.id])
                  }
                  className={`rounded-full px-2 py-0.5 text-[11px] ${on ? "text-primary-foreground" : "border border-border text-muted-foreground"}`}
                  style={on ? { backgroundColor: l.color } : undefined}
                >
                  {l.name}
                </button>
              );
            })}
          </div>
          <Button
            className="w-full"
            disabled={!title.trim() || create.isPending}
            onClick={() => create.mutate()}
          >
            Create task
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
