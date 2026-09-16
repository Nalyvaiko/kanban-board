import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/avatar";
import { TaskFilterBar } from "@/components/task/task-filter-bar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { qk, useLabels, useMembers } from "@/hooks/use-project-data";
import { formatDate, priorityStyles, typeStyles } from "@/lib/task-meta";
import { api } from "@/services";
import type { TaskFilters } from "@/services";

export const Route = createFileRoute("/projects/$projectId/list")({
  head: () => ({
    meta: [
      { title: "Task list — Mini Jira" },
      { name: "description", content: "All project tasks in a searchable, filterable table." },
      { property: "og:title", content: "Task list — Mini Jira" },
      { property: "og:description", content: "Browse every task with filters for status, assignee, priority and labels." },
    ],
  }),
  component: ListPage,
});

function ListPage() {
  const { projectId } = Route.useParams();
  const navigate = Route.useNavigate();
  const [filters, setFilters] = useState<TaskFilters>({});
  const [debounced, setDebounced] = useState<TaskFilters>({});

  useEffect(() => {
    const t = setTimeout(() => setDebounced(filters), 250);
    return () => clearTimeout(t);
  }, [filters]);

  const { data: tasks = [] } = useQuery({
    queryKey: [...qk.tasks(projectId), debounced],
    queryFn: () => api.listTasks(projectId, debounced),
  });
  const { data: members = [] } = useMembers(projectId);
  const { data: labels = [] } = useLabels(projectId);
  const { data: boards = [] } = useQuery({
    queryKey: qk.boards(projectId),
    queryFn: () => api.listBoards(projectId),
  });
  const { data: boardData } = useQuery({
    queryKey: qk.boardData(boards[0]?.id ?? "none"),
    queryFn: () => api.getBoardData(boards[0]!.id),
    enabled: boards.length > 0,
  });
  const columnName = (columnId: string) =>
    boardData?.columns.find((c) => c.id === columnId)?.name ?? "—";

  return (
    <div className="space-y-4">
      <TaskFilterBar filters={filters} onChange={setFilters} members={members} labels={labels} />

      <div className="surface-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Due</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((t) => {
              const assignee = members.find((m) => m.userId === t.assigneeId)?.user ?? null;
              return (
                <TableRow
                  key={t.id}
                  className="cursor-pointer"
                  onClick={() =>
                    void navigate({ to: ".", search: { task: t.id }, replace: false })
                  }
                >
                  <TableCell className="font-mono text-xs">{t.key}</TableCell>
                  <TableCell className="font-medium">{t.title}</TableCell>
                  <TableCell>
                    <span className={`rounded px-1.5 py-0.5 text-[11px] ${typeStyles[t.type]}`}>
                      {t.type}
                    </span>
                  </TableCell>
                  <TableCell>{columnName(t.columnId)}</TableCell>
                  <TableCell>
                    <span className={`rounded px-1.5 py-0.5 text-[11px] ${priorityStyles[t.priority]}`}>
                      {t.priority}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      <Avatar user={assignee} size={20} />
                      {assignee?.name ?? "Unassigned"}
                    </span>
                  </TableCell>
                  <TableCell>{formatDate(t.dueDate)}</TableCell>
                </TableRow>
              );
            })}
            {tasks.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                  No tasks match your filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
