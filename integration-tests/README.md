# integration-tests

End-to-end tests that drive the real `docker-compose.yaml` stack (the
actual built Docker image, real Postgres) and talk to it over plain HTTP -
unlike `backend/tests`, nothing here imports the backend's Python code, so
these catch things a unit/API test against an in-process app can't:
Docker networking, the compose file itself, and behavior across a
container restart.

## Running

Requires Docker (and nothing already listening on `localhost:8000`, since
that's the compose stack's port):

```sh
make test-integration
# or directly:
cd integration-tests && uv sync && uv run pytest
```

A session-scoped fixture (`conftest.py`) runs `docker compose up -d --build`
once, waits for the app to become reachable, then tears the whole stack
down (`docker compose down -v`) after the run - so this always starts from
and ends on a clean slate. Expect it to take well over a minute: building
the image and starting Postgres both take real time, and a couple of tests
deliberately kill and restart a container mid-test.

## What's covered

- Seed data exists exactly once on a fresh stack (no double-seeding).
- The backend serves the built frontend: the app shell at `/`, client-side
  routes falling back to it correctly, and a real static asset.
- The frontend's catch-all route can't be used for path traversal (tested
  with a raw socket request, since HTTP clients normalize `..` out of a
  URL before sending it - a normal `httpx`/`curl` request wouldn't
  actually exercise the guard).
- `/api/*` isn't swallowed by that catch-all.
- Register/login works against real Postgres.
- Data survives the `app` container being killed and restarted - the
  regression test for a real bug this caught: a session-scoping issue
  that could lose a write if the process died before something else
  happened to flush it (see the `docker-static-frontend` /
  `postgres-support` branch history).
- Data survives the `db` (Postgres) container being killed and restarted,
  and the app reconnects once it's back.
