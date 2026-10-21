import json
from pathlib import Path

from contract_oracles import evaluate_h1_case


LEXICON = Path(__file__).parents[2] / "contracts" / "lexicons" / "field-evidence-v2.json"


def test_every_h1_required_case_executes_against_the_deterministic_oracle():
    cases = json.loads(LEXICON.read_text(encoding="utf-8"))["required_cases"]
    assert {case["id"] for case in cases} == {
        "H1-MS", "H1-EN", "H1-ZH", "H1-UOM", "H1-UOM-ATTACHED",
        "H1-UOM-UPPER", "H1-UOM-MIXED",
        "H1-TYPE", "H1-TYPE-NEG", "H1-TYPE-NEG2",
        "H1-MS-TEENS", "H1-MS-TENS", "H1-MS-TENS-UNIT",
        "H1-EN-TEEN", "H1-EN-COMPOUND",
        "H1-ZH-TEENS", "H1-ZH-TENS",
        "H1-DEC-1", "H1-DEC-2", "H1-DEC-NEG",
        "H1-AMT", "H1-AMT-NEG", "H1-AMT-DEC",
        "H1-PACK-1", "H1-PACK-2", "H1-PACK-3", "H1-PACK-4",
        "H1-AMB-1", "H1-UPM", "H1-UNIT-PRICE", "H1-DEC-COMMA-NEG", "H1-UOM-PLURAL",
        "DEV-39", "DEV-40", "DEV-41",
    }
    for case in cases:
        actual = evaluate_h1_case(case)
        for key in ("qty", "uom", "pack_size", "diagnostic", "model_value_accepted", "family", "issue", "reason_code"):
            if key in case:
                assert actual.get(key) == case[key], f"{case['id']}: {key}"


def test_qty_evidence_offsets_are_present_and_slice_correct():
    cases = {case["id"]: case for case in json.loads(LEXICON.read_text(encoding="utf-8"))["required_cases"]}
    expected = {
        "H1-AMT": (17, 18, "3"),
        "H1-AMT-NEG": (9, 10, "5"),
        "H1-AMT-DEC": (27, 28, "4"),
        "H1-UOM-UPPER": (0, 1, "5"),
    }
    for case_id, (start, end, text) in expected.items():
        actual = evaluate_h1_case(cases[case_id])
        assert (actual["qty_start"], actual["qty_end"]) == (start, end), case_id
        span = cases[case_id]["span"].casefold()
        assert span[start:end] == text, case_id
