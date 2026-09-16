import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/projects/$projectId/")({
  beforeLoad: ({ params, search }) => {
    throw redirect({
      to: "/projects/$projectId/board",
      params,
      search: search as { task?: string | undefined },
    });
  },
});
