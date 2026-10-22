"""Server-authoritative identity endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app.auth import AllowedAction, CurrentUser, Role, permission_summary_for
from app.deps import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Identity"])


class TenantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    tenant: TenantSummary
    display_name: str
    role: Role
    permissions: list[AllowedAction]
    permission_summary: str


@router.get(
    "/me",
    response_model=MeResponse,
    responses={401: {"description": "Missing, malformed, unknown, or inactive token"}},
)
def get_me(
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MeResponse:
    response.headers["Cache-Control"] = "no-store"
    return MeResponse(
        user_id=user.user_id,
        tenant=TenantSummary(id=user.tenant_id, name=user.tenant_name),
        display_name=user.display_name,
        role=user.role,
        permissions=list(user.permissions),
        permission_summary=permission_summary_for(user.role),
    )
