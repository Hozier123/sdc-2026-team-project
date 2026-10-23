"""Regression tests for comma-decimal pack sizes from canonical AI samples."""

from __future__ import annotations

import pytest

from app.ai.fallback import parse_pack_size_h1, parse_pack_size_h1_with_offsets


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Minyak Masak 1,5kg", None),
        ("Minyak Masak 1,5 kg", None),
        ("Tepung Gandum 5 ctn 1kg", "1kg"),
        ("Minyak Masak 5kg", "5kg"),
        ("Minyak 12 x 1L", "12 x 1L"),
    ],
)
def test_pack_size_does_not_start_inside_comma_decimal(text, expected):
    assert parse_pack_size_h1(text) == expected
    value, start, end = parse_pack_size_h1_with_offsets(text)
    assert value == expected
    if expected is None:
        assert start is None and end is None
    else:
        assert start is not None and end is not None
