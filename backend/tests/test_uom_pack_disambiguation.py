"""UOM must come from the quantity, not from inside the pack size."""

from __future__ import annotations

import pytest

from app.ai.fallback import parse_uom_h1, parse_uom_h1_with_offsets


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tepung Gandum 5 bag 1kg", "bag"),
        ("Tepung Gandum 5 ctn 1kg", "ctn"),
        ("Beras Wangi 10 bag", "bag"),
        ("Minyak Masak 1,5kg", "kg"),
    ],
)
def test_uom_is_not_taken_from_pack_size(text, expected):
    assert parse_uom_h1(text) == expected
    value, start, end = parse_uom_h1_with_offsets(text)
    assert value == expected
    assert start is not None and end is not None
