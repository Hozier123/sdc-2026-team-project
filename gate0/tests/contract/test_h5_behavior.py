import json
from pathlib import Path

from contract_oracles import detect_condition_kinds, evaluate_condition


LEXICON = Path(__file__).parents[2] / "contracts" / "lexicons" / "condition-triggers-v3.json"


def test_all_16_h5_truth_table_rows_execute_with_exact_labels():
    cases = json.loads(LEXICON.read_text(encoding="utf-8"))["truth_table"]
    for case in cases:
        actual = evaluate_condition(case["input"])
        assert actual["kinds"] == case["kinds"], case["id"]
        assert actual["price_basis"] == case["price_basis"], case["id"]
        if "blocking" in case:
            assert actual["blocking"] == case["blocking"], case["id"]


def test_h5_price_basis_values_are_legal_and_allocation_remains_unallocated():
    cases = json.loads(LEXICON.read_text(encoding="utf-8"))["truth_table"]
    assert {case["price_basis"] for case in cases}.issubset({None, "UNIT", "TOTAL", "UNKNOWN"})
    allocation = next(case for case in cases if case["id"] == 10)
    assert allocation["price_basis"] == "UNKNOWN"
    assert allocation["amount_allocation"] == "UNALLOCATED"
    explicit_unit = next(case for case in cases if case["id"] == 12)
    assert explicit_unit["price_basis"] == "UNIT"
    assert explicit_unit["amount_allocation"] == "UNIT_EXPLICIT"


def test_discount_negation_is_a_machine_checked_near_neighbor():
    assert detect_condition_kinds("I am not asking for discount.") == []
    assert detect_condition_kinds("harga lama RM95 sudah bayar") == []


def test_new_price_variants_are_explicitly_covered():
    for text in ("can less?", "老价钱?", "harga lama?", "boleh diskaun?"):
        assert detect_condition_kinds(text) == ["PRICE"], text
