"""FastAPI dependencies for the authenticated identity slice."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.auth import (
    CurrentUser,
    InvalidTokenError,
    hash_token,
    parse_authorization,
    permissions_for,
)
from app.config import Settings
from app.db import connect


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    token = parse_authorization(request.headers.get("Authorization"))
    digest = hash_token(token)

    # Unknown database failures are server errors. Do not invent a business
    # error code or a non-contract 503 response for /me; FastAPI's 500 path
    # preserves the frozen error boundary.
    with connect(settings) as conn:
        row = conn.execute(
            "SELECT u.user_id, u.tenant_id, u.display_name, u.role, t.name "
            "FROM users u JOIN tenants t ON t.tenant_id = u.tenant_id "
            "WHERE u.demo_token_hash = %s AND u.active = true",
            (digest,),
        ).fetchone()

    if row is None:
        raise InvalidTokenError("unknown or inactive token")

    user_id, tenant_id, display_name, role, tenant_name = row
    permissions = permissions_for(role)
    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        display_name=display_name,
        role=role,
        permissions=permissions,
    )
