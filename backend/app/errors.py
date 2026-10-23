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


class ApiError(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    default_message = "Request failed."

    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class MessageTooLongError(ApiError):
    status_code = 422
    error_code = "MESSAGE_TOO_LONG"
    default_message = "message_text must not exceed 4000 Unicode code points."


class AiAndFallbackUnavailableError(ApiError):
    status_code = 503
    error_code = "AI_AND_FALLBACK_UNAVAILABLE"
    default_message = "AI extraction and local fallback are unavailable."


class RateLimitedError(ApiError):
    status_code = 429
    error_code = "RATE_LIMITED"
    default_message = "Too many requests."


class ResourceNotFoundError(ApiError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"
    default_message = "Resource not found."


class ForbiddenActionError(ApiError):
    status_code = 403
    error_code = "FORBIDDEN_ACTION"
    default_message = "Action is forbidden for this role."


class StaleVersionError(ApiError):
    status_code = 409
    error_code = "STALE_VERSION"
    default_message = "Draft version is stale."


class PendingOwnerApprovalError(ApiError):
    status_code = 409
    error_code = "PENDING_OWNER_APPROVAL"
    default_message = "Draft is waiting for owner approval."


class AlreadyApprovedError(ApiError):
    status_code = 409
    error_code = "ALREADY_APPROVED"
    default_message = "Draft already generated a delivery order."


class DraftRejectedError(ApiError):
    status_code = 409
    error_code = "DRAFT_REJECTED"
    default_message = "Draft is rejected and read-only."


class StockChangedError(ApiError):
    status_code = 409
    error_code = "STOCK_CHANGED"
    default_message = "Stock changed and no longer satisfies the draft."


class InvalidLineOperationError(ApiError):
    status_code = 400
    error_code = "INVALID_LINE_OPERATION"
    default_message = "Line set does not cover the current draft."


class EmptyOrderError(ApiError):
    status_code = 400
    error_code = "EMPTY_ORDER"
    default_message = "Order must retain at least one line."


class OverrideRequiredError(ApiError):
    status_code = 400
    error_code = "OVERRIDE_REQUIRED"
    default_message = "Price override requires a reason."


class TargetLineRequiredError(ApiError):
    status_code = 400
    error_code = "TARGET_LINE_REQUIRED"
    default_message = "Price resolution requires a target line."


class NoteRequiredError(ApiError):
    status_code = 400
    error_code = "NOTE_REQUIRED"
    default_message = "This resolution requires a note."


class InsufficientStockError(ApiError):
    status_code = 400
    error_code = "INSUFFICIENT_STOCK"
    default_message = "Stock is insufficient for approval."


class RejectionReasonRequiredError(ApiError):
    status_code = 422
    error_code = "REJECTION_REASON_REQUIRED"
    default_message = "Rejection requires a non-empty note."


class InvalidQuantityError(ApiError):
    status_code = 422
    error_code = "INVALID_QUANTITY"
    default_message = "Quantity must be a positive integer."


class MissingTierPriceError(ApiError):
    status_code = 422
    error_code = "MISSING_TIER_PRICE"
    default_message = "No tier price exists for this customer and SKU."


class RequestValidationFailedError(ApiError):
    status_code = 422
    error_code = "REQUEST_VALIDATION_FAILED"
    default_message = "Request validation failed."


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
    response.headers["Cache-Control"] = "no-store"
    if response.status_code == 503:
        response.headers["Retry-After"] = "5"
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.middleware("http")(request_id_middleware)

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return _invalid_token_response(request)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimitedError):
            retry_after = exc.details.get("retry_after_seconds")
            if isinstance(retry_after, int):
                headers["Retry-After"] = str(retry_after)
        return _error_response(
            exc.status_code,
            exc.error_code,
            exc.message,
            exc.details,
            headers=headers,
        )

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
