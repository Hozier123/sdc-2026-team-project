"""Request IDs and the small set of errors used by the identity slice."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth import InvalidTokenError

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _request_id(value: str | None) -> str:
    if value and _REQUEST_ID_RE.fullmatch(value):
        return value
    return str(uuid4())


def _invalid_token_response(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error_code": "INVALID_TOKEN",
            "message": "Invalid or missing token.",
            "details": {},
        },
        headers={
            "WWW-Authenticate": "Bearer",
            "Cache-Control": "no-store",
        },
    )


async def request_id_middleware(request: Request, call_next):
    request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.middleware("http")(request_id_middleware)

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return _invalid_token_response(request)
