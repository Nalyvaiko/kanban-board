import { CalendarClock, Bug, Sparkles, SquareCheck } from "lucide-react";

import { Avatar } from "@/components/avatar";
import { formatDate, isOverdue, priorityStyles, typeStyles } from "@/lib/task-meta";
import type { Label, MemberWithUser, Task } from "@/services";

const typeIcon = { task: SquareCheck, bug: Bug, feature: Sparkles } as const;

export function TaskCard({
  task,
  labels,
  members,
  onOpen,
  draggable = false,
  onDragStart,
}: {
  task: Task;
  labels: Label[];
  members: MemberWithUser[];
  onOpen: (taskId: string) => void;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
}) {
  const assignee = members.find((m) => m.userId === task.assigneeId)?.user ?? null;
  const taskLabels = labels.filter((l) => task.labelIds.includes(l.id));
  const Icon = typeIcon[task.type];

  return (
    <article
      draggable={draggable}
      onDragStart={onDragStart}
      onClick={() => onOpen(task.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter") onOpen(task.id);
      }}
      role="button"
      tabIndex={0}
      aria-label={`${task.key} ${task.title}`}
      className="surface-card cursor-pointer space-y-2 p-3 text-left transition-shadow hover:shadow-float focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <p className="text-sm leading-snug font-medium">{task.title}</p>
      {taskLabels.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {taskLabels.map((l) => (
            <span
              key={l.id}
              className="rounded-full px-2 py-0.5 text-[10px] font-medium text-primary-foreground"
              style={{ backgroundColor: l.color }}
            >
              {l.name}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="size-3.5" aria-hidden />
        <span className="font-mono">{task.key}</span>
        <span className={`rounded px-1.5 py-0.5 text-[10px] ${priorityStyles[task.priority]}`}>
          {task.priority}
        </span>
        {task.dueDate && (
          <span
            className={`flex items-center gap-1 text-[11px] ${isOverdue(task.dueDate) ? "text-destructive" : ""}`}
          >
            <CalendarClock className="size-3" />
            {formatDate(task.dueDate)}
          </span>
        )}
        <span className="ml-auto">
          <Avatar user={assignee} size={22} />
        </span>
      </div>
      <span className={`sr-only ${typeStyles[task.type]}`}>{task.type}</span>
    </article>
  );
}
