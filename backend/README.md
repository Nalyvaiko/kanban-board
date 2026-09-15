# kanban-backend

REST API backend for the Mini Jira kanban board (see `../PROJECT-SPEC.md`
and `../openapi.yaml` at the repo root for the product/API spec this
implements).

## Data storage

Everything lives in an in-memory `Store` (`src/kanban_backend/store.py`) -
no database, no external services. Data resets whenever the process
restarts, and the store is seeded with a demo project, users, boards, and
tasks at import time (`src/kanban_backend/seed.py`) so the frontend has
something to look at immediately.

Seeded accounts (all use the password `password123`):

| Email               | Role(s)                                              |
| ------------------- | ----------------------------------------------------- |
| alice@example.com   | admin on "Website Redesign", member on "Mobile App"    |
| bob@example.com     | member on "Website Redesign", admin on "Mobile App"    |
| carol@example.com   | viewer on "Website Redesign"                           |
| dave@example.com    | no project yet; has a pending invitation to join       |

## Authentication

`openapi.yaml` describes a cookie-based session. This implementation
deviates from that deliberately, per the project's requirements: passwords
are salted and hashed (PBKDF2-HMAC-SHA256, stdlib only), and sessions are
opaque bearer tokens returned by `/auth/register`, `/auth/login`, and
`/auth/google`, sent back by clients as `Authorization: Bearer <token>`.

## Layout

```
src/kanban_backend/
  main.py          FastAPI app assembly, CORS, router registration
  models.py        Pydantic schemas for every entity and request/response body
  store.py         In-memory data store + cascading-delete helpers
  auth.py          Password hashing, bearer tokens, role-check dependencies
  seed.py          Demo data seeding
  activity_log.py  Shared helper for writing to the project activity feed
  viewmodels.py    Composes "with relation" view models (e.g. comment + author)
  routers/         One module per resource (auth, projects, tasks, ...)
tests/             pytest suite (see below)
```

## Running

```sh
uv run kanban-backend
# or: uv run uvicorn kanban_backend.main:app --reload
```

The API is served under `/api` (e.g. `http://127.0.0.1:8000/api/projects`).
Interactive docs are at `/docs`.

## Testing

```sh
uv run pytest
```

Each test gets a blank store (see `tests/conftest.py`) and builds whatever
data it needs through the API itself, so tests don't depend on the seed
data's exact contents.
