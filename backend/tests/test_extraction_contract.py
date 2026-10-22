import pytest

from app.extraction.base import RawExtraction, RawRow, validate_raw_extraction


def test_valid_raw_extraction_is_returned():
    raw = RawExtraction(rows=(RawRow(span="5 ctn", qty=5, uom="ctn"),))
    assert validate_raw_extraction(raw, "Tepung 5 ctn") is raw


def test_row_span_must_exist_in_masked_text():
    raw = RawExtraction(rows=(RawRow(span="6 ctn", qty=6),))
    with pytest.raises(ValueError, match="span"):
        validate_raw_extraction(raw, "Tepung 5 ctn")


@pytest.mark.parametrize("qty", [0, -1, "5", 1.5])
def test_qty_must_be_positive_integer_or_null(qty):
    raw = RawExtraction(rows=(RawRow(span="5 ctn", qty=qty),))
    with pytest.raises(ValueError, match="qty"):
        validate_raw_extraction(raw, "Tepung 5 ctn")


def test_provider_must_return_raw_extraction():
    with pytest.raises(TypeError):
        validate_raw_extraction({"rows": []}, "Tepung 5 ctn")


def test_rows_must_be_raw_rows():
    with pytest.raises(TypeError):
        validate_raw_extraction(RawExtraction(rows=({"span": "5 ctn"},)), "Tepung 5 ctn")
