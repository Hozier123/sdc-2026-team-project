"""Offline mutation tests against an archived real synthetic T2 direct evidence fixture."""

import json
import stat
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from tools.audit_b04_evidence import Audit, canonical_case, checksum, main

FIXTURE = Path(__file__).parent / "fixtures/b04-audit-direct.zip"


def payload():
    with zipfile.ZipFile(FIXTURE) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def get(files, path):
    return json.loads(files[path])


def put(files, path, value):
    files[path] = json.dumps(value, ensure_ascii=False, indent=2).encode()


def edit(files, path, change):
    value = get(files, path)
    change(value)
    put(files, path, value)


def archive(tmp_path, files, *, rehash=True):
    files = dict(files)
    if rehash:
        put(
            files,
            "MANIFEST.json",
            {
                "files": [
                    {"path": name, "bytes": len(raw), "sha256": checksum(raw)}
                    for name, raw in sorted(files.items())
                    if name != "MANIFEST.json"
                ]
            },
        )
    target = tmp_path / (uuid4().hex + ".zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output:
        for name, raw in files.items():
            output.writestr(name, raw)
    return target


def inspect(tmp_path, files, *, rehash=True, **options):
    target = archive(tmp_path, files, rehash=rehash)
    return Audit(**options).run(target)


def codes(report):
    return {item["code"] for item in report["findings"]}


def request(files, step):
    return next(
        name
        for name in files
        if name.startswith("direct/request-") and name.endswith(f"-{step}.json")
    )


def test_real_fixture_passes_with_pinned_reference_and_inputs_are_unchanged():
    original = FIXTURE.read_bytes()
    report = Audit().run(FIXTURE, FIXTURE, checksum(original))
    assert report["status"] == "PASS", report["findings"]
    assert report["real_cases"] == 1 and report["mock_cases"] == 0
    assert report["finding_counts"].get("ERROR", 0) == 0
    assert report["api_database_gpu_calls"] == 0
    assert FIXTURE.read_bytes() == original


def test_manifest_checksum_corruption_is_reported(tmp_path):
    files = payload()
    edit(files, "MANIFEST.json", lambda data: data["files"][0].update(sha256="0" * 64))
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "FAIL" and "HASH_MISMATCH" in codes(report)


def test_input_manifest_copy_is_verified_against_pinned_reference(tmp_path):
    files = payload()
    files["input/MANIFEST.json"] = files["MANIFEST.json"]
    target = archive(tmp_path, files)
    report = Audit().run(target, FIXTURE, checksum(FIXTURE.read_bytes()))
    assert report["status"] == "PASS", report["findings"]
    assert len(report["reference_manifest_copies"]) == 1
    assert report["reference_manifest_copies"][0]["reference_path"] == "MANIFEST.json"


@pytest.mark.parametrize("pin", [None, "0" * 64])
def test_untrusted_reference_cannot_reclassify_input_manifest(tmp_path, pin):
    files = payload()
    files["input/MANIFEST.json"] = files["MANIFEST.json"]
    report = Audit().run(archive(tmp_path, files), FIXTURE, pin)
    assert not report["reference_manifest_copies"]
    assert "MANIFEST_FILE_MISSING" in codes(report)
    assert report["status"] != "PASS"


def test_changed_input_manifest_cannot_be_reclassified(tmp_path):
    files = payload()
    files["input/MANIFEST.json"] = files["MANIFEST.json"]
    edit(files, "input/MANIFEST.json", lambda data: data.update(changed=True))
    report = Audit().run(archive(tmp_path, files), FIXTURE, checksum(FIXTURE.read_bytes()))
    assert not report["reference_manifest_copies"]
    assert "MANIFEST_FILE_MISSING" in codes(report)


def test_reference_manifest_never_replaces_missing_returned_evidence(tmp_path):
    files = payload()
    files["input/MANIFEST.json"] = files["MANIFEST.json"]
    del files["direct/response-002-parse.txt"]
    report = Audit().run(archive(tmp_path, files), FIXTURE, checksum(FIXTURE.read_bytes()))
    assert report["status"] == "INCOMPLETE"
    assert "RAW_RESPONSE_MISSING" in codes(report)


def test_reference_manifest_does_not_cover_returned_files(tmp_path):
    files = payload()
    files["input/MANIFEST.json"] = files.pop("MANIFEST.json")
    target = archive(tmp_path, files, rehash=False)
    report = Audit().run(target, FIXTURE, checksum(FIXTURE.read_bytes()))
    assert report["status"] == "INCOMPLETE"
    assert "UNLISTED_EVIDENCE" in codes(report)


@pytest.mark.parametrize(
    "name",
    [
        "direct/response-002-parse.txt",
        "direct/checkpoint.json",
        "direct/database-verification.json",
    ],
)
def test_missing_required_file_is_incomplete(tmp_path, name):
    files = payload()
    del files[name]
    report = inspect(tmp_path, files)
    assert report["status"] == "INCOMPLETE", report["findings"]


def test_missing_manifest_cannot_pass(tmp_path):
    files = payload()
    del files["MANIFEST.json"]
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "INCOMPLETE" and "MANIFEST_MISSING" in codes(report)


def test_only_report_and_hashes_are_not_business_evidence(tmp_path):
    files = {"report.md": b"PASS", "SHA256.txt": (checksum(b"PASS") + "  report.md\n").encode()}
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "INCOMPLETE" and report["real_cases"] == 0


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("stock", "INVENTORY_DELTA"),
        ("reported_delta", "REPORTED_STOCK_DELTA"),
        ("duplicate_do", "DB_DO_COUNT"),
        ("duplicate_deduction", "DB_AUDIT_COUNT"),
        ("order_state", "DB_ORDER_STATE"),
        ("omitted_sku", "INVENTORY_COVERAGE"),
        ("reported_failed", "DB_REPORTED_STATUS"),
    ],
)
def test_db_truth_is_recomputed_even_when_manifest_and_checks_say_pass(tmp_path, mutation, code):
    files = payload()
    data = get(files, "direct/database-verification.json")
    if mutation == "stock":
        data["after"]["inventory"]["SKU_PENCUCI_1L"] = 22
    elif mutation == "reported_delta":
        data["stock_delta"] = {}
    elif mutation == "duplicate_do":
        data["after"]["delivery_orders"].append(data["after"]["delivery_orders"][0])
    elif mutation == "duplicate_deduction":
        data["after"]["audit_rows"].append(["INVENTORY_DEDUCT", "CLERK"])
    elif mutation == "order_state":
        data["after"]["order_state"][0] = "REJECTED"
    elif mutation == "omitted_sku":
        del data["inventory_before"]["SKU_MOP_UNIT"]
        del data["after"]["inventory"]["SKU_MOP_UNIT"]
    else:
        data["status"] = "FAIL"
    assert all(data["checks"].values())
    put(files, "direct/database-verification.json", data)
    report = inspect(tmp_path, files)
    assert report["status"] == "FAIL" and code in codes(report), report["findings"]
    assert "HASH_MISMATCH" not in codes(report)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("request_id", "REQUEST_ID_MISSING"),
        ("inline_body", "RAW_BODY_MISMATCH"),
        ("request_version", "REQUEST_VERSION"),
        ("request_target", "REQUEST_TARGET"),
        ("checkpoint", "CACHED_STEP_MISMATCH"),
        ("driver", "DRIVER_VERSION"),
        ("case_digest", "CASE_HASH_BINDING"),
        ("actual_mode", "AI_MODE_BINDING"),
    ],
)
def test_run_request_version_and_response_bindings(tmp_path, mutation, code):
    files = payload()
    if mutation == "request_id":
        edit(files, request(files, "parse"), lambda value: value.update(request_id=None))
    elif mutation == "inline_body":
        edit(
            files,
            request(files, "parse"),
            lambda value: value["response_body"].update(customer_id="WRONG"),
        )
    elif mutation == "request_version":
        edit(
            files,
            request(files, "approve"),
            lambda value: value["request_body"].update(expected_version=1),
        )
    elif mutation == "request_target":
        edit(
            files,
            request(files, "approve"),
            lambda value: value.update(path="/orders/OTHER/approve"),
        )
    elif mutation == "checkpoint":
        edit(
            files,
            "direct/checkpoint.json",
            lambda value: value["steps"]["save"].update(request_id="wrong-id"),
        )
    elif mutation in {"driver", "case_digest"}:
        key = "driver_sha256" if mutation == "driver" else "case_sha256"
        for name in ("summary.json", "checkpoint.json"):
            edit(files, "direct/" + name, lambda value: value["binding"].update({key: "0" * 64}))
    else:
        for name in ("summary.json", "checkpoint.json"):
            edit(files, "direct/" + name, lambda value: value.update(actual_ai_mode="LLM"))
    report = inspect(tmp_path, files)
    assert report["status"] == "FAIL" and code in codes(report), report["findings"]


