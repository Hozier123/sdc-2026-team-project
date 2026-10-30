"""Offline B04 ZIP/directory evidence audit. Never extracts ZIPs or calls APIs/DB/GPU."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import zipfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SIGNED_DRIVER = "16c08c081d107582a48cd193bfbd554a4719df1ff8a8d01c32bcb41c88b9ffd5"
MAX_FILES = 5000
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
ROLES = {"CLERK", "OWNER", "WAREHOUSE"}
ROUTES = {"direct", "owner_approve", "owner_reject", "stock_blocked"}


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_case(case: dict) -> str:
    return checksum(json.dumps(case, sort_keys=True).encode())


def load_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("non-finite JSON number")

    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)


def safe_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("path must be a string")
    value = value.replace("\\", "/")
    parts = PurePosixPath(value).parts
    if not value or value.startswith("/") or not parts:
        raise ValueError("absolute/empty path")
    if any(part in {".", ".."} or ":" in part or re.search(r"[\x00-\x1f]", part) for part in parts):
        raise ValueError("unsafe path component")
    return "/".join(parts)


def child(folder: str, name: str) -> str:
    return safe_name(f"{folder}/{name}" if folder else name)


def money(value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean amount")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("invalid amount")
    return amount


def quantity(value) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("invalid quantity")
    return value


class Audit:
    def __init__(self, *, expected_driver=SIGNED_DRIVER, negative_runs=(), require_t2_four=False):
        self.expected_driver = expected_driver.lower()
        self.negative_runs = set(negative_runs)
        self.require_t2_four = require_t2_four
        self.files: dict[str, bytes] = {}
        self.reference: dict[str, bytes] = {}
        self.reference_pinned = False
        self.reference_manifest_copies = []
        self.issues: list[dict] = []
        self.cases: list[dict] = []
        self.checks = 0
        self.covered = set()
        self.json_cache = {}
        self.request_ids = set()

    def issue(self, severity, code, path, message):
        self.issues.append({"severity": severity, "code": code, "path": path, "message": message})

    def check(self, condition, code, path, message, severity="ERROR"):
        self.checks += 1
        if not condition:
            self.issue(severity, code, path, message)
        return bool(condition)

    def read_source(self, path: Path) -> tuple[dict[str, bytes], str | None]:
        files = {}
        folded = set()
        total = 0

        def add(name, data):
            nonlocal total
            key = safe_name(name)
            if key.casefold() in folded:
                raise ValueError("duplicate/case-colliding member")
            if len(files) >= MAX_FILES or len(data) > MAX_FILE or total + len(data) > MAX_TOTAL:
                raise ValueError("evidence size limit exceeded")
            folded.add(key.casefold())
            files[key] = data
            total += len(data)

        try:
            if path.is_dir():
                for item in sorted(path.rglob("*")):
                    if item.is_symlink() or not item.resolve().is_relative_to(path.resolve()):
                        raise ValueError("symlinks are not evidence files")
                    if item.is_file():
                        if item.stat().st_size > MAX_FILE:
                            raise ValueError("member too large")
                        add(item.relative_to(path).as_posix(), item.read_bytes())
                fingerprint = checksum(
                    json.dumps(
                        {k: checksum(v) for k, v in sorted(files.items())}, sort_keys=True
                    ).encode()
                )
            else:
                if path.stat().st_size > MAX_TOTAL:
                    raise ValueError("archive too large")
                raw = path.read_bytes()
                fingerprint = checksum(raw)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    entries = archive.infolist()
                    if len(entries) > MAX_FILES or sum(x.file_size for x in entries) > MAX_TOTAL:
                        raise ValueError("archive size limit exceeded")
                    for entry in entries:
                        safe_name(entry.filename.rstrip("/"))
                        if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                            raise ValueError("symlink/encrypted archive member")
                        if entry.is_dir():
                            continue
                        if entry.file_size > MAX_FILE:
                            raise ValueError("member too large")
                        with archive.open(entry) as stream:
                            data = stream.read(MAX_FILE + 1)
                        add(entry.filename, data)
            return files, fingerprint
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
            self.issue(
                "ERROR",
                "UNREADABLE_OR_UNSAFE_SOURCE",
                str(path),
                "Source is unreadable, corrupt, oversized, encrypted, linked, "
                "or contains unsafe/duplicate paths.",
            )
            return {}, None

    def json(self, path, *, required=True):
        if path not in self.files:
            if required:
                self.issue(
                    "MISSING", "FILE_MISSING", path, "Required evidence file was not supplied."
                )
            return None
        if path not in self.json_cache:
            try:
                self.json_cache[path] = load_json(self.files[path])
            except (ValueError, UnicodeError):
                self.issue(
                    "ERROR", "INVALID_JSON", path, "JSON is invalid, duplicated-key, or non-finite."
                )
                self.json_cache[path] = None
        return self.json_cache[path]

    def resolve(self, manifest_path, relative):
        name = safe_name(relative)
        folder = str(PurePosixPath(manifest_path).parent)
        folder = "" if folder == "." else folder
        return child(folder, name)

    def manifests(self):
        found = 0
        for path, raw in sorted(self.files.items()):
            name = PurePosixPath(path).name.lower()
            entries = []
            if name in {"manifest.json", "handoff-manifest.json", "source-manifest.json"}:
                data = self.json(path)
                candidates = data.get("files", []) if isinstance(data, dict) else data
                if isinstance(candidates, list):
                    entries = [
                        item
                        for item in candidates
                        if isinstance(item, dict) and "path" in item and "sha256" in item
                    ]
            elif name in {"sha256.txt", "sha256.md", "sha256sums.txt"}:
                try:
                    for line in raw.decode("utf-8-sig").splitlines():
                        cols = [x.strip().strip("`") for x in line.split("|")]
                        if (
                            len(cols) == 5
                            and cols[2].isdigit()
                            and re.fullmatch(r"[a-fA-F0-9]{64}", cols[3])
                        ):
                            entries.append(
                                {"path": cols[1], "bytes": int(cols[2]), "sha256": cols[3]}
                            )
                        else:
                            match = re.fullmatch(r"([A-Fa-f0-9]{64})\s+\*?(.+)", line.strip())
                            if match:
                                entries.append({"path": match[2], "sha256": match[1]})
                except UnicodeError:
                    self.issue("ERROR", "MANIFEST_ENCODING", path, "Cannot decode SHA256 manifest.")
            if not entries:
                continue
            found += 1
            # Reviewers may include the original input manifest without shipping
            # the original source snapshot again. Recognize that provenance only
            # for byte-identical manifests in input/ and an externally pinned ZIP.
            reference_path = None
            if (
                self.reference_pinned
                and PurePosixPath(path).parent.name == "input"
                and name in {"manifest.json", "handoff-manifest.json", "source-manifest.json"}
            ):
                reference_path = next(
                    (
                        candidate
                        for candidate, original in self.reference.items()
                        if PurePosixPath(candidate).name.lower() == name and original == raw
                    ),
                    None,
                )
            manifest_files = self.reference if reference_path else self.files
            if reference_path:
                self.reference_manifest_copies.append(
                    {
                        "path": path,
                        "reference_path": reference_path,
                        "sha256": checksum(raw),
                        "entries": len(entries),
                    }
                )
            seen = set()
            for item in entries:
                try:
                    target = self.resolve(reference_path or path, item["path"])
                    expected = str(item["sha256"]).lower()
                    if target in seen or not re.fullmatch(r"[a-f0-9]{64}", expected):
                        raise ValueError("invalid manifest entry")
                    seen.add(target)
                    if not reference_path:
                        self.covered.add(target)
                    if target not in manifest_files:
                        self.issue(
                            "MISSING",
                            "MANIFEST_FILE_MISSING",
                            target,
                            "A listed file was not supplied.",
                        )
                        continue
                    self.check(
                        checksum(manifest_files[target]) == expected,
                        "HASH_MISMATCH",
                        target,
                        "Stored bytes do not match the manifest SHA256.",
                    )
                    size = item.get("bytes", item.get("size"))
                    if size is not None:
                        self.check(
                            type(size) is int and len(manifest_files[target]) == size,
                            "SIZE_MISMATCH",
                            target,
                            "Stored bytes do not match the manifest size.",
                        )
                except (ValueError, TypeError, KeyError):
                    self.issue(
                        "ERROR",
                        "MANIFEST_ENTRY_INVALID",
                        path,
                        "Manifest contains an unsafe, duplicated, or invalid entry.",
                    )
        if not found:
            self.issue(
                "MISSING",
                "MANIFEST_MISSING",
                "",
                "No supported JSON/SHA256 file manifest was supplied.",
            )
        self.manifest_count = found

    def request_records(self, folder, case, summary):
        records = {}
        numbers = []
        for path in sorted(self.files):
            if str(PurePosixPath(path).parent) != folder:
                continue
            match = re.fullmatch(r"request-(\d+)-(.+)\.json", PurePosixPath(path).name)
            if not match:
                continue
            record = self.json(path)
            if not isinstance(record, dict):
                continue
            number, step = match.groups()
            numbers.append(int(number))
            self.check(
                record.get("case_id") == case["case_id"]
                and record.get("run_id") == summary["run_id"],
                "REQUEST_RUN_BINDING",
                path,
                "Request case_id/run_id differs from its case summary.",
            )
            self.check(
                record.get("step") == step,
                "REQUEST_STEP_BINDING",
                path,
                "Request filename and step differ.",
            )
            self.check(
                bool(record.get("sent_request_id")),
                "SENT_REQUEST_ID_MISSING",
                path,
                "Client request ID was not recorded.",
            )
            self.check(
                type(record.get("elapsed_ms")) in {int, float} and record["elapsed_ms"] >= 0,
                "ELAPSED_INVALID",
                path,
                "Request elapsed_ms is absent or invalid.",
            )
            received = record.get("request_id")
            if record.get("http_status") is not None:
                self.check(
                    bool(received),
                    "REQUEST_ID_MISSING",
                    path,
                    "Server request ID was not recorded.",
                )
                if received:
                    self.check(
                        received not in self.request_ids,
                        "REQUEST_ID_REUSED",
                        path,
                        "Server request ID is reused across recorded attempts.",
                    )
                    self.request_ids.add(received)
                headers = {k.lower(): v for k, v in record.get("response_headers", {}).items()}
                if headers.get("x-request-id"):
                    self.check(
                        headers["x-request-id"] == received,
                        "REQUEST_ID_HEADER_MISMATCH",
                        path,
                        "Returned header and recorded request ID differ.",
                    )
                raw_path = child(folder, f"response-{number}-{step}.txt")
                if raw_path not in self.files:
                    self.issue(
                        "MISSING",
                        "RAW_RESPONSE_MISSING",
                        raw_path,
                        "Raw response text was not supplied.",
                    )
                else:
                    raw = self.files[raw_path]
                    if record.get("raw_response_redacted"):
                        self.issue(
                            "REVIEW",
                            "ORIGINAL_RAW_HASH_REDACTED",
                            raw_path,
                            "The redacted file can be manifest-checked; "
                            "the original unredacted byte hash cannot be recomputed.",
                        )
                    else:
                        self.check(
                            checksum(raw) == record.get("raw_response_sha256"),
                            "RAW_RESPONSE_HASH",
                            raw_path,
                            "Raw response bytes differ from the recorded SHA256.",
                        )
                    try:
                        parsed = load_json(raw)
                    except (ValueError, UnicodeError):
                        parsed = None
                    self.check(
                        parsed == record.get("response_body"),
                        "RAW_BODY_MISMATCH",
                        path,
                        "Parsed raw response differs from the inline response body.",
                    )
            else:
                self.issue(
                    "MISSING",
                    "UNFINISHED_REQUEST",
                    path,
                    "No server response is recorded; "
                    "the in-flight/transport-failed request requires reconciliation.",
                )
            records.setdefault(step, []).append((path, record))
        if numbers:
            self.check(
                sorted(numbers) == list(range(1, max(numbers) + 1)),
                "REQUEST_SEQUENCE_GAP",
                folder,
                "Request sequence has missing or duplicate numbers.",
            )
        else:
            self.issue(
                "MISSING", "REQUEST_RECORDS_MISSING", folder, "No request records were supplied."
            )
        return {step: attempts[-1] for step, attempts in records.items()}

    def compare_lines(self, lines, expected, path, *, working=False):
        actual = []
        for line in lines:
            qty = quantity(line["effective_qty"] if working else line["quantity"])
            price = money(line["effective_unit_price"] if working else line["applied_unit_price"])
            actual.append((line["sku_id"], qty, line["uom"] if working else line["unit"], price))
            self.check(
                money(line["subtotal_rm"]) == qty * price,
                "LINE_SUBTOTAL",
                path,
                "A line subtotal is inconsistent with quantity times unit price.",
            )
        wanted = [
            (x["sku_id"], quantity(x["quantity"]), x["unit"], money(x["applied_unit_price"]))
            for x in expected
        ]
        self.check(
            actual == wanted,
            "BUSINESS_LINES",
            path,
            "SKU/quantity/unit/unit price/order differs from case.expected.",
        )

    def reference_case(self, case, path, negative):
        candidates = []
        for name, raw in self.reference.items():
            if "/b04-cases/" not in name or not name.endswith(".json"):
                continue
            item = load_json(raw)
            if item.get("tenant_id") == case.get("tenant_id") and item.get("route") == case.get(
                "route"
            ):
                candidates.append(item)
        if candidates:
            fields = ["tenant_id", "route", "parse", "save", "allowed_ai_modes", "decision_note"]
            if not negative:
                fields.append("expected")
            self.check(
                any(all(case.get(key) == item.get(key) for key in fields) for item in candidates),
                "REFERENCE_CASE_MISMATCH",
                path,
                "Case input/decisions/expectation/modes differ from the reference snapshot.",
            )
        elif self.reference:
            self.issue(
                "REVIEW",
                "REFERENCE_CASE_NOT_FOUND",
                path,
                "No matching tenant/route case exists in the supplied reference.",
            )

    def case(self, folder):
        case_path, summary_path = child(folder, "case.json"), child(folder, "summary.json")
        case, summary = self.json(case_path), self.json(summary_path)
        checkpoint = self.json(child(folder, "checkpoint.json"))
        if not all(isinstance(item, dict) for item in (case, summary, checkpoint)):
            return
        info = {
            "path": folder,
            "case_id": case.get("case_id"),
            "run_id": summary.get("run_id"),
            "tenant_id": case.get("tenant_id"),
            "route": case.get("route"),
            "reported_result": summary.get("status"),
            "actual_ai_mode": summary.get("actual_ai_mode"),
        }
        self.cases.append(info)
        start_issues = len(self.issues)
        try:
            route = case["route"]
            if route not in ROUTES:
                self.issue(
                    "MISSING",
                    "UNSUPPORTED_CASE_FORMAT",
                    case_path,
                    "This auditor supports the four B04 driver routes; "
                    "unbound formal workflow plans are unsupported.",
                )
                return
            negative = (
                summary["run_id"] in self.negative_runs or case["case_id"] in self.negative_runs
            )
            mock = summary["binding"].get("mock") is True
            self.check(
                type(summary["binding"].get("mock")) is bool,
                "MOCK_BINDING_MISSING",
                folder,
                "Real/mock binding must be explicit.",
            )
            self.check(
                bool(case.get("allowed_ai_modes"))
                and set(case["allowed_ai_modes"]) <= {"LLM", "FALLBACK", "ALIAS_ONLY", "MIXED"},
                "PLANNED_AI_MODES",
                folder,
                "Planned AI modes are invalid.",
            )
            info.update(mock=mock, expected_negative=negative)
            self.check(
                summary.get("case_id") == case["case_id"],
                "CASE_ID_BINDING",
                folder,
                "Summary case_id differs from case.json.",
            )
            self.check(
                summary["binding"].get("case_sha256") == canonical_case(case),
                "CASE_HASH_BINDING",
                folder,
                "Canonical case digest differs from the checkpoint binding.",
            )
            self.check(
                summary["binding"].get("driver_sha256", "").lower() == self.expected_driver,
                "DRIVER_VERSION",
                folder,
                "Driver SHA256 differs from the explicitly expected signed version.",
            )
            for key in (
                "run_id",
                "case_id",
                "binding",
                "status",
                "identities",
                "actual_ai_mode",
                "draft_id",
                "draft_version",
                "do_number",
            ):
                self.check(
                    checkpoint.get(key) == summary.get(key),
                    "CHECKPOINT_SUMMARY_MISMATCH",
                    folder,
                    f"Checkpoint and summary disagree on {key}.",
                )
            self.check(
                not checkpoint.get("pending_request"),
                "PENDING_WRITE",
                folder,
                "Checkpoint still contains an in-flight request.",
            )
            self.reference_case(case, case_path, negative)
            records = self.request_records(folder, case, summary)

            def body(step):
                return records[step][1]["response_body"]

            for name, cached in checkpoint.get("steps", {}).items():
                path = child(folder, cached["file"])
                actual = self.json(path)
                if isinstance(actual, dict):
                    self.check(
                        actual.get("step") == name
                        and actual.get("request_id") == cached.get("request_id")
                        and actual.get("response_body") == cached.get("body")
                        and actual.get("http_status") == cached.get("http_status"),
                        "CACHED_STEP_MISMATCH",
                        path,
                        "Checkpoint cached response does not match the recorded request.",
                    )
            for name, (path, record) in records.items():
                if name.startswith("identity_") and record.get("http_status") == 200:
                    user = record["response_body"]
                    role = record["role"]
                    self.check(
                        role in ROLES
                        and user.get("role") == role
                        and user.get("tenant", {}).get("id") == case["tenant_id"],
                        "IDENTITY_BINDING",
                        path,
                        "Identity role/tenant is inconsistent with the role and case.",
                    )
                    self.check(
                        summary.get("identities", {}).get(role) == user.get("user_id"),
                        "IDENTITY_USER",
                        path,
                        "Summary user_id differs from /me evidence.",
                    )
            if negative:
                self.check(
                    summary.get("status") == "FAIL" and bool(summary.get("reason")),
                    "NEGATIVE_OUTCOME",
                    folder,
                    "Explicit negative run did not record an explained FAIL.",
                )
                if "approve" in records or "owner_decide" in records:
                    self.issue(
                        "REVIEW",
                        "NEGATIVE_MUTATIONS_REVIEW",
                        folder,
                        "The expected-failure run includes approval/decision attempts; "
                        "inspect side effects.",
                    )
                if child(folder, "database-verification.json") not in self.files:
                    self.issue(
                        "REVIEW",
                        "NEGATIVE_DB_NOT_PROVIDED",
                        folder,
                        "Negative FAIL is recorded; stock/DO side effects "
                        "cannot be recomputed without DB snapshots.",
                    )
                info["verification_scope"] = "EXPECTED_FAIL_RECORD_ONLY"
                return
            expected_result = "SIMULATED_PASS" if mock else "API_PASS"
            result = summary.get("status")
            self.check(
                result == expected_result,
                "CASE_RESULT",
                folder,
                "Case did not finish with the expected real/mock pass status.",
                severity="MISSING"
                if result in {"CHECKPOINT", "BLOCKED", "INDETERMINATE"}
                else "ERROR",
            )
            success = route in {"direct", "owner_approve"}
            required = {"identity_clerk", "parse", "save", "approve", "final_draft", "activity_0"}
            if route.startswith("owner_"):
                required |= {"identity_owner", "owner_review", "owner_decide"}
            if success:
                required |= {"identity_warehouse", "delivery_order", "warehouse", "audit"}
            missing = required - records.keys()
            for name in sorted(missing):
                self.issue(
                    "MISSING",
                    "REQUIRED_STEP_MISSING",
                    folder,
                    f"Required step {name} was not supplied.",
                )
            if missing:
                return
            for name in required:
                status = (
                    400
                    if name == "approve" and route == "stock_blocked"
                    else 202
                    if name == "approve" and route.startswith("owner_")
                    else 200
                )
                self.check(
                    records[name][1].get("http_status") == status,
                    "HTTP_SEQUENCE",
                    records[name][0],
                    "HTTP status does not match the planned route and step.",
                )
            parsed, saved, final = body("parse"), body("save"), body("final_draft")
            expected = case["expected"]["lines"]
            self.check(
                summary.get("actual_ai_mode") == parsed.get("ai_mode")
                and parsed.get("ai_mode") in case["allowed_ai_modes"]
                and saved.get("ai_mode") == parsed.get("ai_mode")
                and final.get("ai_mode") == parsed.get("ai_mode"),
                "AI_MODE_BINDING",
                folder,
                "Actual/planned/historical AI modes are inconsistent.",
            )
            self.check(
                parsed.get("customer_id") == case["parse"]["customer_id"],
                "CUSTOMER_BINDING",
                folder,
                "Parsed customer differs from the frozen case input.",
            )
            draft_id = parsed["draft_id"]
            expected_requests = {
                "parse": ("POST", "/orders/parse-draft"),
                "save": ("PUT", f"/orders/drafts/{draft_id}/lines"),
                "approve": ("POST", f"/orders/{draft_id}/approve"),
                "final_draft": ("GET", f"/orders/drafts/{draft_id}"),
            }
            if success:
                number = summary.get("do_number")
                expected_requests.update(
                    {
                        "delivery_order": ("GET", f"/delivery-orders/{number}"),
                        "warehouse": ("GET", f"/warehouse/delivery-orders/{number}"),
                        "audit": ("GET", f"/orders/{number}/audit-detail"),
                    }
                )
            if route.startswith("owner_"):
                approval_id = summary.get("approval_id")
                expected_requests.update(
                    {
                        "owner_review": ("GET", f"/approvals/{approval_id}"),
                        "owner_decide": ("POST", f"/approvals/{approval_id}/decide"),
                    }
                )
            for name, (method, path) in expected_requests.items():
                record = records[name][1]
                self.check(
                    record.get("method") == method and record.get("path") == path,
                    "REQUEST_TARGET",
                    records[name][0],
                    "Request method/path/entity differs.",
                )
            self.check(
                records["parse"][1].get("request_body") == case["parse"],
                "PARSE_INPUT",
                folder,
                "Sent parse input differs from case.parse.",
            )
            self.check(
                draft_id
                == saved.get("draft_id")
                == final.get("draft_id")
                == summary.get("draft_id"),
                "DRAFT_BINDING",
                folder,
                "Draft IDs differ across responses.",
            )
            self.check(
                saved["version"] == parsed["version"] + 1
                and final["version"] == saved["version"] == summary["draft_version"],
                "VERSION_BINDING",
                folder,
                "Draft versions do not follow parse/save/final sequence.",
            )
            self.check(
                records["save"][1]["request_body"]["expected_version"] == parsed["version"]
                and records["approve"][1]["request_body"] == {"expected_version": saved["version"]},
                "REQUEST_VERSION",
                folder,
                "Save/approve payload uses the wrong version or extra approval lines.",
            )
            self.compare_lines(saved["lines"], expected, folder, working=True)
            state = (
                "DO_GENERATED"
                if success
                else "REJECTED"
                if route == "owner_reject"
                else saved["status"]
            )
            self.check(
                final.get("status") == state and final.get("do_number") == summary.get("do_number"),
                "FINAL_STATE",
                folder,
                "Final order state or DO reference differs from the route summary.",
            )
            if route == "stock_blocked":
                self.check(
                    "INSUFFICIENT_STOCK" in saved.get("blocking_issues", [])
                    and body("approve").get("error_code")
                    in {"INSUFFICIENT_STOCK", "DISAMBIGUATION_UNRESOLVED"},
                    "STOCK_BLOCK_REASON",
                    folder,
                    "Stock case failed for an unrelated reason.",
                )
            if route.startswith("owner_"):
                pending, detail = body("approve"), body("owner_review")
                self.check(
                    pending.get("approval_id")
                    == detail.get("approval_id")
                    == summary.get("approval_id")
                    and detail.get("draft_id") == draft_id
                    and detail.get("draft_version") == saved["version"]
                    and detail.get("status") == "PENDING",
                    "OWNER_SNAPSHOT",
                    folder,
                    "Owner review does not reference the submitted saved version.",
                )
                self.compare_lines(detail["snapshot"]["lines"], expected, folder, working=True)
                decision = records["owner_decide"][1]["request_body"]
                self.check(
                    decision.get("decision")
                    == ("REJECT" if route == "owner_reject" else "APPROVE"),
                    "OWNER_DECISION",
                    folder,
                    "Owner decision differs from the planned route.",
                )
                if route == "owner_reject":
                    rejected = body("owner_decide")
                    self.check(
                        rejected.get("status") == "REJECTED"
                        and rejected.get("draft_id") == draft_id
                        and rejected.get("decision_note") == case.get("decision_note")
                        and not rejected.get("do_number"),
                        "REJECTION_BINDING",
                        folder,
                        "Rejection reason/state/entity differs from the case.",
                    )
            if success:
                do = body("delivery_order")
                for label, document in [
                    ("approval", body("approve") if route == "direct" else body("owner_decide")),
                    ("delivery", do),
                    ("audit", body("audit")["final_snapshot"]),
                ]:
                    self.compare_lines(document["lines"], expected, folder)
                    self.check(
                        document.get("draft_id") == draft_id
                        and document.get("draft_version") == saved["version"]
                        and document.get("do_number") == summary.get("do_number"),
                        "DO_BINDING",
                        folder,
                        f"{label} DO references differ from the saved order.",
                    )
                    self.check(
                        money(document["final_total_rm"])
                        == sum(money(x["subtotal_rm"]) for x in document["lines"]),
                        "DO_TOTAL",
                        folder,
                        "DO total differs from the sum of line amounts.",
                    )
                    actor = "CLERK" if route == "direct" else "OWNER"
                    self.check(
                        document.get("approval_mode")
                        == ("DIRECT" if route == "direct" else "OWNER_APPROVED")
                        and document.get("approved_by") == summary["identities"][actor],
                        "APPROVER_BINDING",
                        folder,
                        "DO approval mode/actor differs from role evidence.",
                    )
                warehouse = body("warehouse")
                self.check(
                    set(warehouse) <= {"do_number", "customer_name", "items", "approved_at"}
                    and all(
                        set(item) <= {"sku_id", "display_name", "quantity", "unit", "picking_note"}
                        for item in warehouse["items"]
                    ),
                    "WAREHOUSE_FIELDS",
                    folder,
                    "Warehouse response exposes unapproved fields.",
                )
                self.check(
                    warehouse["do_number"] == do["do_number"]
                    and [(x["sku_id"], x["quantity"], x["unit"]) for x in warehouse["items"]]
                    == [(x["sku_id"], x["quantity"], x["unit"]) for x in do["lines"]],
                    "WAREHOUSE_LINES",
                    folder,
                    "Warehouse picking differs from the DO.",
                )
            activities = []
            pages = sorted(
                (name for name in records if name.startswith("activity_")),
                key=lambda x: int(x.split("_")[-1]),
            )
            for index, name in enumerate(pages):
                response = body(name)
                activities.extend(response["items"])
                self.check(
                    (response.get("next_cursor") is None) == (index == len(pages) - 1),
                    "ACTIVITY_PAGINATION",
                    folder,
                    "Activity pages are incomplete or continue after termination.",
                )
            events = Counter(item["event_type"] for item in activities)
            self.check(
                events["INVENTORY_DEDUCTED"] == int(success)
                and events["DO_CREATED"] == int(route == "direct")
                and events["OWNER_APPROVED"] == int(route == "owner_approve")
                and events["OWNER_REJECTED"] == int(route == "owner_reject"),
                "ACTIVITY_COUNTS",
                folder,
                "Activity event counts differ from the planned route.",
            )
            if mock:
                self.issue(
                    "REVIEW",
                    "MOCK_ONLY",
                    folder,
                    "Simulated evidence is not real HTTP/DB/LLM proof.",
                )
            else:
                self.database(
                    folder, case, summary, body("audit") if success else None, final["status"]
                )
            info["verification_scope"] = (
                "SIMULATED" if mock else "REAL_EVIDENCE_INTERNAL_CONSISTENCY"
            )
        except (KeyError, TypeError, ValueError, ArithmeticError, IndexError, AttributeError):
            self.issue(
                "ERROR",
                "CASE_SHAPE_INVALID",
                folder,
                "Required B04 case/response/DB fields have invalid shapes or values.",
            )
        finally:
            info["findings"] = len(self.issues) - start_issues

    def database(self, folder, case, summary, audit, final_status):
        path = child(folder, "database-verification.json")
        data = self.json(path)
        if not isinstance(data, dict):
            return
        self.check(
            data.get("status") == "PASS",
            "DB_REPORTED_STATUS",
            path,
            "Producer did not report its DB verification as PASS.",
        )
        before = data["inventory_before"]
        after = data.get("after", {})
        if not after and "inventory_after" in data:
            after = {
                "inventory": data["inventory_after"],
                "delivery_orders": data["delivery_orders"],
                "audit_rows": data["audit_rows"],
                "approvals": data.get("approval_requests", []),
                "order_state": data["final_order_state"],
            }
        stock = after["inventory"]
        self.check(
            set(before) == set(stock)
            and len(before) == {"T1": 40, "T2": 16}.get(case["tenant_id"], len(before)),
            "INVENTORY_COVERAGE",
            path,
            "Before/after SKU sets differ or canonical tenant inventory is incomplete.",
        )
        self.check(
            all(type(value) is int and value >= 0 for value in [*before.values(), *stock.values()]),
            "INVENTORY_VALUES",
            path,
            "Inventory contains invalid/negative values.",
        )
        delta = {sku: before[sku] - stock[sku] for sku in before if before[sku] != stock[sku]}
        success = case["route"] in {"direct", "owner_approve"}
        wanted = Counter()
        if success:
            for line in case["expected"]["lines"]:
                wanted[line["sku_id"]] += quantity(line["quantity"])
        self.check(
            delta == dict(wanted),
            "INVENTORY_DELTA",
            path,
            "Recomputed per-SKU stock change differs from the case business outcome.",
        )
        self.check(
            data.get("stock_delta") == delta,
            "REPORTED_STOCK_DELTA",
            path,
            "Reported stock_delta differs from the raw inventory snapshots.",
        )
        deliveries = after["delivery_orders"]
        self.check(
            len(deliveries) == int(success),
            "DB_DO_COUNT",
            path,
            "Database DO count is not exactly one for success or zero for rejection/block.",
        )
        if success and deliveries:
            number, total, mode = deliveries[0][:3]
            self.check(
                number == summary.get("do_number")
                and money(total)
                == sum(
                    quantity(x["quantity"]) * money(x["applied_unit_price"])
                    for x in case["expected"]["lines"]
                )
                and mode == ("DIRECT" if case["route"] == "direct" else "OWNER_APPROVED"),
                "DB_DO_BINDING",
                path,
                "Database DO number/total/approval mode differs from the case or HTTP evidence.",
            )
        counts = Counter(
            row["action"] if isinstance(row, dict) else row[0] for row in after["audit_rows"]
        )
        expected = {
            "SAVE_LINES": 1,
            "APPROVE": int(case["route"] == "direct"),
            "DECIDE_APPROVE": int(case["route"] == "owner_approve"),
            "DECIDE_REJECT": int(case["route"] == "owner_reject"),
            "INVENTORY_DEDUCT": int(success),
            "SUBMIT_APPROVAL": int(case["route"].startswith("owner_")),
        }
        for action, count in expected.items():
            self.check(
                counts[action] == count,
                "DB_AUDIT_COUNT",
                path,
                f"Recomputed {action} count differs from the route.",
            )
        if audit:
            self.check(
                Counter(item["event_type"] for item in audit["events"]) == counts,
                "API_DB_AUDIT_MISMATCH",
                path,
                "HTTP audit events differ from the database audit rows.",
            )
        state = after["order_state"]
        self.check(
            state[0] == final_status and state[1] == summary["draft_version"],
            "DB_ORDER_STATE",
            path,
            "Database order status/version differs from HTTP evidence.",
        )
        if case["route"].startswith("owner_"):
            approvals = after["approvals"]
            self.check(
                len(approvals) == 1
                and approvals[0][0] == summary.get("approval_id")
                and approvals[0][1]
                == ("REJECTED" if case["route"] == "owner_reject" else "APPROVED"),
                "DB_APPROVAL_STATE",
                path,
                "Database owner approval ID/terminal state differs.",
            )
        for name, passed in data.get("checks", {}).items():
            if passed is False:
                self.issue(
                    "ERROR",
                    "DECLARED_DB_CHECK_FAILED",
                    path,
                    f"Producer marked DB check {name} false.",
                )
        if data.get("checks", {}).get("t1_unchanged") is not None:
            if "protected_before" in data and "protected_after" in data:
                self.check(
                    data["protected_before"] == data["protected_after"],
                    "PROTECTED_TENANT_CHANGED",
                    path,
                    "Raw protected-tenant snapshots differ.",
                )
            else:
                self.issue(
                    "REVIEW",
                    "PROTECTED_RAW_AFTER_NOT_SUPPLIED",
                    path,
                    "Protected-tenant unchanged is a producer assertion; "
                    "paired raw snapshots were not supplied.",
                )
        self.db_snapshots[folder] = (before, stock)

    def batches(self):
        for path in sorted(self.files):
            if PurePosixPath(path).name != "batch-summary.json":
                continue
            data = self.json(path)
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                continue
            folder = str(PurePosixPath(path).parent)
            prior = {}
            for declared in data["results"]:
                run_path = child(folder, declared["run_id"])
                matches = [item for item in self.cases if item["path"] == run_path]
                if not matches:
                    self.issue(
                        "MISSING",
                        "BATCH_RUN_MISSING",
                        run_path,
                        "A declared batch run has no supplied case evidence.",
                    )
                    continue
                actual = matches[0]
                self.check(
                    declared.get("case_id") == actual["case_id"]
                    and declared.get("status") == actual["reported_result"]
                    and declared.get("actual_ai_mode") == actual["actual_ai_mode"],
                    "BATCH_CASE_BINDING",
                    path,
                    "Batch result disagrees with the individual case summary.",
                )
                if run_path in self.db_snapshots and data.get("database"):
                    before, after = self.db_snapshots[run_path]
                    tenant = actual["tenant_id"]
                    if tenant in prior:
                        self.check(
                            prior[tenant] == before,
                            "BATCH_INVENTORY_CHAIN",
                            run_path,
                            "Stock snapshots are discontinuous inside the same database batch.",
                        )
                    prior[tenant] = after
            for name, expected in data.get("source_hashes", {}).items():
                clean = safe_name(name)
                candidates = [
                    raw
                    for key, raw in self.files.items()
                    if key == clean or key.endswith("/" + clean)
                ]
                if not candidates and clean in self.reference:
                    candidates = [self.reference[clean]]
                if candidates:
                    self.check(
                        all(checksum(raw) == expected.lower() for raw in candidates),
                        "BATCH_SOURCE_HASH",
                        name,
                        "Supplied/reference source differs from the captured batch source hash.",
                    )
                else:
                    self.missing_sources.add(clean)
            extra_path = child(folder, "duplicate-and-tenant-checks.json")
            extra = self.json(extra_path, required=False)
            if extra is not None and data.get("additional_checks") is not None:
                self.check(
                    extra == data["additional_checks"],
                    "EXTRA_SUMMARY_MISMATCH",
                    path,
                    "Supplementary check file differs from the batch summary.",
                )
            extra = extra or data.get("additional_checks")
            if extra:
                requests = {item["name"]: item for item in extra.get("requests", [])}
                for name, status, code in [
                    ("repeat_approval", 409, "ALREADY_APPROVED"),
                    ("t1_cannot_read_t2_draft", 404, "RESOURCE_NOT_FOUND"),
                    ("t1_cannot_read_t2_warehouse", 404, "RESOURCE_NOT_FOUND"),
                ]:
                    item = requests.get(name)
                    self.check(
                        item is not None,
                        "EXTRA_REQUEST_MISSING",
                        path,
                        f"Supplementary request {name} is absent.",
                        severity="MISSING",
                    )
                    if item:
                        self.check(
                            item.get("status_code") == status
                            and item.get("body", {}).get("error_code") == code
                            and bool(item.get("request_id")),
                            "EXTRA_HTTP_RESULT",
                            path,
                            f"Supplementary {name} HTTP/code/request_id "
                            "differs from its declared purpose.",
                        )
                if "before_retry" in extra and "after_retry" in extra:
                    self.check(
                        extra["before_retry"] == extra["after_retry"],
                        "RETRY_CHANGED_DB",
                        path,
                        "Raw before/after retry database snapshots differ.",
                    )
                else:
                    self.issue(
                        "REVIEW",
                        "RETRY_DB_PAIR_NOT_SUPPLIED",
                        path,
                        "409 response is present; unchanged DB is only asserted "
                        "without paired retry snapshots.",
                    )
                for name, passed in extra.get("checks", {}).items():
                    if passed is False:
                        self.issue(
                            "ERROR",
                            "DECLARED_EXTRA_CHECK_FAILED",
                            path,
                            f"Producer marked supplementary check {name} false.",
                        )
        if self.missing_sources:
            self.issue(
                "REVIEW",
                "SOURCE_BYTES_NOT_SUPPLIED",
                "",
                "Captured source hashes have no supplied/reference bytes for "
                f"{len(self.missing_sources)} files.",
            )

    def run(self, source: Path, reference: Path | None = None, reference_sha256=None):
        self.db_snapshots = {}
        self.missing_sources = set()
        self.files, source_hash = self.read_source(source)
        reference_hash = None
        if reference:
            self.reference, reference_hash = self.read_source(reference)
            if reference_sha256:
                self.reference_pinned = self.check(
                    reference_hash == reference_sha256.lower(),
                    "REFERENCE_ARCHIVE_HASH",
                    str(reference),
                    "Reference archive differs from the externally pinned SHA256.",
                )
            else:
                self.issue(
                    "REVIEW",
                    "REFERENCE_NOT_PINNED",
                    str(reference),
                    "Reference was supplied without an externally pinned archive SHA256.",
                )
        else:
            self.issue(
                "REVIEW",
                "NO_EXTERNAL_REFERENCE",
                "",
                "Only internal consistency and the expected driver hash are checked; "
                "case truth/source authenticity is not independently established.",
            )
        self.manifests()
        folders = sorted(
            {
                str(PurePosixPath(path).parent)
                for path in self.files
                if PurePosixPath(path).name == "case.json"
            }
        )
        for folder in folders:
            self.case(folder)
        try:
            self.batches()
        except (ValueError, TypeError, KeyError, ArithmeticError, IndexError, AttributeError):
            self.issue(
                "ERROR",
                "BATCH_SHAPE_INVALID",
                "",
                "Batch/source/supplementary records have invalid shapes.",
            )
        if not self.cases:
            self.issue(
                "MISSING",
                "CASE_EVIDENCE_MISSING",
                "",
                "Reports and hash lists alone are not a complete B04 evidence package.",
            )
        real = [
            item
            for item in self.cases
            if not item.get("mock") and not item.get("expected_negative")
        ]
        if self.require_t2_four:
            self.check(
                {item["route"] for item in real if item["tenant_id"] == "T2"} >= ROUTES,
                "T2_ROUTE_COVERAGE",
                "",
                "The four required real T2 routes were not all supplied.",
                severity="MISSING",
            )
        tracked = [
            path
            for path in self.files
            if PurePosixPath(path).name
            in {
                "case.json",
                "checkpoint.json",
                "summary.json",
                "database-verification.json",
                "batch-summary.json",
            }
            or PurePosixPath(path).name.startswith(("request-", "response-"))
        ]
        if any(path not in self.covered for path in tracked):
            self.issue(
                "MISSING",
                "UNLISTED_EVIDENCE",
                "",
                "One or more core evidence files are not covered by a supplied manifest.",
            )
        errors = Counter(item["severity"] for item in self.issues)
        status = "FAIL" if errors["ERROR"] else "INCOMPLETE" if errors["MISSING"] else "PASS"
        return {
            "schema_version": "B04-EVIDENCE-AUDIT-v1",
            "status": status,
            "scope": "Offline artifact integrity and supported DEV evidence consistency; "
            "not formal scoring or independent signoff",
            "input": str(source.resolve()),
            "input_sha256": source_hash,
            "reference": str(reference.resolve()) if reference else None,
            "reference_sha256": reference_hash,
            "expected_driver_sha256": self.expected_driver,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "files_read": len(self.files),
            "manifests_checked": self.manifest_count,
            "reference_manifest_copies": self.reference_manifest_copies,
            "checks_performed": self.checks,
            "real_cases": len(real),
            "mock_cases": sum(item.get("mock") is True for item in self.cases),
            "negative_cases": sum(item.get("expected_negative") is True for item in self.cases),
            "finding_counts": dict(errors),
            "needs_manual_review": bool(errors["REVIEW"]),
            "cases": self.cases,
            "findings": self.issues,
            "limitations": [
                "Hash consistency does not prove the generator or actual server/database contact.",
                "Absent retry/protected-tenant snapshot pairs remain manual review.",
                "No formal TEST32/v5 scoring, concurrency, or independent acceptance is asserted.",
            ],
            "api_database_gpu_calls": 0,
            "input_modified": False,
        }


def markdown(report):
    lines = [
        f"# B04 证据包核验：{report['status']}",
        "",
        "仅为离线材料核验；不代替正式评分或独立签收。",
        "",
        f"文件 {report['files_read']}；清单 {report['manifests_checked']}；"
        f"检查 {report['checks_performed']}；真实例 {report['real_cases']}；"
        f"模拟例 {report['mock_cases']}；显式负例 {report['negative_cases']}。",
        "",
        f"待人工确认：{'是' if report['needs_manual_review'] else '否'}。",
        "",
        "| 级别 | 编号 | 文件 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["findings"]:
        values = [
            str(item[key]).replace("|", "\\|").replace("\n", " ")
            for key in ("severity", "code", "path", "message")
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines += [
        "",
        "输入未修改；API、数据库、GPU 调用数为 0。",
        "",
        "PASS 表示所覆盖的自动检查通过。REVIEW 项保留，不能把缺失的原始数据推断为已验证。",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-sha256")
    parser.add_argument("--expected-driver-sha256", default=SIGNED_DRIVER)
    parser.add_argument("--negative-run", action="append", default=[])
    parser.add_argument("--require-t2-four", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.expected_driver_sha256) or (
        args.reference_sha256
        and (not args.reference or not re.fullmatch(r"[a-fA-F0-9]{64}", args.reference_sha256))
    ):
        parser.error("SHA256 arguments must be 64 hex characters; pinning requires --reference")
    output = (
        args.out
        or ROOT
        / "evidence/b04-audits"
        / f"audit-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:6]}.json"
    )
    md = output.with_suffix(".md")
    for source in filter(None, (args.source, args.reference)):
        for target in (output, md):
            if target.resolve() == source.resolve() or (
                source.is_dir() and target.resolve().is_relative_to(source.resolve())
            ):
                parser.error("reports must be outside the evidence/reference source")
    if output.exists() or md.exists() or output.suffix.lower() != ".json":
        parser.error("--out must name a new .json file; reports are never overwritten")
    report = Audit(
        expected_driver=args.expected_driver_sha256,
        negative_runs=args.negative_run,
        require_t2_four=args.require_t2_four,
    ).run(args.source, args.reference, args.reference_sha256)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with md.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    print(
        f"status={report['status']} real_cases={report['real_cases']} "
        f"findings={report['finding_counts']}"
    )
    print(f"report={output.resolve()}\nreadable_report={md.resolve()}")
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
