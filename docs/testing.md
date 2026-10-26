# Testing

Four layers, each a different tradeoff between speed and realism. Run the fastest
layer that would actually catch the bug you're worried about.

## Backend unit/API tests - pytest

- Runner: pytest. Location: `backend/tests/`.
- Against an isolated in-memory SQLite DB (`conftest.py` sets `DATABASE_URL` to
  `sqlite:///:memory:` before any import), reset to blank before and after each
  test.
- Build whatever data a test needs through the real API (`register`, `login`,
  create a project, ...) rather than reaching into the store directly - tests
  exercise the same path a real client would.
- Command: `cd backend && uv run pytest` (or `make test-backend`).

**Known gap**: the in-memory DB skips the file-based SQLite transaction/locking
code path entirely (see `db.py`'s own comment on this). A concurrency bug in that
path - see issue #21 - has to be reproduced with a standalone script against a
real file-based DB; it cannot be caught by this suite. If you touch `db.py`'s
SQLite transaction handling, verify by hand the way #21 did, not just by running
`pytest`.

## Frontend tests - Vitest

- Runner: Vitest. Location: `frontend/`.
- Command: `cd frontend && npx vitest run` (or `make test-frontend`).

## Integration tests - real Docker Compose stack

- Builds the real image and drives the real `docker-compose.yaml` (app + real
  Postgres, real HTTP), not mocks.
- Location: `integration-tests/`. Command: `make test-integration`
  (`cd integration-tests && uv sync && uv run pytest`).
- Slow, needs Docker running. Not part of `make test`.

## End-to-end tests - Playwright

- Drives the same real `docker-compose.yaml` stack through a real Chromium
  browser.
- Location: `e2e/`. Command: `make test-e2e`
  (`cd e2e && npm install && npx playwright install --with-deps chromium && npm test`).
- Slow, needs Docker running. Not part of `make test`.

## CI

`.github/workflows/ci-cd.yml` runs backend and frontend tests in parallel, then
integration and e2e tests against the real compose stack, on every push and pull
request - only once all of that passes does `deploy-dev` run.

## Verifying infrastructure and observability work

None of the four layers above touch CloudFormation, the CI/CD workflows
themselves, or the observability stack - there is no automated test suite for
those. Verify them the way this project's own history actually did (see the
DevOps Engineer and SRE docs in `team/`): `cfn-lint` / `actionlint` / `shellcheck`
for static checks, and bringing up the real stack (`docker compose up`, a real
`aws cloudformation deploy`) and exercising it for anything a static check can't
catch - a static pass is not evidence the thing works.