def test_raw_response_byte_corruption_is_not_hidden_by_rehashed_manifest(tmp_path):
    files = payload()
    files["direct/response-002-parse.txt"] += b" "
    report = inspect(tmp_path, files)
    assert report["status"] == "FAIL" and "RAW_RESPONSE_HASH" in codes(report)


def test_reference_checks_fixed_expectation_even_after_rebinding_case_hash(tmp_path):
    files = payload()
    case = get(files, "direct/case.json")
    case["expected"]["lines"][0]["applied_unit_price"] = "0.01"
    put(files, "direct/case.json", case)
    for name in ("summary.json", "checkpoint.json"):
        edit(
            files,
            "direct/" + name,
            lambda value: value["binding"].update(case_sha256=canonical_case(case)),
        )
    target = archive(tmp_path, files)
    report = Audit().run(target, FIXTURE, checksum(FIXTURE.read_bytes()))
    assert report["status"] == "FAIL" and "REFERENCE_CASE_MISMATCH" in codes(report)


def test_reference_archive_pin_is_checked(tmp_path):
    target = archive(tmp_path, payload())
    report = Audit().run(target, FIXTURE, "0" * 64)
    assert report["status"] == "FAIL" and "REFERENCE_ARCHIVE_HASH" in codes(report)


def test_one_case_cannot_claim_t2_four_route_coverage():
    report = Audit(require_t2_four=True).run(FIXTURE)
    assert report["status"] == "INCOMPLETE" and "T2_ROUTE_COVERAGE" in codes(report)


