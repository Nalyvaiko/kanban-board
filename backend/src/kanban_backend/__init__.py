def main() -> None:
    """Entry point for `uv run kanban-backend` - runs the dev server."""
    import uvicorn

    uvicorn.run(
        "kanban_backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[".venv/*", "*/.venv/*"],
    )
