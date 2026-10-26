.PHONY: run run-backend run-frontend install install-backend install-frontend test test-backend test-frontend test-integration test-e2e test-concurrency

run: run-backend

run-backend:
	cd backend && uv run kanban-backend

run-frontend:
	cd frontend && npm run dev

install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm ci

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npx vitest run

# Slow, and needs Docker running - builds the real image and drives
# docker-compose.yaml, not just backend/frontend code. Not part of `test`.
test-integration:
	cd integration-tests && uv sync && uv run pytest

# Slow, needs Docker running - drives docker-compose.yaml through a real
# browser (Playwright). Not part of `test`.
test-e2e:
	cd e2e && npm install && npx playwright install --with-deps chromium && npm test

# Needs DATABASE_URL pointed at a real file *before* pytest ever imports
# kanban_backend.db - testpaths=["tests"] in pyproject.toml means
# tests_concurrency/ is never swept into `make test-backend` to begin
# with, and DATABASE_URL must be set here, not inside the test, since
# the engine binds to whatever it is at import time. Not part of `test`.
test-concurrency:
	rm -f backend/.concurrency-test.db
	cd backend && DATABASE_URL=sqlite:///.concurrency-test.db uv run pytest tests_concurrency/
	rm -f backend/.concurrency-test.db
