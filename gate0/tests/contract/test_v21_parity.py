import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def test_every_external_manifest_input_matches_recorded_hash_and_size():
    manifest = json.loads((ROOT / "baseline-manifest.json").read_text(encoding="utf-8"))
    keys = (
        "baseline", "proposal", "review", "prior_review", "orbyte_reference",
        "execution_manual", "gate0_review", "gate0_revision2_review",
    )
    for key in keys:
        record = manifest[key]
        path = ROOT / record["path"]
        assert path.is_file(), key
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == record["sha256"], key
        if "bytes" in record:
            assert path.stat().st_size == record["bytes"], key


def test_protected_01_to_04_files_still_match_gate0_entry_hashes():
    manifest = json.loads((ROOT / "baseline-manifest.json").read_text(encoding="utf-8"))
    for record in manifest["protected_files_at_gate0"]:
        path = ROOT / record["path"]
        assert path.is_file(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == record["sha256"]


def test_v21_baseline_file_hash_and_critical_terms_are_still_present():
    manifest = json.loads((ROOT / "baseline-manifest.json").read_text(encoding="utf-8"))
    record = manifest["baseline"]
    path = ROOT / record["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == record["sha256"]
    text = path.read_text(encoding="utf-8")
    for term in (
        "demo_token_hash", "save_to_alias_cache", "alias_scope", "OVERDUE_NOTICE",
    ):
        assert term in text

    protected_text = "\n".join(
        (ROOT / item["path"]).read_text(encoding="utf-8")
        for item in manifest["protected_files_at_gate0"]
    )
    for state in ("OFFLINE", "WARMING", "READY", "DEGRADED"):
        assert state in protected_text


def test_v21_critical_fields_are_reflected_in_machine_contracts():
    spec = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    schemas = spec["components"]["schemas"]
    line_input = schemas["WorkingLineInput"]["properties"]
    assert {"save_to_alias_cache", "alias_scope"}.issubset(line_input)
    assert schemas["CreditFlag"]["enum"] == ["NONE", "OVERDUE_NOTICE"]
    sql = (ROOT / "migrations" / "0001_baseline.sql").read_text(encoding="utf-8")
    for token in ("demo_token_hash", "credit_flag IN ('NONE','OVERDUE_NOTICE')", "actor_role"):
        assert token in sql
