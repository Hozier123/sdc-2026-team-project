"""Resolver must not auto-pick a SKU when UOM is missing and units differ."""

from __future__ import annotations

from decimal import Decimal

from app.extraction.base import RawRow
from app.resolver import Catalog, CatalogProduct, resolve_row

BAG = CatalogProduct(
    sku_id="SKU_BAWANG_10KG",
    family_id="FAM_BAWANG",
    name="Bawang 10kg",
    pack_size="10kg",
    grade=None,
    base_unit="bag",
    tier_price=Decimal("32.00"),
    available_qty=10,
)
KG = CatalogProduct(
    sku_id="SKU_BAWANG_KG",
    family_id="FAM_BAWANG",
    name="Bawang bulk",
    pack_size="bulk",
    grade=None,
    base_unit="kg",
    tier_price=Decimal("3.50"),
    available_qty=100,
)


def _catalog(*products: CatalogProduct) -> Catalog:
    return Catalog(products=products, aliases=())


def test_missing_uom_with_mixed_base_units_does_not_select_a_sku():
    result = resolve_row(
        RawRow(span="Bawang 10kg", qty=10, uom=None, fam="FAM_BAWANG", pack_size="10kg"),
        _catalog(BAG, KG),
    )

    assert result.product is None
    assert result.issue_code == "MISSING_UOM"
    assert {candidate.sku_id for candidate in result.candidates} == {
        "SKU_BAWANG_10KG",
        "SKU_BAWANG_KG",
    }


def test_explicit_kg_selects_bulk_sku():
    result = resolve_row(
        RawRow(span="Bawang 10kg", qty=10, uom="kg", fam="FAM_BAWANG", pack_size=None),
        _catalog(BAG, KG),
    )

    assert result.product == KG


def test_missing_uom_can_still_resolve_single_base_unit_family():
    result = resolve_row(
        RawRow(span="Tepung 10kg", qty=10, uom=None, fam="FAM_TEPUNG", pack_size="10kg"),
        _catalog(
            CatalogProduct(
                sku_id="SKU_TEPUNG_10KG",
                family_id="FAM_TEPUNG",
                name="Tepung 10kg",
                pack_size="10kg",
                grade=None,
                base_unit="bag",
                tier_price=Decimal("20.00"),
                available_qty=10,
            )
        ),
    )

    assert result.product is not None
    assert result.product.sku_id == "SKU_TEPUNG_10KG"
