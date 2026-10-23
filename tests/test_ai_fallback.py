"""Unit tests for KiraOrder deterministic offline fallback engine.

Verifies compliance with Gate 0 v4 contract and Review Revision v2:
- F1: Decimal quantity defensive interception (both dot '2.5 ctn' and comma '1,5kg', '0,5 ctn', '2,5 liter')
- F2: Compound number words with longest-match-first
- F3: Dynamic loading of field-evidence-v2.json
- Preserves all 35 required cases:
    - H1-DEC-COMMA-NEG ('Air 500 g x 12, 3 pack' -> qty=3)
    - H1-AMT-DEC ('kalau RM12.50 boleh, ambil 4 pack' -> qty=4)
    - H1-UPM ('Milo RM2.50 satu, 10 ctn' -> qty=10)
    - Thousands currency amount ('RM1,200 for 3 ctn' -> qty=3)
"""

import pytest

from backend.ai.fallback import (
    DEFAULT_SEED_CATALOG,
    extract_fallback_line,
    extract_fallback_order,
    load_h1_lexicon,
    parse_pack_size_h1,
    parse_pack_size_h1_with_offsets,
    parse_quantity_h1,
    parse_uom_h1,
    split_into_candidate_spans,
)


def test_f3_dynamic_lexicon_loading():
    """F3: Verify that field-evidence-v2.json loads dynamically."""
    lexicon = load_h1_lexicon()
    assert lexicon["version"] == "field-evidence-v2"
    assert "quantity" in lexicon
    assert "uom_aliases" in lexicon
    assert "pack_size" in lexicon


def test_f1_dot_and_comma_decimal_interception():
    """F1: Verify that both dot and comma decimals are strictly blocked."""
    # Dot decimals
    l1 = extract_fallback_line("Minyak 2.5 ctn")
    assert l1.qty is None
    assert l1.pack_size is None
    assert l1.is_decimal_qty is True
    assert l1.issue_reason == "INVALID_QUANTITY"

    l2 = extract_fallback_line("Beras 1.5kg")
    assert l2.qty is None
    assert l2.pack_size is None
    assert l2.is_decimal_qty is True
    assert l2.issue_reason == "INVALID_QUANTITY"
    assert parse_pack_size_h1("Beras 1.5kg") == "1.5kg"
    assert parse_pack_size_h1_with_offsets("Beras 1.5kg") == ("1.5kg", 6, 11)
    assert parse_pack_size_h1("Beras 1．5kg") is None

    # Comma decimals (N10 fix)
    l3 = extract_fallback_line("Beras 1,5kg")
    assert l3.qty is None
    assert l3.pack_size is None
    assert l3.is_decimal_qty is True
    assert l3.issue_reason == "INVALID_QUANTITY"
    assert parse_pack_size_h1("Gula 1,5kg") is None
    assert parse_pack_size_h1_with_offsets("Gula 1,5kg") == (None, None, None)
    assert parse_pack_size_h1("Gula 1，5kg") is None

    l4 = extract_fallback_line("Gula 0,5 ctn")
    assert l4.qty is None
    assert l4.pack_size is None
    assert l4.is_decimal_qty is True
    assert l4.issue_reason == "INVALID_QUANTITY"

    l5 = extract_fallback_line("Minyak 2,5 liter")
    assert l5.qty is None
    assert l5.pack_size is None
    assert l5.is_decimal_qty is True
    assert l5.issue_reason == "INVALID_QUANTITY"


def test_comma_negative_cases_preserved():
    """Verify H1-DEC-COMMA-NEG: commas with spaces (list items) are NOT blocked as decimal."""
    # "12, 3" has space after comma; 3 is the order quantity, 12 is spec
    qty, reason, _, _ = parse_quantity_h1("Air 500 g x 12, 3 pack")
    assert qty == 3
    assert reason is None


def test_amounts_with_decimals_and_thousands_preserved():
    """Verify H1-AMT-DEC, H1-UPM, and thousands amounts are masked without blocking quantity."""
    # H1-AMT-DEC: RM12.50 has decimal, but order qty is 4 pack
    qty1, reason1, _, _ = parse_quantity_h1("kalau RM12.50 boleh, ambil 4 pack")
    assert qty1 == 4
    assert reason1 is None

    # H1-UPM: RM2.50 satu has decimal and marker, order qty is 10 ctn
    qty2, reason2, _, _ = parse_quantity_h1("Milo RM2.50 satu, 10 ctn")
    assert qty2 == 10
    assert reason2 is None

    # Comma currency decimal: RM2,50 satu, 10 ctn -> qty=10
    qty2_comma, reason2_comma, _, _ = parse_quantity_h1("Milo RM2,50 satu, 10 ctn")
    assert qty2_comma == 10
    assert reason2_comma is None

    # Comma currency without quantity: Milo RM2,50 -> qty=None
    qty_no_qty, _, _, _ = parse_quantity_h1("Milo RM2,50")
    assert qty_no_qty is None

    # Comma currency in negotiation: RM12,50 for 5 ctn -> qty=5
    qty_comma_for, _, _, _ = parse_quantity_h1("RM12,50 for 5 ctn")
    assert qty_comma_for == 5

    # Thousands comma: RM1,200 for 3 ctn -> qty=3
    qty3, reason3, _, _ = parse_quantity_h1("RM1,200 for 3 ctn")
    assert qty3 == 3
    assert reason3 is None


