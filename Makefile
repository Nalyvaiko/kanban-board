.PHONY: run run-backend run-frontend install install-backend install-frontend test test-backend test-frontend

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
