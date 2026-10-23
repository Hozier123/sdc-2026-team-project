"""B25 deterministic field evidence tests."""

import pytest

from app.extraction.base import RawExtraction, RawRow, validate_raw_extraction
from app.extraction.evidence import pack_size_evidence


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        ("Milo 2kg, 4 ctn", "2kg"),
        ("Minyak 12 x 1L, 5 ctn", "12 x 1L"),
        ("Tepung 5kg x 2", "5kg"),
        ("美禄 500g 装, 3 包", "500g"),
    ],
)
def test_pack_size_evidence_uses_registered_pattern(span, expected):
    evidence = pack_size_evidence(span)
    assert evidence is not None
    value, start, end = evidence
    assert value == expected
    assert span[start:end].replace(" 装", "") == expected


def test_pack_size_evidence_returns_none_without_pack():
    assert pack_size_evidence("Milo 5 ctn") is None


def test_non_strict_validation_isolates_bad_rows():
    raw = RawExtraction(
        rows=(
            RawRow(span="Milo 5 ctn", qty=5, fam="FAM_MILO"),
            RawRow(span="missing span", qty=1, fam="FAM_MILO"),
        )
    )
    validated = validate_raw_extraction(raw, "Milo 5 ctn", strict=False)
    assert validated.rows[0].invalid_reason is None
    assert validated.rows[1].invalid_reason == "SOURCE_EVIDENCE_INVALID"


def test_strict_validation_still_rejects_bad_rows():
    raw = RawExtraction(rows=(RawRow(span="missing span", qty=1),))
    with pytest.raises(ValueError):
        validate_raw_extraction(raw, "Milo 5 ctn", strict=True)
