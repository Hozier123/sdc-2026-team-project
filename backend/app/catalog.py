"""B02: a bounded, read-only product directory for the authenticated tenant."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.errors import ForbiddenActionError

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])
CATALOG_LIMIT = 100


class CatalogProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: str
    display_name: str
    pack_size: str | None
    grade: str | None
    base_unit: str


class CatalogProductsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CatalogProduct]
    limit: Literal[100] = CATALOG_LIMIT
    truncated: bool


@router.get(
    "/products",
    response_model=CatalogProductsResponse,
    responses={
        401: {"description": "Invalid or missing token"},
        403: {"description": "Only CLERK and OWNER may read the product directory"},
    },
)
def list_products(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogProductsResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()

    with connect(settings) as conn:
        rows = conn.execute(
            "SELECT product_id, name, pack_size, grade, base_unit FROM products "
            'WHERE tenant_id=%s AND active=true ORDER BY product_id COLLATE "C" LIMIT %s',
            (user.tenant_id, CATALOG_LIMIT + 1),
        ).fetchall()

    return CatalogProductsResponse(
        items=[
            CatalogProduct(
                sku_id=row[0],
                display_name=row[1],
                pack_size=row[2],
                grade=row[3],
                base_unit=row[4],
            )
            for row in rows[:CATALOG_LIMIT]
        ],
        truncated=len(rows) > CATALOG_LIMIT,
    )
