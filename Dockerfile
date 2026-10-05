# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the frontend into static files with Node.
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first so this layer is cached across source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build \
    # `vite build` writes the prerendered app shell as _shell.html (see
    # tanstackStart.spa in vite.config.ts) rather than index.html; a static
    # file server needs the conventional name to serve it as the default
    # document and as the SPA fallback for client-side routes.
    && mv dist/client/_shell.html dist/client/index.html

# ---------------------------------------------------------------------------
# Stage 2: the backend, with the built frontend bundled in as static files.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend

# Installed via uv's own script rather than copying the binary out of a
# ghcr.io image (the previous approach) - that pull hit a real, if
# transient, 429 rate-limit from ghcr.io in CI. This still depends on
# GitHub's release CDN (where the script fetches the actual binary
# from), but no longer on ghcr.io's separate container-registry pull
# path specifically.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /app/backend

# Install dependencies before copying the rest of the source, so this
# (slow) layer is only rebuilt when pyproject.toml/uv.lock actually change.
# --extra postgres bundles the Postgres driver alongside the default
# SQLite support, so switching DATABASE_URL to a Postgres URL at runtime
# doesn't need a different image.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-install-project --no-dev --extra postgres

COPY backend/ ./
RUN uv sync --locked --no-dev --extra postgres

# main.py serves this directory at "/" (and everything under it) whenever
# it's present - see FRONTEND_DIR in src/kanban_backend/main.py.
COPY --from=frontend-build /app/frontend/dist/client ./static

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

# SQLite file lives on a separate volume so it survives container recreation;
# point DATABASE_URL elsewhere (e.g. a Postgres URL) to use a different DB.
ENV DATABASE_URL=sqlite:////data/kanban.db
VOLUME ["/data"]

EXPOSE 8000

CMD [".venv/bin/uvicorn", "kanban_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
