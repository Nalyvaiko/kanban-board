import type { Priority, TaskType } from "@/services";

export const TASK_TYPES: { value: TaskType; label: string }[] = [
  { value: "task", label: "Task" },
  { value: "bug", label: "Bug" },
  { value: "feature", label: "Feature" },
];

export const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

export const typeStyles: Record<TaskType, string> = {
  task: "bg-secondary text-secondary-foreground",
  bug: "bg-destructive/10 text-destructive",
  feature: "bg-success/10 text-success",
};

export const priorityStyles: Record<Priority, string> = {
  low: "bg-secondary text-muted-foreground",
  medium: "bg-primary/10 text-primary",
  high: "bg-warning/15 text-accent-foreground",
  urgent: "bg-destructive/15 text-destructive",
};

/**
 * Due dates are calendar days, stored as midnight UTC of that day (the date
 * picker sends `new Date("YYYY-MM-DD").toISOString()`). Format them in UTC
 * so the day doesn't shift back by one for viewers west of UTC.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** `YYYY-MM-DD` for the viewer's own (local) today. */
function localToday(now: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * A task is overdue once its due *day* has passed - not from the first
 * moment of that day. Compares the due day (UTC, see `formatDate`) against
 * the viewer's local today.
 */
export function isOverdue(iso: string | null, now: Date = new Date()): boolean {
  if (!iso) return false;
  const due = new Date(iso);
  if (Number.isNaN(due.getTime())) return false;
  return due.toISOString().slice(0, 10) < localToday(now);
}

export function toDateInput(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toISOString().slice(0, 10);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
