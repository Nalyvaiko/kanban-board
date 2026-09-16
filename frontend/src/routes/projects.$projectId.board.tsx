import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { GripVertical, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { CreateTaskDialog } from "@/components/task/create-task-dialog";
import { TaskCard } from "@/components/task/task-card";
import { TaskFilterBar } from "@/components/task/task-filter-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  qk,
  useBoards,
  useCanWrite,
  useLabels,
  useMembers,
  useMyRole,
} from "@/hooks/use-project-data";
import { api } from "@/services";
import type { Column, TaskFilters } from "@/services";

export const Route = createFileRoute("/projects/$projectId/board")({
  head: () => ({
    meta: [
      { title: "Board — Mini Jira" },
      { name: "description", content: "Kanban board with drag-and-drop task cards." },
      { property: "og:title", content: "Board — Mini Jira" },
      { property: "og:description", content: "Move work across customizable Kanban columns." },
    ],
  }),
  component: BoardPage,
});

function BoardPage() {
  const { projectId } = Route.useParams();
  const navigate = Route.useNavigate();
  const queryClient = useQueryClient();
  const { data: boards = [] } = useBoards(projectId);
  const [boardId, setBoardId] = useState<string | null>(null);
  const board = boards.find((b) => b.id === boardId) ?? boards[0];
  const { data: boardData } = useQuery({
    queryKey: qk.boardData(board?.id ?? "none"),
    queryFn: () => api.getBoardData(board!.id),
    enabled: !!board,
  });
  const { data: members = [] } = useMembers(projectId);
  const { data: labels = [] } = useLabels(projectId);
  const { data: role } = useMyRole(projectId);
  const canWrite = useCanWrite(projectId);
  const [filters, setFilters] = useState<TaskFilters>({});
  const [overColumn, setOverColumn] = useState<string | null>(null);

  const move = useMutation({
    mutationFn: ({ taskId, columnId }: { taskId: string; columnId: string }) =>
      api.moveTask(taskId, columnId),
    onSuccess: () => void queryClient.invalidateQueries(),
    onError: (e: Error) => toast.error(e.message),
  });

  const createBoard = useMutation({
    mutationFn: (name: string) => api.createBoard(projectId, name),
    onSuccess: (b) => {
      setBoardId(b.id);
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const filteredTasks = useMemo(() => {
    const all = boardData?.tasks ?? [];
    const search = filters.search?.trim().toLowerCase();
    return all
      .filter((t) =>
        filters.assigneeId
          ? filters.assigneeId === "unassigned"
            ? t.assigneeId === null
            : t.assigneeId === filters.assigneeId
          : true,
      )
      .filter((t) => (filters.priority ? t.priority === filters.priority : true))
      .filter((t) => (filters.type ? t.type === filters.type : true))
      .filter((t) => (filters.labelId ? t.labelIds.includes(filters.labelId) : true))
      .filter((t) =>
        search
          ? t.title.toLowerCase().includes(search) ||
            t.key.toLowerCase().includes(search) ||
            t.description.toLowerCase().includes(search)
          : true,
      );
  }, [boardData?.tasks, filters]);

  const openTask = (taskId: string) =>
    void navigate({ to: ".", search: { task: taskId }, replace: false });

  if (boards.length === 0) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const selectClass =
    "h-9 rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label="Board"
          className={selectClass}
          value={board?.id ?? ""}
          onChange={(e) => setBoardId(e.target.value)}
        >
          {boards.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        {role === "admin" && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              const name = window.prompt("Board name");
              if (name?.trim()) createBoard.mutate(name);
            }}
          >
            <Plus className="size-4" /> Board
          </Button>
        )}
        <div className="ml-auto">
          {canWrite && board && boardData && (
            <CreateTaskDialog
              projectId={projectId}
              boardId={board.id}
              columns={boardData.columns}
            />
          )}
        </div>
      </div>

      <TaskFilterBar filters={filters} onChange={setFilters} members={members} labels={labels} />

      <div className="flex items-start gap-3 overflow-x-auto pb-4">
        {(boardData?.columns ?? []).map((column) => (
          <ColumnLane
            key={column.id}
            column={column}
            tasks={filteredTasks.filter((t) => t.columnId === column.id)}
            members={members}
            labels={labels}
            canWrite={canWrite}
            isAdmin={role === "admin"}
            highlighted={overColumn === column.id}
            onOpen={openTask}
            onDropTask={(taskId) => {
              setOverColumn(null);
              move.mutate({ taskId, columnId: column.id });
            }}
            onDragEnter={() => setOverColumn(column.id)}
            onDragLeave={() => setOverColumn((c) => (c === column.id ? null : c))}
          />
        ))}
        {role === "admin" && board && (
          <AddColumn boardId={board.id} />
        )}
      </div>
    </div>
  );
}

