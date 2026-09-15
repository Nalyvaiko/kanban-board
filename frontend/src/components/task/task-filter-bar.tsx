import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PRIORITIES, TASK_TYPES } from "@/lib/task-meta";
import type { Label, MemberWithUser, TaskFilters } from "@/services";

export function TaskFilterBar({
  filters,
  onChange,
  members,
  labels,
}: {
  filters: TaskFilters;
  onChange: (next: TaskFilters) => void;
  members: MemberWithUser[];
  labels: Label[];
}) {
  const set = (patch: Partial<TaskFilters>) => onChange({ ...filters, ...patch });
  const active =
    !!filters.search ||
    !!filters.assigneeId ||
    !!filters.priority ||
    !!filters.type ||
    !!filters.labelId;

  const selectClass =
    "h-9 rounded-md border border-input bg-card px-2 text-sm text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative">
        <Search className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
        <Input
          aria-label="Search tasks"
          placeholder="Search tasks, keys, descriptions"
          className="h-9 w-64 pl-8"
          value={filters.search ?? ""}
          onChange={(e) => set({ search: e.target.value })}
        />
      </div>
      <select
        aria-label="Filter by assignee"
        className={selectClass}
        value={filters.assigneeId ?? ""}
        onChange={(e) => set({ assigneeId: e.target.value || undefined })}
      >
        <option value="">Any assignee</option>
        <option value="unassigned">Unassigned</option>
        {members.map((m) => (
          <option key={m.userId} value={m.userId}>
            {m.user.name}
          </option>
        ))}
      </select>
      <select
        aria-label="Filter by priority"
        className={selectClass}
        value={filters.priority ?? ""}
        onChange={(e) => set({ priority: (e.target.value || undefined) as TaskFilters["priority"] })}
      >
        <option value="">Any priority</option>
        {PRIORITIES.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
      <select
        aria-label="Filter by type"
        className={selectClass}
        value={filters.type ?? ""}
        onChange={(e) => set({ type: (e.target.value || undefined) as TaskFilters["type"] })}
      >
        <option value="">Any type</option>
        {TASK_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <select
        aria-label="Filter by label"
        className={selectClass}
        value={filters.labelId ?? ""}
        onChange={(e) => set({ labelId: e.target.value || undefined })}
      >
        <option value="">Any label</option>
        {labels.map((l) => (
          <option key={l.id} value={l.id}>
            {l.name}
          </option>
        ))}
      </select>
      {active && (
        <Button variant="ghost" size="sm" onClick={() => onChange({})}>
          <X className="size-4" /> Clear
        </Button>
      )}
    </div>
  );
}
