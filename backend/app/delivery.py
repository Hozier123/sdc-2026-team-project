"""Read immutable delivery orders for CLERK/OWNER."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.errors import ForbiddenActionError, ResourceNotFoundError
from app.schemas import DeliveryOrder

router = APIRouter(prefix="/api/v1", tags=["DeliveryOrders"])


@router.get(
    "/delivery-orders/{do_number}",
    response_model=DeliveryOrder,
    responses={
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "WAREHOUSE must use the warehouse endpoint"},
        404: {"description": "DO not found in tenant"},
    },
)
def get_delivery_order(
    do_number: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeliveryOrder:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    with connect(settings) as conn:
        row = conn.execute(
            "SELECT do_number, draft_id, draft_version, customer_id, customer_name, "
            "lines, final_total_rm, prepared_by, approved_by, escalation_reasons, "
            "approval_mode, reply_draft, related_do_number, approved_at "
            "FROM delivery_orders WHERE tenant_id=%s AND do_number=%s",
            (user.tenant_id, do_number),
        ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return DeliveryOrder(
        do_number=row[0],
        draft_id=row[1],
        draft_version=row[2],
        customer_id=row[3],
        customer_name=row[4],
        lines=row[5],
        final_total_rm=format(row[6], ".2f"),
        prepared_by=row[7],
        approved_by=row[8],
        escalation_reasons=row[9] or [],
        approval_mode=row[10],
        reply_draft=row[11],
        related_do_number=row[12],
        approved_at=row[13],
    )
