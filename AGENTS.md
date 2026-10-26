# kanban-board

A Jira-style kanban board app: FastAPI/SQLModel backend (`backend/`), React/
TanStack Start frontend (`frontend/`), deployed to AWS via CloudFormation with
a full CI/CD pipeline and an observability stack with automated on-call
response.

## Docs — read when relevant

- `PROJECT-SPEC.md` — product scope, MVP goals, data model. Source of truth for
  product decisions.
- `openapi.yaml` — the API contract the backend implements against.
- `_docs/plan.md` — points to the above, plus where infra/observability
  decisions live (they're not in `PROJECT-SPEC.md`).
- `_docs/process.md` — how the agent team works: roles, orchestrator, task
  lifecycle, rules.
- `_docs/task-template.md` — the four-section template every groomed task uses.
- `_docs/tasks.md` — backlog, one-to-one with the GitHub issues.
- `_docs/testing.md` — the four test layers (pytest/Vitest/integration/e2e),
  what each actually covers, and the one known gap in the backend suite.
- `_docs/team/*.md` — what each role (PM, Software Engineer, DevOps Engineer,
  SRE, QA) actually does and its definition of done.
- `backend/README.md`, `cloudformation/README.md`, `observability/README.md`,
  `on-call-engineer/README.md` — area-specific setup, tradeoffs, and how to run
  each piece.

## Rules

- Read `PROJECT-SPEC.md` (and `_docs/plan.md` for anything infra/observability)
  before planning work; do not expand scope past it.
- Follow `_docs/process.md`.
- Keep `_docs/tasks.md` and the GitHub issues in sync when tasks change.
- Branch off `main`; do not commit directly to `main`.
- Keep planning and reference docs in `_docs/`.
- For backend, use `uv` for dependency management: `uv sync`, `uv add
  <package>`, `uv run python <file>`.
- Regularly commit code to git.

## Stack

- **Backend**: FastAPI + SQLModel/SQLAlchemy, `uv`-managed, SQLite by default
  (Postgres via `DATABASE_URL` - no code change needed)
- **Frontend**: React, TanStack Start, Vite
- **Local dev**: `docker-compose.yml` (app + Postgres)
- **CI/CD**: GitHub Actions (`.github/workflows/ci-cd.yml`,
  `promote-to-production.yml`) - parallel tests, build-once-push-to-ECR,
  auto-deploy to dev, manual promote to production
- **AWS infra**: CloudFormation (`cloudformation/`) - single-EC2 app stacks
  (dev + prod), a shared ECR repo, a shared observability instance
- **Observability**: OpenTelemetry Collector + Prometheus + Loki + Tempo +
  Grafana (`observability/`), with alerting and an automated on-call responder
  (`on-call-engineer/`)

## Commands

- `make install` / `make run` — install and run backend + frontend together
- `make test` — backend (pytest) + frontend (Vitest) tests
- `make test-integration` / `make test-e2e` — slower, need Docker running, not
  part of `make test`
- `docker compose up` — app + Postgres, local
- `cd observability && docker compose up -d` — the observability stack, its
  own independent Compose project

See `_docs/testing.md` for the full breakdown and `cloudformation/README.md` /
`observability/README.md` for the AWS equivalents.

## Environment

- Repo: `Nalyvaiko/kanban-board` (public).
