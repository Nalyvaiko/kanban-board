# Mini Jira Kanban — Task Roadmap

## Done
- Services layer contract (`src/services/api.ts`) + domain types
- Mock implementation (`src/services/mock/`) with localStorage persistence, seed data, auth, roles
- Design system tokens + fonts wired into `src/styles.css` / root route
- Auth context (`src/lib/auth.tsx`), app shell, avatar, task card, filter bar, task details dialog, create-task dialog
- Routes: `/` landing, `/auth`, `/dashboard`, `/projects`, `/profile`

## In progress
- Project layout + tabs: board (Kanban DnD), list view, members, settings

## Left
- Project routes: `projects.$projectId.tsx`, board, list, members, settings
- Vitest tests for services layer (auth, permissions, tasks, comments, search)
- Verify build, test run, and browser smoke test
