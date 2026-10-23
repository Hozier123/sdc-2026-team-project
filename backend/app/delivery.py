"""Read immutable delivery orders for CLERK/OWNER."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.errors import ForbiddenActionError
from app.read_models import _delivery_order
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
        delivery_order, _ = _delivery_order(conn, user.tenant_id, do_number)
    return delivery_order
