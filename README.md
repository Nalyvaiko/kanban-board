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
drop it if you're fine with the data resetting each run. Point `DATABASE_URL`
(`-e DATABASE_URL=...`) at a different database - e.g. Postgres - to use
that instead.
