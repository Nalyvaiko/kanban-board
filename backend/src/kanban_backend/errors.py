"""Shared API error type, matching the `Error` schema in openapi.yaml:
`{ "message": str, "status": int }`.
"""

from __future__ import annotations

from fastapi import HTTPException


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
