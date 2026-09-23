# kanban-board

A Kanban board app: FastAPI/SQLModel backend (`backend/`), React/TanStack
Start frontend (`frontend/`). See `backend/README.md` and `PROJECT-SPEC.md`
for more detail; `make run` / `make install` (see `Makefile`) cover local
dev.

## Running with Docker

```sh
docker build -t kanban-board .
docker run -p 8000:8000 -v kanban-data:/data kanban-board
```

Then open `http://localhost:8000` - the backend serves the built frontend
directly, so there's just one process and one port. `-v kanban-data:/data`
persists the SQLite database in a named volume across container restarts;
drop it if you're fine with the data resetting each run.

### With Postgres

The image bundles the Postgres driver too, so switching is just an env var:

```sh
docker compose up
```

`docker-compose.yml` runs the app alongside a Postgres container and points
`DATABASE_URL` at it automatically. To point at Postgres running elsewhere
instead, set `DATABASE_URL` yourself, e.g.
`-e DATABASE_URL=postgresql+psycopg://user:pass@host/db`.
