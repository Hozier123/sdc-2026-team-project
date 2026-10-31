"""D02 UOM semantics: parse-draft blocking and adjacent counterexamples.

These tests exercise the backend draft builder without a database. The catalog
mirrors the T1 seed values that matter for D02: Bawang has a bulk kg SKU
("散装") and a 10kg bag SKU; Minyak has a btl 5kg SKU and a pail 17kg SKU.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.extraction.base import RawExtraction, RawRow
from app.extraction.evidence import evidenced_uom
from app.parse import _ai_draft
from app.resolver import Catalog, CatalogProduct

BAWANG_KG = CatalogProduct(
    sku_id="SKU_BAWANG_KG",
    family_id="FAM_BAWANG",
    name="Bawang besar India 印度洋葱",
    pack_size="散装",
    grade=None,
    base_unit="kg",
    tier_price=Decimal("3.50"),
    available_qty=40,
)
BAWANG_BAG = CatalogProduct(
    sku_id="SKU_BAWANG_10KG",
    family_id="FAM_BAWANG",
    name="Bawang besar India 印度洋葱",
    pack_size="10kg",
    grade=None,
    base_unit="bag",
    tier_price=Decimal("32.00"),
    available_qty=15,
)
MINYAK_BTL = CatalogProduct(
    sku_id="SKU_MINYAK_5KG",
    family_id="FAM_MINYAK",
    name="Minyak masak 食用油",
    pack_size="5kg",
    grade=None,
    base_unit="btl",
    tier_price=Decimal("29.00"),
    available_qty=25,
)
MINYAK_PAIL = CatalogProduct(
    sku_id="SKU_MINYAK_17KG",
    family_id="FAM_MINYAK",
    name="Minyak masak 食用油",
    pack_size="17kg",
    grade=None,
    base_unit="pail",
    tier_price=Decimal("94.00"),
    available_qty=15,
)
CATALOG = Catalog(
    products=(BAWANG_KG, BAWANG_BAG, MINYAK_BTL, MINYAK_PAIL),
    aliases=(),
)

CUSTOMER = {
    "tenant_id": "T1",
    "customer_id": "CUS_T1",
    "name": "Customer One",
    "tier": "A",
    "credit_flag": "NONE",
    "phone_e164": None,
}

D02_GAPS = [
    ("DEV-01", "10kg Bawang Bsr India", 10, "10kg", "FAM_BAWANG"),
    ("DEV-05", "Bawang Bsr India 50kg", 50, "50kg", "FAM_BAWANG"),
    ("DEV-11", "50kg Bawang Bsr India", 50, "50kg", "FAM_BAWANG"),
    ("DEV-33", "kalau ada bagi 50kg Bawang Bsr India", 50, "50kg", "FAM_BAWANG"),
    ("DEV-07", "4 botol minyak 5kg", 4, "5kg", "FAM_MINYAK"),
    ("DEV-13", "1 pail Minyak 17kg", 1, "17kg", "FAM_MINYAK"),
    ("DEV-27", "5 pail Minyak 17kg", 5, "17kg", "FAM_MINYAK"),
]


def _draft(rows, text, catalog=CATALOG, *, language_hint="en"):
    return _ai_draft(
        customer=CUSTOMER,
        masked_text=text,
        raw=RawExtraction(rows=tuple(rows)),
        draft_id="DRF_D02",
        now="2026-10-31T00:00:00+00:00",
        language_hint=language_hint,
        catalog=catalog,
        conn=None,
        checks=None,
    )


def _codes(draft):
    return [issue["code"] for issue in draft["issues"]]


@pytest.mark.parametrize(("case", "span", "qty", "pack", "family"), D02_GAPS)
def test_d02_parse_blocks_missing_uom_and_keeps_candidates(case, span, qty, pack, family):
    draft = _draft(
        [RawRow(span=span, qty=qty, uom=None, fam=family, pack_size=pack)],
        span,
    )

    assert draft["status"] == "DISAMBIGUATION_REQUIRED", case
    line = draft["lines"][0]
    assert line["sku_id"] is None, case
    assert line["uom"] is None, case
    assert line["pack_size"] == pack, case
    expected = (
        {"SKU_BAWANG_KG", "SKU_BAWANG_10KG"}
        if family == "FAM_BAWANG"
        else {"SKU_MINYAK_5KG", "SKU_MINYAK_17KG"}
    )
    assert {candidate["sku_id"] for candidate in line["candidate_skus"]} == expected, case

    missing = [issue for issue in draft["issues"] if issue["code"] == "MISSING_UOM"]
    assert len(missing) == 1, case
    assert missing[0]["blocking"] is True, case
    assert missing[0]["ask"] == "CLERK", case
    assert missing[0]["reason_code"] == "FIELD_NOT_EVIDENCED", case
    assert missing[0]["line_id"] == line["line_id"], case

    assert "APPROVE_AND_GENERATE_DO" in draft["blocked_actions"], case
    assert "MISSING_UOM" in draft["blocked_actions"]["APPROVE_AND_GENERATE_DO"], case
    assert "APPROVE_AND_GENERATE_DO" not in draft["allowed_actions"], case
    assert "COPY_CLARIFICATION" in draft["allowed_actions"], case
    assert draft["clarification_draft"] is not None, case

    # The clarification offers both base units instead of picking one.
    units = {candidate["base_unit"] for candidate in line["candidate_skus"]}
    message = draft["clarification_draft"]["message"]
    for unit in units:
        assert unit in message, (case, unit, message)


def test_explicit_bag_selects_bag_sku_without_a_missing_uom_issue():
    draft = _draft(
        [RawRow(span="1 bag Bawang 10kg", qty=1, uom="bag", fam="FAM_BAWANG", pack_size="10kg")],
        "1 bag Bawang 10kg",
    )

    assert draft["status"] == "READY_FOR_APPROVAL"
    line = draft["lines"][0]
    assert line["sku_id"] == "SKU_BAWANG_10KG"
    assert line["uom"] == "bag"
    assert line["pack_size"] == "10kg"
    assert "MISSING_UOM" not in _codes(draft)
    assert "APPROVE_AND_GENERATE_DO" in draft["allowed_actions"]
    assert draft["blocked_actions"] == {}


def test_explicit_kg_does_not_promote_the_weight_to_a_10kg_bag():
    draft = _draft(
        [
            RawRow(
                span="Bawang Bsr India 10kg",
                qty=10,
                uom="kg",
                fam="FAM_BAWANG",
                pack_size="10kg",
            )
        ],
        "Bawang Bsr India 10kg",
    )

    assert draft["status"] == "READY_FOR_APPROVAL"
    line = draft["lines"][0]
    assert line["sku_id"] == "SKU_BAWANG_KG"
    assert line["uom"] == "kg"
    assert line["pack_size"] == "散装"
    assert line["subtotal_rm"] == "35.00"
    assert "MISSING_UOM" not in _codes(draft)


def test_decimal_quantity_blocks_as_invalid_quantity_without_a_line():
    draft = _draft(
        [RawRow(span="Bawang 2.5kg", qty=2, uom=None, fam="FAM_BAWANG", pack_size="2.5kg")],
        "Bawang 2.5kg",
    )

    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    assert draft["lines"] == []
    assert _codes(draft) == ["LOW_CONFIDENCE_MATCH"]
    assert draft["issues"][0]["reason_code"] == "INVALID_QUANTITY"
    assert draft["issues"][0]["blocking"] is True
    assert "APPROVE_AND_GENERATE_DO" in draft["blocked_actions"]


def test_single_base_unit_family_pack_ambiguity_is_not_mislabelled_missing_uom():
    milo_1kg = CatalogProduct(
        sku_id="SKU_MILO_1KG",
        family_id="FAM_MILO",
        name="Milo 1kg",
        pack_size="1kg",
        grade=None,
        base_unit="ctn",
        tier_price=Decimal("5.00"),
        available_qty=10,
    )
    milo_2kg = CatalogProduct(
        sku_id="SKU_MILO_2KG",
        family_id="FAM_MILO",
        name="Milo 2kg",
        pack_size="2kg",
        grade=None,
        base_unit="ctn",
        tier_price=Decimal("9.00"),
        available_qty=10,
    )
    draft = _draft(
        [RawRow(span="Milo 2 bag", qty=2, uom=None, fam="FAM_MILO", pack_size=None)],
        "Milo 2 bag",
        Catalog(products=(milo_1kg, milo_2kg), aliases=()),
    )

    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    assert _codes(draft) == ["MULTIPLE_PACK_SIZES"]
    assert "MISSING_UOM" not in draft["blocked_actions"]["APPROVE_AND_GENERATE_DO"]
    assert "MULTIPLE_PACK_SIZES" in draft["blocked_actions"]["APPROVE_AND_GENERATE_DO"]
    message = draft["clarification_draft"]["message"]
    assert "1kg" in message and "2kg" in message
    assert "ctn (RM 5.00/ctn) / ctn" not in message


def test_tenant_uom_aliases_are_only_used_within_the_owning_tenant():
    t1_units = [
        ("bag", "bag"),
        ("btl", "botol"),
        ("btl", "bottle"),
        ("kg", "kg"),
        ("pail", "pail"),
    ]
    t2_units = [
        ("btl", "botol"),
        ("btl", "bottle"),
        ("pack", "pkt"),
    ]

    assert evidenced_uom("botol", "4 botol minyak 5kg", t1_units) == "btl"
    assert evidenced_uom("botol", "4 botol minyak 5kg", t2_units) == "btl"
    assert evidenced_uom("btl", "4 botol minyak 5kg", t1_units) == "btl"
    assert evidenced_uom("pail", "1 pail Minyak 17kg", t1_units) == "pail"
    assert evidenced_uom("pail", "1 pail Minyak 17kg", t2_units) is None
    assert evidenced_uom("btl", "Minyak 17kg", t1_units) is None
    assert evidenced_uom(None, "4 botol minyak 5kg", t1_units) is None
