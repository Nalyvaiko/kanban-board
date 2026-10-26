# kanban-board

**The problem**: a team juggling work across several projects needs more
than a single to-do list - they need boards they can customize per
project, the ability to see who's working on what and assign it to them,
and a history of what happened and when, without standing up a full Jira
instance to get it. This is a Jira-style project management app that
covers that: multiple projects, customizable Kanban boards, task
assignment/priority/labels/due dates/comments/attachments, activity
history, and three permission levels (admin/member/viewer) per project -
see `PROJECT-SPEC.md` for the full MVP scope this implements against.

**Built as**: a FastAPI/SQLModel backend (`backend/`) and a React/
TanStack Start frontend (`frontend/`), on top of a full deployment
pipeline, an observability stack with alerting, and an on-call automation,
following an explicit agent-team process (`docs/`) - see "Evidence of the
work done" below. `make run` / `make install` (see `Makefile`) cover
local dev.

## Try the live app

**http://3.146.110.209:8000** - a real deployment on AWS (EC2, via
`cloudformation/template.yaml`), kept up to date automatically by CI/CD on
every push to `main` (verified reachable as of this commit: `/` returns
200, `/api/health` returns `{"status":"ok"}`).

**Expected behavior**: log in with the read-only demo account below and
you'll land on a dashboard showing a pre-existing project, "Website
Redesign," with its own Kanban board, columns, and tasks already
populated - browse it, open a task, search/filter, and check the
activity history, all without needing to create anything first:

| Email | Password | What you'll see |
| --- | --- | --- |
| carol@example.com | password123 | Viewer-only on "Website Redesign" - browse everything, change nothing |

This is deliberately the *only* credential published here, and
deliberately the viewer role: this is a public demo on a shared live
database, and a viewer account can't create, edit, delete, or comment on
anything - verified directly against the live deployment (a write
attempt as `carol` gets a real `403`), not just assumed from the role
name. See `backend/README.md`'s "Data storage" section for the other
seeded accounts (not published here, since they can write) - or just
register your own account on the live app above to try the full,
editable experience with your own disposable data.

No install needed - just open the URL above.

## Evidence of the work done

- **Automated CI/CD**: `.github/workflows/ci-cd.yml` runs backend,
  frontend, integration, and end-to-end tests against a real Docker
  stack, then builds and deploys to the live URL above on every push to
  `main`; `.github/workflows/promote-to-production.yml` promotes that
  exact, already-tested image to a separate production stack on manual
  approval. See `cloudformation/README.md`.
- **Observability**: every request is traced, four app metrics are
  tracked, and structured JSON logs carry the same trace ID as their
  trace and metrics - all verified end-to-end against a real OpenTelemetry
  Collector + Prometheus + Loki + Tempo + Grafana stack, not just
  configured. See `observability/README.md` and `backend/README.md`'s
  "Telemetry" section.
- **Alerting + on-call automation**: a Grafana alert rule fires on
  repeated task-creation failures; `on-call-engineer/poll.py` watches for
  firing alerts and dispatches a headless coding agent to investigate (and
  optionally fix) with no human needing to see the alert first. See
  `on-call-engineer/README.md`.
- **An explicit agent-team process**: `docs/` defines the roles (PM,
  Software Engineer, DevOps Engineer, SRE, QA), the task lifecycle, and
  the rules this project is actually built under - see `AGENTS.md` for
  the entry point.
- **A public paper trail**: every piece of work above was tracked as a
  [GitHub issue](https://github.com/Nalyvaiko/kanban-board/issues?q=is%3Aissue)
  and shipped through a reviewed PR referencing it - the issue list is a
  real, closeable record of what was planned, built, and verified, not
  just commit history.
- **Real-bug test-and-fix cycles**: a SQLite concurrency bug (and its
  regression test), an AWS SSM comment-length limit only discoverable by
  a live run, and a deliberately introduced bug caught and reverted - see
  the closed issues above for each.

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

## Deploying to AWS

See `cloudformation/README.md` - a CloudFormation template that runs the
same `docker-compose.yaml` on a single EC2 instance, plus the cost and
durability tradeoffs that keeps it cheap, and how automatic CI/CD deploys
to it on every push to `main`.

## Observability

See `observability/README.md` - an OpenTelemetry Collector, Prometheus,
Loki, Tempo, and Grafana, as a separate Compose project you can point
this app's traces, metrics, and logs at - plus the alert rule and
on-call automation (`on-call-engineer/README.md`) built on top of it.

## How this project is built

See `AGENTS.md` and `docs/` - this project is developed by a defined team
of agent roles (PM, Software Engineer, DevOps Engineer, SRE, QA) following
an explicit process, with work tracked as
[GitHub issues](https://github.com/Nalyvaiko/kanban-board/issues?q=is%3Aissue)
and shipped through PRs.