def test_protected_side_boolean_is_not_promoted_to_raw_snapshot_proof():
    report = Audit().run(FIXTURE)
    assert report["status"] == "PASS"
    assert "PROTECTED_RAW_AFTER_NOT_SUPPLIED" in codes(report)
    assert report["needs_manual_review"] is True


def test_mock_is_separate_and_does_not_count_as_real(tmp_path):
    files = payload()
    for name in ("summary.json", "checkpoint.json"):
        edit(
            files,
            "direct/" + name,
            lambda value: (
                value.update(status="SIMULATED_PASS"),
                value["binding"].update(mock=True),
            ),
        )
    report = inspect(tmp_path, files, require_t2_four=True)
    assert report["real_cases"] == 0 and report["mock_cases"] == 1
    assert report["status"] == "INCOMPLETE" and "MOCK_ONLY" in codes(report)


def test_expected_negative_requires_explicit_opt_in(tmp_path):
    files = payload()
    case = get(files, "direct/case.json")
    case["case_id"] += "-negative"
    case["expected"]["lines"][0]["sku_id"] = "SKU_WRONG_EXPECTATION"
    put(files, "direct/case.json", case)
    for path in list(files):
        if path.startswith("direct/request-") and int(Path(path).name.split("-")[1]) > 3:
            del files[path]
        elif path.startswith("direct/response-") and int(Path(path).name.split("-")[1]) > 3:
            del files[path]
    del files["direct/database-verification.json"]
    for name in ("summary.json", "checkpoint.json"):
        value = get(files, "direct/" + name)
        value.update(
            case_id=case["case_id"],
            run_id="direct-negative",
            status="FAIL",
            reason="business lines differ from case.expected (SKU/qty/unit/price/order)",
        )
        value["binding"]["case_sha256"] = canonical_case(case)
        value["identities"].pop("WAREHOUSE", None)
        value.pop("do_number", None)
        if "steps" in value:
            value["steps"] = {
                key: item
                for key, item in value["steps"].items()
                if key in {"identity_clerk", "parse", "save"}
            }
        put(files, "direct/" + name, value)
    for name in list(files):
        if name.startswith("direct/request-"):
            edit(
                files,
                name,
                lambda value: value.update(case_id=case["case_id"], run_id="direct-negative"),
            )
    target = archive(tmp_path, files)
    assert Audit().run(target)["status"] != "PASS"
    report = Audit(negative_runs=["direct-negative"]).run(target)
    assert report["status"] == "PASS" and report["negative_cases"] == 1, report["findings"]
    assert "NEGATIVE_DB_NOT_PROVIDED" in codes(report)