function ColumnLane({
  column,
  tasks,
  members,
  labels,
  canWrite,
  isAdmin,
  highlighted,
  onOpen,
  onDropTask,
  onDragEnter,
  onDragLeave,
}: {
  column: Column;
  tasks: Awaited<ReturnType<typeof api.listTasks>>;
  members: Awaited<ReturnType<typeof api.listMembers>>;
  labels: Awaited<ReturnType<typeof api.listLabels>>;
  canWrite: boolean;
  isAdmin: boolean;
  highlighted: boolean;
  onOpen: (taskId: string) => void;
  onDropTask: (taskId: string) => void;
  onDragEnter: () => void;
  onDragLeave: () => void;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(column.name);

  const rename = useMutation({
    mutationFn: () => api.renameColumn(column.id, name),
    onSuccess: () => {
      setEditing(false);
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteColumn(column.id),
    onSuccess: () => void queryClient.invalidateQueries(),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <section
      aria-label={column.name}
      onDragOver={(e) => {
        e.preventDefault();
        onDragEnter();
      }}
      onDragLeave={onDragLeave}
      onDrop={(e) => {
        e.preventDefault();
        const taskId = e.dataTransfer.getData("text/task-id");
        if (taskId) onDropTask(taskId);
      }}
      className={`w-72 shrink-0 rounded-lg border p-2 transition-colors ${
        highlighted ? "border-primary bg-primary/5" : "border-border bg-surface"
      }`}
    >
      <header className="mb-2 flex items-center gap-1 px-1">
        {isAdmin && <GripVertical className="size-4 text-muted-foreground" />}
        {editing ? (
          <form
            className="flex flex-1 gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              rename.mutate();
            }}
          >
            <Input
              className="h-7 text-sm"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
            />
            <Button size="sm" className="h-7" type="submit">
              Save
            </Button>
          </form>
        ) : (
          <>
            <h2 className="text-sm font-semibold">{column.name}</h2>
            <span className="rounded-full bg-secondary px-2 text-xs text-muted-foreground">
              {tasks.length}
            </span>
          </>
        )}
        {isAdmin && !editing && (
          <div className="ml-auto flex">
            <button
              aria-label={`Rename ${column.name}`}
              className="p-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => {
                setName(column.name);
                setEditing(true);
              }}
            >
              Edit
            </button>
            <button
              aria-label={`Delete ${column.name}`}
              className="p-1 text-muted-foreground hover:text-destructive"
              onClick={() => {
                if (window.confirm(`Delete column "${column.name}"? Tasks move to the first column.`))
                  remove.mutate();
              }}
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
        )}
      </header>

      <div className="space-y-2">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            labels={labels}
            members={members}
            onOpen={onOpen}
            draggable={canWrite}
            onDragStart={(e) => e.dataTransfer.setData("text/task-id", task.id)}
          />
        ))}
        {tasks.length === 0 && (
          <p className="rounded-md border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
            Drop tasks here
          </p>
        )}
      </div>
    </section>
  );
}

function AddColumn({ boardId }: { boardId: string }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const add = useMutation({
    mutationFn: () => api.createColumn(boardId, name),
    onSuccess: () => {
      setOpen(false);
      setName("");
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!open)
    return (
      <button
        className="flex w-40 shrink-0 items-center justify-center gap-1 rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground hover:text-foreground"
        onClick={() => setOpen(true)}
      >
        <Plus className="size-4" /> Add column
      </button>
    );
  return (
    <form
      className="w-56 shrink-0 space-y-2 rounded-lg border border-border bg-surface p-2"
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      <Input
        autoFocus
        aria-label="Column name"
        placeholder="Column name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <div className="flex gap-2">
        <Button size="sm" type="submit" disabled={!name.trim()}>
          Add
        </Button>
        <Button size="sm" variant="ghost" type="button" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
