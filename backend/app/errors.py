"""Request IDs and the fixed error responses used by the API slice."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import InvalidTokenError

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class MessageTooLongError(Exception):
    """The raw or masked message exceeds 4000 Unicode code points."""


class ResourceNotFoundError(Exception):
    """A tenant-scoped resource is missing or not visible."""


class ForbiddenActionError(Exception):
    """The authenticated role cannot perform this action."""


def _request_id(value: str | None) -> str:
    if value and _REQUEST_ID_RE.fullmatch(value):
        return value
    return str(uuid4())


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details or {},
        },
        headers=headers,
    )


def _invalid_token_response(request: Request) -> JSONResponse:
    return _error_response(
        401,
        "INVALID_TOKEN",
        "Invalid or missing token.",
        headers={
            "WWW-Authenticate": "Bearer",
            "Cache-Control": "no-store",
        },
    )


async def request_id_middleware(request: Request, call_next):
    request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        # Unknown server failures are 500, not invented business error codes.
        # Keep the response generic so no DSN/token/exception detail leaks.
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.middleware("http")(request_id_middleware)

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return _invalid_token_response(request)

    @app.exception_handler(MessageTooLongError)
    async def message_too_long_handler(request: Request, exc: MessageTooLongError) -> JSONResponse:
        return _error_response(
            422,
            "MESSAGE_TOO_LONG",
            "message_text must not exceed 4000 Unicode code points.",
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        return _error_response(404, "RESOURCE_NOT_FOUND", "Resource not found.")

    @app.exception_handler(ForbiddenActionError)
    async def forbidden_action_handler(request: Request, exc: ForbiddenActionError) -> JSONResponse:
        return _error_response(403, "FORBIDDEN_ACTION", "Action is forbidden for this role.")

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = []
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", ()) if part != "body"]
            fields.append(
                {
                    "path": ".".join(location) or "body",
                    "reason": str(error.get("msg", "invalid")),
                }
            )
        return _error_response(
            422,
            "REQUEST_VALIDATION_FAILED",
            "Request validation failed.",
            {"fields": fields},
        )