@pytest.mark.parametrize(
    "member", ["../escape.txt", "/absolute.txt", "C:/outside.txt", "a/../../escape"]
)
def test_unsafe_zip_paths_are_rejected_without_extraction(tmp_path, member):
    target = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(target, "w") as zipped:
        zipped.writestr(member, "untrusted")
    report = Audit().run(target)
    assert report["status"] == "FAIL" and "UNREADABLE_OR_UNSAFE_SOURCE" in codes(report)
    assert not (tmp_path / "escape.txt").exists()


def test_zip_symlink_is_rejected(tmp_path):
    target = tmp_path / "link.zip"
    with zipfile.ZipFile(target, "w") as zipped:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zipped.writestr(link, "../outside")
    assert Audit().run(target)["status"] == "FAIL"


def test_case_colliding_zip_names_are_rejected(tmp_path):
    target = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(target, "w") as zipped:
        zipped.writestr("CASE.json", "{}")
        zipped.writestr("case.json", "{}")
    assert Audit().run(target)["status"] == "FAIL"


def test_member_size_limits_are_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.audit_b04_evidence.MAX_FILE", 64)
    target = tmp_path / "large.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("large.txt", "x" * 1000)
    assert Audit().run(target)["status"] == "FAIL"


def test_malformed_manifest_entry_does_not_crash(tmp_path):
    files = payload()
    put(files, "MANIFEST.json", {"files": [{"path": ["not", "a", "string"], "sha256": "0" * 64}]})
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "FAIL" and "MANIFEST_ENTRY_INVALID" in codes(report)


def test_duplicate_json_keys_are_rejected(tmp_path):
    files = payload()
    files["direct/case.json"] = b'{"case_id":"one","case_id":"two"}'
    assert "INVALID_JSON" in codes(inspect(tmp_path, files))


def test_markdown_sha256_manifest_is_supported(tmp_path):
    files = payload()
    del files["MANIFEST.json"]
    rows = ["| 文件 | 字节 | SHA-256 |", "|---|---:|---|"]
    rows += [
        f"| `{name}` | {len(raw)} | `{checksum(raw).upper()}` |" for name, raw in files.items()
    ]
    files["SHA256.txt"] = ("\n".join(rows) + "\n").encode()
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "PASS", report["findings"]


def test_wrapped_root_folder_is_supported(tmp_path):
    files = {"zhou-evidence/" + name: raw for name, raw in payload().items()}
    report = inspect(tmp_path, files, rehash=False)
    assert report["status"] == "PASS", report["findings"]


def test_directory_input_is_read_only(tmp_path):
    folder = tmp_path / "evidence"
    for name, raw in payload().items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    before = {
        str(path.relative_to(folder)): path.read_bytes()
        for path in folder.rglob("*")
        if path.is_file()
    }
    assert Audit().run(folder)["status"] == "PASS"
    after = {
        str(path.relative_to(folder)): path.read_bytes()
        for path in folder.rglob("*")
        if path.is_file()
    }
    assert after == before
    with pytest.raises(SystemExit) as error:
        main([str(folder), "--out", str(folder / "audit.json")])
    assert error.value.code == 2 and not (folder / "audit.json").exists()


def test_cli_writes_reports_outside_source_and_refuses_overwrite(tmp_path):
    out = tmp_path / "report.json"
    assert main([str(FIXTURE), "--out", str(out)]) == 0
    assert json.loads(out.read_text("utf-8"))["status"] == "PASS"
    assert out.with_suffix(".md").is_file()
    original = out.read_bytes()
    with pytest.raises(SystemExit):
        main([str(FIXTURE), "--out", str(out)])
    assert out.read_bytes() == original