def test_f2_compound_number_words_multilingual():
    """F2: Verify compound number words across Malay, English, and Chinese."""
    qty, reason, _, _ = parse_quantity_h1("lima belas ctn")
    assert qty == 15
    assert reason is None

    qty, reason, _, _ = parse_quantity_h1("tiga puluh lima ctn")
    assert qty == 35
    assert reason is None

    qty, reason, _, _ = parse_quantity_h1("twenty-five ctn")
    assert qty == 25
    assert reason is None

    qty, reason, _, _ = parse_quantity_h1("三十五箱")
    assert qty == 35
    assert reason is None


def test_ambiguous_quantity():
    """Verify that multiple non-overlapping quantities produce AMBIGUOUS_QUANTITY."""
    qty, reason, _, _ = parse_quantity_h1("Milo satu 10 ctn")
    assert qty is None
    assert reason == "AMBIGUOUS_QUANTITY"


def test_pack_size_and_spec_protection():
    """Verify pack size specs like '10kg bawang' preserve 10, but '5kg x 2' yields 2."""
    qty1, reason1, _, _ = parse_quantity_h1("10kg bawang")
    assert qty1 == 10
    assert reason1 is None

    line2 = extract_fallback_line("Tepung 5kg x 2")
    assert line2.qty == 2
    assert line2.pack_size == "5kg"

    line3 = extract_fallback_line("Minyak 12 x 1L, 5 ctn")
    assert line3.qty == 5
    assert line3.pack_size == "12 x 1L"
    assert line3.uom == "ctn"

    line4 = extract_fallback_line("Minyak 12 x 1.5L, 5 ctn")
    assert line4.qty == 5
    assert line4.pack_size == "12 x 1.5L"
    assert line4.uom == "ctn"
    assert line4.family_id == "FAM_OIL"

    line5 = extract_fallback_line("Flour 10 ctn 1kg")
    assert line5.qty == 10
    assert line5.pack_size == "1kg"
    assert line5.uom == "ctn"
    assert line5.family_id == "FAM_FLOUR"


def test_five_acceptance_criteria_fallback():
    """Verify the 5 required acceptance criteria at fallback level."""
    # 1. 'Gula 1,5kg' -> pack=None, qty=None, INVALID_QUANTITY
    l1 = extract_fallback_line("Gula 1,5kg")
    assert l1.pack_size is None
    assert l1.qty is None
    assert l1.issue_reason == "INVALID_QUANTITY"

    # 2. 'Beras 1.5kg' -> pack=None, qty=None, INVALID_QUANTITY
    l2 = extract_fallback_line("Beras 1.5kg")
    assert l2.pack_size is None
    assert l2.qty is None
    assert l2.issue_reason == "INVALID_QUANTITY"

    # 3. 'Minyak 12 x 1.5L, 5 ctn' -> pack='12 x 1.5L', qty=5
    l3 = extract_fallback_line("Minyak 12 x 1.5L, 5 ctn")
    assert l3.pack_size == "12 x 1.5L"
    assert l3.qty == 5

    # 4. 'Minyak 12 x 1L, 5 ctn' -> pack='12 x 1L', qty=5
    l4 = extract_fallback_line("Minyak 12 x 1L, 5 ctn")
    assert l4.pack_size == "12 x 1L"
    assert l4.qty == 5

    # 5. 'Flour 10 ctn 1kg' -> pack='1kg', qty=10
    l5 = extract_fallback_line("Flour 10 ctn 1kg")
    assert l5.pack_size == "1kg"
    assert l5.qty == 10


def test_full_fallback_order_pipeline():
    """End-to-end fallback extraction test for multiple items."""
    msg = (
        "1. Tepung 5kg Grade A, 5 ctn\n"
        "2. Minyak 2,5 ctn\n"
        "3. Beras Wangi 10 ctn"
    )
    lines = extract_fallback_order(msg)
    assert len(lines) == 3

    assert lines[0].family_id == "FAM_FLOUR"
    assert lines[0].qty == 5
    assert lines[0].uom == "ctn"

    # Line 2 has decimal qty -> blocked
    assert lines[1].family_id == "FAM_OIL"
    assert lines[1].qty is None
    assert lines[1].is_decimal_qty is True
    assert lines[1].issue_reason == "INVALID_QUANTITY"

    assert lines[2].family_id == "FAM_RICE"
    assert lines[2].qty == 10
    assert lines[2].uom == "ctn"
