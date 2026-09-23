# kanban-backend

REST API backend for the Mini Jira kanban board (see `../PROJECT-SPEC.md`
and `../openapi.yaml` at the repo root for the product/API spec this
implements).

## Data storage

Data is persisted through SQLAlchemy/SQLModel (`src/kanban_backend/db.py`,
`store.py`) to whatever database `DATABASE_URL` points at - any SQLAlchemy
URL works, so switching from SQLite to Postgres later is a config change,
not a code change. Defaults to a local SQLite file (`./kanban.db`, relative
to wherever the process is started) if `DATABASE_URL` isn't set:

```sh
DATABASE_URL=sqlite:///./kanban.db uv run kanban-backend        # default
DATABASE_URL=postgresql+psycopg://user:pass@host/db uv run kanban-backend
```

Postgres needs the `psycopg` driver, which is an optional dependency group
rather than installed by default (`uv sync --extra postgres`). The Docker
image (`../Dockerfile`) always includes it, so switching a container to
Postgres is just a `DATABASE_URL` change - see `../docker-compose.yml` for
a ready-to-run example (`docker compose up`).

On first run against an empty database, `src/kanban_backend/seed.py` seeds a
demo project, users, boards, and tasks so the frontend has something to look
at immediately. Restarting against an already-seeded database (the normal
case now that data persists) skips seeding.

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
  main.py          FastAPI app assembly, CORS, router registration, DB session commit/rollback
  db.py            SQLAlchemy engine/session config, driven by DATABASE_URL
  models.py        SQLModel entities (table + Pydantic schema in one) and request/response bodies
  store.py         Dict-like facade over the DB + cascading-delete helpers
  auth.py          Password hashing, bearer tokens, role-check dependencies
  seed.py          Demo data seeding (only runs against an empty database)
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

If a `static/` directory is present next to this file (populated by the
Docker build - see `../Dockerfile` - not by local dev), `main.py` also
serves it directly at `/`, with any unmatched path falling back to its
`index.html` so client-side routing works. In local dev, `static/` doesn't
exist, so this is skipped entirely and only the API is served; run the
frontend separately (`cd ../frontend && npm run dev`).

## Testing

```sh
uv run pytest
```

Tests run against an isolated in-memory SQLite database (see
`tests/conftest.py`), reset to blank before and after each test, and build
whatever data they need through the API itself rather than depending on the
seed data's exact contents.
