"""Bearer demo-token authentication and role permissions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

Role = Literal["CLERK", "OWNER", "WAREHOUSE"]
AllowedAction = Literal[
    "EDIT_DRAFT",
    "RESOLVE_ISSUE",
    "COPY_CLARIFICATION",
    "APPROVE_AND_GENERATE_DO",
    "SUBMIT_FOR_OWNER",
    "OWNER_APPROVE",
    "OWNER_REJECT",
    "CANCEL_DRAFT",
    "VIEW_ACTIVITY",
    "WAKE_AI",
]

# Static role capabilities from Gate 0 fields.md. The server, not the client,
# decides these; /me only reports them.
_CLERK_PERMISSIONS: tuple[AllowedAction, ...] = (
    "EDIT_DRAFT",
    "RESOLVE_ISSUE",
    "COPY_CLARIFICATION",
    "APPROVE_AND_GENERATE_DO",
    "SUBMIT_FOR_OWNER",
    "VIEW_ACTIVITY",
    "WAKE_AI",
)
_OWNER_PERMISSIONS: tuple[AllowedAction, ...] = _CLERK_PERMISSIONS + (
    "OWNER_APPROVE",
    "OWNER_REJECT",
    "CANCEL_DRAFT",
)

ROLE_PERMISSIONS: dict[str, tuple[AllowedAction, ...]] = {
    "CLERK": _CLERK_PERMISSIONS,
    "OWNER": _OWNER_PERMISSIONS,
    "WAREHOUSE": (),
}

PERMISSION_SUMMARIES: dict[str, str] = {
    "CLERK": "Can create and edit drafts, resolve issues, and submit for approval.",
    "OWNER": "Can create, edit, approve, reject, and cancel drafts.",
    "WAREHOUSE": "Read-only warehouse delivery order access.",
}


class InvalidTokenError(Exception):
    """Raised when a Bearer token is absent, malformed, unknown, or inactive."""


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    tenant_id: str
    tenant_name: str
    display_name: str
    role: Role
    permissions: tuple[AllowedAction, ...]


def hash_token(token: str) -> str:
    """Return the stable demo-token digest used by seed and /me."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest().lower()


def parse_authorization(header: str | None) -> str:
    """Extract exactly one Bearer token from an Authorization header."""
    if not header:
        raise InvalidTokenError("missing Authorization header")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise InvalidTokenError("malformed Bearer header")
    return parts[1]


def permissions_for(role: str) -> tuple[AllowedAction, ...]:
    try:
        return ROLE_PERMISSIONS[role]
    except KeyError:
        raise InvalidTokenError("unknown role") from None


def permission_summary_for(role: str) -> str:
    try:
        return PERMISSION_SUMMARIES[role]
    except KeyError:
        raise InvalidTokenError("unknown role") from None
