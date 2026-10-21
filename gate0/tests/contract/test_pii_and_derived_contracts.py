import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"


def test_mask_tokens_are_single_versioned_vocabulary():
    lexicon = json.loads(
        (ROOT / "contracts" / "lexicons" / "pii-mask-tokens-v1.json").read_text(encoding="utf-8")
    )
    assert set(lexicon["tokens"].values()) == {
        "[REDACTED_PHONE]", "[REDACTED_MYKAD]", "[REDACTED_EMAIL]",
    }
    for path in FIXTURES.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "[PHONE]" not in text
        assert "[MYKAD]" not in text
        assert "[EMAIL]" not in text


def test_condition_id_is_deterministic_and_conditions_are_an_exact_derived_subset():
    fixture = json.loads((FIXTURES / "parse_draft.json").read_text(encoding="utf-8"))
    body = fixture["body"]
    issue = body["issues"][0]
    canonical = f"{body['draft_id']}|{issue['condition_kind']}|{issue['span_start']}|{issue['span_end']}"
    expected = "CND_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24].upper()
    assert issue["condition_id"] == expected
    assert body["conditions"] == [item for item in body["issues"] if item["code"] == "CUSTOMER_CONDITION"]


def test_bootstrap_script_installs_both_locked_dependency_sets_and_runs_verifier():
    script = (ROOT / "scripts" / "bootstrap_gate0.ps1").read_text(encoding="utf-8")
    assert "requirements.txt" in script
    # The implementation delegates to Invoke-Pnpm so it can fall back to
    # GATE0_PNPM / corepack / npx; assert the behavior, not one literal line.
    assert "Invoke-Pnpm" in script
    assert "'install'" in script or '"install"' in script
    assert "--frozen-lockfile" in script
    assert "scripts\\verify_gate0.py" in script


def test_clerk_approval_fixture_is_self_only_and_read_only():
    fixture = json.loads((FIXTURES / "approval_list_clerk.json").read_text(encoding="utf-8"))
    assert "mine=true" in fixture["path"]
    for item in fixture["body"]["items"]:
        assert item["requested_by"] == "USR_CLERK_01"
        assert item["allowed_actions"] == []


def test_approve_202_is_caller_scoped_not_owner_actions():
    fixture = json.loads((FIXTURES / "approve_202.json").read_text(encoding="utf-8"))
    assert fixture["body"]["allowed_actions"] == []


def test_save_with_insufficient_stock_is_200_and_increments_version():
    fixture = json.loads((FIXTURES / "save_lines_insufficient_stock_200.json").read_text(encoding="utf-8"))
    assert fixture["status"] == 200
    assert fixture["body"]["version"] == 2
    assert fixture["body"]["status"] == "DISAMBIGUATION_REQUIRED"
    assert "INSUFFICIENT_STOCK" in fixture["body"]["blocking_issues"]
    issue = fixture["body"]["issues"][0]
    assert issue["line_id"] == "LIN_001"
    assert issue["span"] == "Tepung 5 ctn"
    assert fixture["body"]["clarification_draft"] is not None
    assert "COPY_CLARIFICATION" in fixture["body"]["allowed_actions"]
