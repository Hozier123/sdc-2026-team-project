"""Unit tests for PII masking engine (backend/privacy/pii.py).

Verifies compliance with:
- Gate 0 contract: pii-mask-tokens-v1.json
- Test cases: DEV-07, DEV-24
- False positive resistance for order quantities, SKUs, and prices
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.privacy.pii import (
    MASK_TOKENS,
    TOKEN_EMAIL,
    TOKEN_MYKAD,
    TOKEN_PHONE,
    mask_pii,
)


def test_token_constants_match_gate0_canonical() -> None:
    """Ensure token constants strictly match Gate 0 specification."""
    assert TOKEN_PHONE == "[REDACTED_PHONE]"
    assert TOKEN_MYKAD == "[REDACTED_MYKAD]"
    assert TOKEN_EMAIL == "[REDACTED_EMAIL]"
    assert set(MASK_TOKENS) == {
        "[REDACTED_PHONE]",
        "[REDACTED_MYKAD]",
        "[REDACTED_EMAIL]",
    }


def test_dev_07_phone_preserves_order_and_price() -> None:
    """DEV-07: Mask phone number without corrupting product name, qty, or price."""
    raw = "Tepung 5 ctn, kalau RM95 boleh? Call +60 12-345 6789"
    res = mask_pii(raw)

    assert res.masked_text == "Tepung 5 ctn, kalau RM95 boleh? Call [REDACTED_PHONE]"
    assert res.phone_count == 1
    assert res.mykad_count == 0
    assert res.email_count == 0
    assert res.total_redacted == 1
    assert res.has_pii is True


def test_dev_24_mykad_and_phone_combination() -> None:
    """DEV-24: Mask both MyKad identity numbers and contact phones."""
    raw = "Driver IC 980101-14-5555, contact 012-3456789, deliver to warehouse"
    res = mask_pii(raw)

    assert (
        res.masked_text
        == "Driver IC [REDACTED_MYKAD], contact [REDACTED_PHONE], deliver to warehouse"
    )
    assert res.phone_count == 1
    assert res.mykad_count == 1
    assert res.total_redacted == 2


def test_phone_number_formats() -> None:
    """Verify various Malaysian phone number writing styles."""
    cases = [
        ("+60123456789", "[REDACTED_PHONE]"),
        ("+60 12-345 6789", "[REDACTED_PHONE]"),
        ("6019-8765432", "[REDACTED_PHONE]"),
        ("011-12345678", "[REDACTED_PHONE]"),
        ("0123456789", "[REDACTED_PHONE]"),
        ("03-98765432", "[REDACTED_PHONE]"),
        ("+60 3-1234 5678", "[REDACTED_PHONE]"),
    ]
    for raw, expected in cases:
        res = mask_pii(raw)
        assert res.masked_text == expected, f"Failed on raw phone: {raw}"
        assert res.phone_count == 1


def test_mykad_formats() -> None:
    """Verify various MyKad formatting conventions."""
    cases = [
        ("010203-10-1234", "[REDACTED_MYKAD]"),
        ("951231 01 5678", "[REDACTED_MYKAD]"),
        ("880808145555", "[REDACTED_MYKAD]"),
    ]
    for raw, expected in cases:
        res = mask_pii(raw)
        assert res.masked_text == expected, f"Failed on raw MyKad: {raw}"
        assert res.mykad_count == 1


def test_email_masking() -> None:
    """Verify email address masking."""
    raw = "Please send invoice to finance.mgr+ap@kedaimaju.com.my and cc boss@gmail.com"
    res = mask_pii(raw)
    assert (
        res.masked_text
        == "Please send invoice to [REDACTED_EMAIL] and cc [REDACTED_EMAIL]"
    )
    assert res.email_count == 2


def test_false_positive_resistance() -> None:
    """Ensure normal business terms, quantities, dates, and SKUs are NOT masked."""
    benign_text = (
        "Order 100 ctn of SKU-980101 and 5000 kg Sugar at RM1200. "
        "Delivered on 2026-10-21. Stock code A95."
    )
    res = mask_pii(benign_text)
    assert res.masked_text == benign_text
    assert res.total_redacted == 0
    assert res.has_pii is False


def test_empty_string_handling() -> None:
    """Ensure empty or blank strings return clean empty result."""
    res = mask_pii("")
    assert res.masked_text == ""
    assert res.total_redacted == 0
    assert res.has_pii is False
