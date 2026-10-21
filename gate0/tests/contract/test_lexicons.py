import json
from pathlib import Path


LEXICONS = Path(__file__).parents[2] / "contracts" / "lexicons"


def test_lexicons_are_versioned_json():
    for path in sorted(LEXICONS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] in path.stem


def test_h5_truth_table_has_exactly_16_unique_cases():
    data = json.loads((LEXICONS / "condition-triggers-v3.json").read_text(encoding="utf-8"))
    cases = data["truth_table"]
    assert len(cases) == 16
    assert [case["id"] for case in cases] == list(range(1, 17))
    assert len({case["input"] for case in cases}) == 16
    assert next(case for case in cases if case["id"] == 6)["kinds"] == ["STOCK", "PRICE"]
    assert next(case for case in cases if case["id"] == 12)["price_basis"] == "UNIT"
    assert next(case for case in cases if case["id"] == 13)["input"] == "can less?"
    assert next(case for case in cases if case["id"] == 14)["input"] == "老价钱?"
    assert next(case for case in cases if case["id"] == 15)["input"] == "harga lama?"


def test_h1_lexicon_has_three_languages_and_units():
    data = json.loads((LEXICONS / "field-evidence-v2.json").read_text(encoding="utf-8"))
    quantity = data["quantity"]
    assert {"ms_units", "en_values", "zh_values"}.issubset(quantity)
    assert data["uom_aliases"]["ctn"]
    assert data["uom_aliases"]["bag"]
    assert data["tenant_uom_source"] == "uom_aliases"
    assert data["fuzzy_matching_allowed"] is False
    assert len(data["required_cases"]) >= 20
