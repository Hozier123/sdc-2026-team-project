"""Resolver must not auto-pick a SKU when UOM is missing and units differ."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.extraction.base import RawRow
from app.extraction.evidence import quantity_evidence
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
    pack_size="散装",
    grade=None,
    base_unit="kg",
    tier_price=Decimal("3.50"),
    available_qty=100,
)
MINYAK_BTL = CatalogProduct(
    sku_id="SKU_MINYAK_5KG",
    family_id="FAM_MINYAK",
    name="Minyak 5kg",
    pack_size="5kg",
    grade=None,
    base_unit="btl",
    tier_price=Decimal("29.00"),
    available_qty=25,
)
MINYAK_PAIL = CatalogProduct(
    sku_id="SKU_MINYAK_17KG",
    family_id="FAM_MINYAK",
    name="Minyak 17kg",
    pack_size="17kg",
    grade=None,
    base_unit="pail",
    tier_price=Decimal("94.00"),
    available_qty=15,
)

CATALOG = Catalog(products=(BAG, KG, MINYAK_BTL, MINYAK_PAIL), aliases=())

# The seven D02 lines, with the unit deliberately absent as in the AI output.
# Each one must produce the MISSING_UOM candidate path, never a SKU.
D02_GAPS = [
    ("DEV-01", "10kg Bawang Bsr India", 10, "10kg", "FAM_BAWANG"),
    ("DEV-05", "Bawang Bsr India 50kg", 50, "50kg", "FAM_BAWANG"),
    ("DEV-11", "50kg Bawang Bsr India", 50, "50kg", "FAM_BAWANG"),
    ("DEV-33", "kalau ada bagi 50kg Bawang Bsr India", 50, "50kg", "FAM_BAWANG"),
    ("DEV-07", "4 botol minyak 5kg", 4, "5kg", "FAM_MINYAK"),
    ("DEV-13", "1 pail Minyak 17kg", 1, "17kg", "FAM_MINYAK"),
    ("DEV-27", "5 pail Minyak 17kg", 5, "17kg", "FAM_MINYAK"),
]


def _catalog(*products: CatalogProduct) -> Catalog:
    return Catalog(products=products, aliases=())


@pytest.mark.parametrize(("case", "span", "qty", "pack", "family"), D02_GAPS)
def test_d02_gaps_require_an_explicit_uom_choice(case, span, qty, pack, family):
    result = resolve_row(
        RawRow(span=span, qty=qty, uom=None, fam=family, pack_size=pack),
        CATALOG,
    )

    assert result.product is None, case
    assert result.issue_code == "MISSING_UOM", case
    expected = (
        {"SKU_BAWANG_KG", "SKU_BAWANG_10KG"}
        if family == "FAM_BAWANG"
        else {"SKU_MINYAK_5KG", "SKU_MINYAK_17KG"}
    )
    assert {candidate.sku_id for candidate in result.candidates} == expected, case


def test_explicit_kg_selects_bulk_sku_even_when_weight_is_in_the_span():
    """`10kg Bawang` with uom=kg is loose stock, not the 10kg bag."""
    result = resolve_row(
        RawRow(
            span="Bawang Bsr India 10kg",
            qty=10,
            uom="kg",
            fam="FAM_BAWANG",
            pack_size="10kg",
        ),
        CATALOG,
    )

    assert result.product == KG
    assert result.issue_code is None


def test_explicit_bag_still_selects_the_10kg_bag_sku():
    result = resolve_row(
        RawRow(span="1 bag Bawang 10kg", qty=1, uom="bag", fam="FAM_BAWANG", pack_size="10kg"),
        CATALOG,
    )

    assert result.product == BAG
    assert result.issue_code is None


def test_contradictory_bag_pack_stays_unresolved():
    """A bag with a non-existent 5kg pack must not fall back to the bulk SKU."""
    result = resolve_row(
        RawRow(span="Bawang 5kg bag", qty=1, uom="bag", fam="FAM_BAWANG", pack_size="5kg"),
        CATALOG,
    )

    assert result.product is None
    assert result.candidates == ()


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


def test_decimal_quantity_is_invalid_not_split_or_rounded():
    assert quantity_evidence("Bawang 2.5kg") == (None, "INVALID_QUANTITY", None, None)
