"""Shared API error type, matching the `Error` schema in openapi.yaml:
`{ "message": str, "status": int }`.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(HTTPException):
    """An HTTPException whose JSON body is `{message, status}`."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(status_code=status_code, detail={"message": message, "status": status_code})


def not_found(message: str = "Not found") -> ApiError:
    return ApiError(404, message)


def forbidden(message: str = "Forbidden") -> ApiError:
    return ApiError(403, message)


def unauthorized(message: str = "Not signed in") -> ApiError:
    return ApiError(401, message)


def bad_request(message: str) -> ApiError:
    return ApiError(400, message)


def conflict(message: str) -> ApiError:
    return ApiError(409, message)


def _error_body(status_code: int, detail: object) -> dict:
    if isinstance(detail, dict) and isinstance(detail.get("message"), str):
        return {"message": detail["message"], "status": status_code}
    return {"message": str(detail), "status": status_code}


def _describe_validation_error(error: dict) -> str:
    # loc is e.g. ("body", "email") or ("query", "priority"); the first
    # part only says where the field came from.
    field = ".".join(str(part) for part in error.get("loc", ())[1:])
    return f"{field}: {error.get('msg', 'Invalid value')}" if field else error.get("msg", "Invalid value")


def install_error_handlers(app: FastAPI) -> None:
    """Make every error response match openapi.yaml's `Error` schema -
    `{"message": str, "status": int}` at the top level.

    Without these, FastAPI wraps an ApiError as `{"detail": {...}}`, and
    its own errors use other shapes again: `{"detail": "Not Found"}` for an
    unknown route, `{"detail": [...]}` for a 422.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            _error_body(exc.status_code, exc.detail),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e.get("loc", ())[1:]), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        message = _describe_validation_error(exc.errors()[0]) if exc.errors() else "Invalid request"
        return JSONResponse({"message": message, "status": 422, "errors": errors}, status_code=422)


def required_text(value: str, message: str) -> str:
    """Return `value` stripped, or raise a 400 with `message` if that
    leaves nothing - for names/titles that must not be blank."""
    text = value.strip()
    if not text:
        raise bad_request(message)
    return text
