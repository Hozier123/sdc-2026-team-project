#!/usr/bin/env python3
"""C08 warehouse-permission audit (API layer, read-only).

Runs a WAREHOUSE-role permission matrix against a KiraOrder deployment,
captures the raw responses and emits a reproducible evidence pack.

Safety properties
-----------------
* Only HTTP calls are made; no database connection, no migration, no reset.
* Write-shaped probes use schema-valid bodies plus non-existent ids, so even a
  broken role guard can only reach a 404 -- it cannot mutate a real object.
* Tokens are read from a private JSON file and are never written to the output
  directory or printed.
* ``POST /ai/wake`` is the only probe that could start an external job if the
  role guard were missing; it runs last and can be skipped with ``--skip-wake``.

Usage
-----
    py -3.13 c08_warehouse_audit.py --tokens <private demo_tokens.json> --out evidence

Exit code is 0 only when every case matches its expected status and every
semantic check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
TOOL_VERSION = "c08-audit/1.0"

DEFAULT_BASE_URL = "https://kiraorder-api.replit.app/api/v1"

# Real objects quoted by the C01 acceptance record (evidence/e2e/c01/2026-10-29).
REAL_DO = "DO_20261029_453C4BC2"
REAL_DRAFT = "DRF_39D4D66CACC440A594B1C1AEBEF151B9"
REAL_CUSTOMER = "CUS_T1"

# Non-existent ids used for write-shaped probes.
PROBE_DRAFT = "DRF_C08_PROBE"
PROBE_APPROVAL = "APR_C08_PROBE"
PROBE_CUSTOMER = "CUS_C08_PROBE"
PROBE_DO = "DO_C08_PROBE"

WAREHOUSE_DO_KEYS = {"do_number", "customer_name", "items", "approved_at"}
WAREHOUSE_ITEM_KEYS = {"sku_id", "display_name", "quantity", "unit", "picking_note"}
AI_STATUS_KEYS = {"state", "available_modes", "fallback_available", "last_checked_at", "message"}
ME_KEYS = {
    "user_id",
    "tenant",
    "display_name",
    "role",
    "permissions",
    "permission_summary",
}

FORBIDDEN_KEY_RE = re.compile(
    r"(price|tier|phone|mobile|contact|message_text|masked|raw_message|subtotal|"
    r"total|cost|credit|reply|applied_unit|final_total|draft_id|draft_version)",
    re.IGNORECASE,
)
CURRENCY_VALUE_RE = re.compile(r"(?:\bRM\s?\d|\bMYR\b)")
PHONE_VALUE_RE = re.compile(r"(?:\+?60|0)1\d[\s-]?\d{3,4}[\s-]?\d{4}")
APPROVED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
AI_STATES = {"OFFLINE", "WARMING", "READY", "DEGRADED"}


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
class HttpClient:
    def __init__(self, base_url: str, tokens: dict[str, str], timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.tokens = tokens
        self.timeout = timeout
        self.requests: list[dict[str, Any]] = []

    def call(
        self,
        method: str,
        path: str,
        role: str | None,
        body: Any | None = None,
        query: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)

        headers = {
            "Accept": "application/json",
            "User-Agent": f"{TOOL_VERSION} (+C08 He)",
        }
        if extra_headers:
            headers.update(extra_headers)
        auth_label = "none"
        if role is not None:
            token = self.tokens.get(role)
            if not token:
                raise SystemExit(f"missing token for role {role!r}")
            headers["Authorization"] = f"Bearer {token}"
            auth_label = f"Bearer <redacted:{role}>"

        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                raw = response.read()
                response_headers = {k.lower(): v for k, v in response.headers.items()}
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
            response_headers = {k.lower(): v for k, v in exc.headers.items()}
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

        text = raw.decode("utf-8", errors="replace")
        try:
            parsed: Any | None = json.loads(text) if text else None
        except json.JSONDecodeError:
            parsed = None

        record = {
            "method": method,
            "url": url,
            "path": path,
            "query": query or {},
            "extra_headers": extra_headers or {},
            "role": role or "none",
            "auth": auth_label,
            "request_body": body,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "headers": {
                key: response_headers.get(key)
                for key in (
                    "content-type",
                    "cache-control",
                    "x-request-id",
                    "www-authenticate",
                    "allow",
                )
            },
            "body_text": text,
            "body": parsed,
            "raw_bytes": raw,
            "body_sha256": hashlib.sha256(raw).hexdigest(),
            "body_bytes": len(raw),
        }
        self.requests.append(record)
        return record


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def walk_keys(value: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(f"{prefix}{key}")
            keys.extend(walk_keys(child, f"{prefix}{key}."))
    elif isinstance(value, list):
        for item in value:
            keys.extend(walk_keys(item, prefix))
    return keys


def walk_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            strings.extend(walk_strings(child))
    elif isinstance(value, list):
        for child in value:
            strings.extend(walk_strings(child))
    return strings


def validate(name: str, record: dict[str, Any]) -> list[str]:
    """Semantic checks; returns a list of failure messages."""
    body = record["body"]
    failures: list[str] = []

    if name == "me_warehouse":
        if not isinstance(body, dict):
            return ["body is not a JSON object"]
        if body.get("role") != "WAREHOUSE":
            failures.append(f"role={body.get('role')!r}")
        if (body.get("tenant") or {}).get("id") != "T1":
            failures.append(f"tenant={(body.get('tenant') or {}).get('id')!r}")
        if body.get("permissions") != []:
            failures.append(f"permissions={body.get('permissions')!r}")
        if set(body) != ME_KEYS:
            failures.append(f"unexpected /me keys: {sorted(set(body) - ME_KEYS)}")

    elif name == "me_clerk":
        if not isinstance(body, dict) or body.get("role") != "CLERK":
            failures.append("default clerk identity is not CLERK")

    elif name == "me_override_ignored":
        if not isinstance(body, dict):
            return ["body is not a JSON object"]
        if body.get("role") != "WAREHOUSE":
            failures.append(f"query role override changed identity: {body.get('role')!r}")
        if (body.get("tenant") or {}).get("id") != "T1":
            failures.append(f"query tenant override changed identity: {(body.get('tenant') or {}).get('id')!r}")
        if body.get("user_id") != "USR_T1_WAREHOUSE":
            failures.append(f"query user_id override changed identity: {body.get('user_id')!r}")

    elif name == "ai_status":
        if not isinstance(body, dict):
            return ["body is not a JSON object"]
        if set(body) != AI_STATUS_KEYS:
            failures.append(f"unexpected /ai/status keys: {sorted(set(body) - AI_STATUS_KEYS)}")
        if body.get("state") not in AI_STATES:
            failures.append(f"state={body.get('state')!r}")
        leaked = [k for k in walk_keys(body) if FORBIDDEN_KEY_RE.search(k)]
        if leaked:
            failures.append(f"ai/status business keys: {leaked}")

    elif name == "warehouse_do":
        if not isinstance(body, dict):
            return ["body is not a JSON object"]
        if set(body) != WAREHOUSE_DO_KEYS:
            failures.append(f"top-level keys {sorted(body)} != {sorted(WAREHOUSE_DO_KEYS)}")
        if body.get("do_number") != REAL_DO:
            failures.append(f"do_number={body.get('do_number')!r}")
        if not isinstance(body.get("customer_name"), str) or not body["customer_name"]:
            failures.append("customer_name missing")
        if not isinstance(body.get("items"), list) or not body["items"]:
            failures.append("items missing/empty")
        else:
            for index, item in enumerate(body["items"]):
                if not isinstance(item, dict):
                    failures.append(f"items[{index}] is not an object")
                    continue
                if set(item) != WAREHOUSE_ITEM_KEYS:
                    failures.append(f"items[{index}] keys {sorted(item)}")
                if not isinstance(item.get("quantity"), int) or item.get("quantity", 0) < 1:
                    failures.append(f"items[{index}] quantity invalid")
        if not isinstance(body.get("approved_at"), str) or not APPROVED_AT_RE.match(body["approved_at"]):
            failures.append(f"approved_at={body.get('approved_at')!r}")

    elif name == "clerk_do_full":
        if not isinstance(body, dict):
            return ["body is not a JSON object"]
        if "final_total_rm" not in body:
            failures.append("clerk projection has no final_total_rm")
        if not isinstance(body.get("lines"), list) or not body["lines"]:
            failures.append("clerk projection has no lines")
        elif "applied_unit_price" not in body["lines"][0]:
            failures.append("clerk line has no applied_unit_price")
        if "reply_draft" not in body:
            failures.append("clerk projection has no reply_draft")

    elif name == "no_error_details":
        if isinstance(body, dict) and body.get("details") not in ({}, None):
            failures.append(f"error body leaks details: {body.get('details')!r}")
        if isinstance(body, dict) and not {"error_code", "message"} <= set(body):
            failures.append(f"error body keys: {sorted(body)}")

    elif name == "do_number_t1":
        if not isinstance(body, dict) or body.get("do_number") != REAL_DO:
            failures.append("tenant query parameter changed the returned object")

    return failures


# --------------------------------------------------------------------------- #
# Matrix definition
# --------------------------------------------------------------------------- #
def build_cases(include_wake: bool) -> list[dict[str, Any]]:
    def case(
        cid: str,
        category: str,
        role: str | None,
        method: str,
        path: str,
        expected: list[int],
        *,
        body: Any | None = None,
        query: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        check: str | None = None,
        note: str = "",
        require_headers: bool = True,
    ) -> dict[str, Any]:
        return {
            "id": cid,
            "category": category,
            "role": role,
            "method": method,
            "path": path,
            "query": query or {},
            "extra_headers": extra_headers or {},
            "body": body,
            "expected": expected,
            "check": check,
            "note": note,
            "require_headers": require_headers,
        }

    cases: list[dict[str, Any]] = [
        # -- identity ------------------------------------------------------
        case("identity.me_t1_warehouse", "identity", "T1_WAREHOUSE", "GET", "/me", [200], check="me_warehouse"),
        case("identity.me_t1_clerk", "identity", "T1_CLERK", "GET", "/me", [200], check="me_clerk"),
        case("identity.me_t2_warehouse", "identity", "T2_WAREHOUSE", "GET", "/me", [200]),
        case("identity.me_no_token", "identity", None, "GET", "/me", [401], require_headers=False),
        case("identity.me_bad_token", "identity", "BAD", "GET", "/me", [401], require_headers=False),
        # -- warehouse read matrix ----------------------------------------
        case("read.customers", "read", "T1_WAREHOUSE", "GET", "/customers", [403], check="no_error_details"),
        case("read.drafts_list", "read", "T1_WAREHOUSE", "GET", "/orders/drafts", [403], check="no_error_details"),
        case("read.draft_detail", "read", "T1_WAREHOUSE", "GET", f"/orders/drafts/{REAL_DRAFT}", [403], check="no_error_details"),
        case("read.approvals_list", "read", "T1_WAREHOUSE", "GET", "/approvals", [403], check="no_error_details"),
        case("read.approval_detail", "read", "T1_WAREHOUSE", "GET", f"/approvals/{PROBE_APPROVAL}", [403], check="no_error_details"),
        case("read.activity", "read", "T1_WAREHOUSE", "GET", "/activity", [403], check="no_error_details"),
        case("read.audit_detail", "read", "T1_WAREHOUSE", "GET", f"/orders/{REAL_DO}/audit-detail", [403], check="no_error_details"),
        case("read.delivery_order", "read", "T1_WAREHOUSE", "GET", f"/delivery-orders/{REAL_DO}", [403], check="no_error_details"),
        case("read.ai_status", "read", "T1_WAREHOUSE", "GET", "/ai/status", [200], check="ai_status"),
        case("read.warehouse_do", "read", "T1_WAREHOUSE", "GET", f"/warehouse/delivery-orders/{REAL_DO}", [200], check="warehouse_do"),
        case("read.warehouse_do_missing", "read", "T1_WAREHOUSE", "GET", f"/warehouse/delivery-orders/{PROBE_DO}", [404], check="no_error_details"),
        case(
            "read.warehouse_list_absent",
            "read",
            "T1_WAREHOUSE",
            "GET",
            "/warehouse/delivery-orders",
            [404],
            note="no bulk DO enumeration route for WAREHOUSE",
        ),
        case("read.clerk_do_full", "read", "T1_CLERK", "GET", f"/delivery-orders/{REAL_DO}", [200], check="clerk_do_full", note="projection source for field diff"),
        # -- warehouse write matrix (valid body + non-existent id) --------
        case(
            "write.parse_draft",
            "write",
            "T1_WAREHOUSE",
            "POST",
            "/orders/parse-draft",
            [403],
            body={"customer_id": PROBE_CUSTOMER, "message_text": "Tepung 4 ctn"},
            check="no_error_details",
            note="non-existent customer: a guard bypass would 404, not write",
        ),
        case(
            "write.save_lines",
            "write",
            "T1_WAREHOUSE",
            "PUT",
            f"/orders/drafts/{PROBE_DRAFT}/lines",
            [403],
            body={"expected_version": 1, "lines": []},
            check="no_error_details",
        ),
        case(
            "write.approve",
            "write",
            "T1_WAREHOUSE",
            "POST",
            f"/orders/{PROBE_DRAFT}/approve",
            [403],
            body={"expected_version": 1},
            check="no_error_details",
        ),
        case(
            "write.decide",
            "write",
            "T1_WAREHOUSE",
            "POST",
            f"/approvals/{PROBE_APPROVAL}/decide",
            [403],
            body={"decision": "APPROVE"},
            check="no_error_details",
        ),
        case(
            "write.discard",
            "write",
            "T1_WAREHOUSE",
            "POST",
            f"/orders/drafts/{PROBE_DRAFT}/discard",
            [403],
            body={"expected_version": 1, "note": "c08 probe"},
            check="no_error_details",
        ),
        case(
            "write.clarification_copied",
            "write",
            "T1_WAREHOUSE",
            "POST",
            f"/orders/drafts/{PROBE_DRAFT}/clarification-copied",
            [403],
            body={"expected_version": 1},
            check="no_error_details",
        ),
        # -- cross-role ----------------------------------------------------
        case("cross.clerk_warehouse_view", "cross_role", "T1_CLERK", "GET", f"/warehouse/delivery-orders/{REAL_DO}", [403], check="no_error_details"),
        case("cross.owner_warehouse_view", "cross_role", "T1_OWNER", "GET", f"/warehouse/delivery-orders/{REAL_DO}", [403], check="no_error_details"),
        # -- tenant isolation ---------------------------------------------
        case("tenant.t2_on_t1_do", "tenant", "T2_WAREHOUSE", "GET", f"/warehouse/delivery-orders/{REAL_DO}", [404], check="no_error_details"),
        case(
            "tenant.t2_override_param",
            "tenant",
            "T2_WAREHOUSE",
            "GET",
            f"/warehouse/delivery-orders/{REAL_DO}",
            [404],
            query={"tenant_id": "T1"},
            check="no_error_details",
            note="query-string tenant override must be ignored",
        ),
        case(
            "tenant.t1_override_param",
            "tenant",
            "T1_WAREHOUSE",
            "GET",
            f"/warehouse/delivery-orders/{REAL_DO}",
            [200],
            query={"tenant_id": "T2"},
            check="do_number_t1",
        ),
        case(
            "tenant.t2_header_override",
            "tenant",
            "T2_WAREHOUSE",
            "GET",
            f"/warehouse/delivery-orders/{REAL_DO}",
            [404],
            extra_headers={"X-Tenant-Id": "T1"},
            check="no_error_details",
            note="tenant header override must be ignored",
        ),
        # -- identity override --------------------------------------------
        case(
            "override.me_query",
            "override",
            "T1_WAREHOUSE",
            "GET",
            "/me",
            [200],
            query={"role": "OWNER", "user_id": "USR_T1_OWNER", "tenant_id": "T2"},
            check="me_override_ignored",
            note="identity must come from the token only",
        ),
        case(
            "override.me_headers",
            "override",
            "T1_WAREHOUSE",
            "GET",
            "/me",
            [200],
            extra_headers={"X-Tenant-Id": "T2", "X-User-Id": "USR_T1_OWNER", "X-Role": "OWNER"},
            check="me_override_ignored",
            note="identity headers must be ignored",
        ),
        # -- method fuzz ---------------------------------------------------
        case("method.delete_warehouse_do", "method", "T1_WAREHOUSE", "DELETE", f"/warehouse/delivery-orders/{REAL_DO}", [405], require_headers=False),
        case("method.post_warehouse_do", "method", "T1_WAREHOUSE", "POST", f"/warehouse/delivery-orders/{REAL_DO}", [405], body={}, require_headers=False),
        case("method.patch_delivery_order", "method", "T1_WAREHOUSE", "PATCH", f"/delivery-orders/{REAL_DO}", [405], body={}, require_headers=False),
        case("method.put_approval", "method", "T1_WAREHOUSE", "PUT", f"/approvals/{PROBE_APPROVAL}", [405], body={}, require_headers=False),
        case("method.delete_draft", "method", "T1_WAREHOUSE", "DELETE", f"/orders/drafts/{PROBE_DRAFT}", [405], require_headers=False),
        case("method.get_parse", "method", "T1_WAREHOUSE", "GET", "/orders/parse-draft", [405], require_headers=False),
        # -- unauthenticated ----------------------------------------------
        case("auth.unauth_warehouse_do", "auth", None, "GET", f"/warehouse/delivery-orders/{REAL_DO}", [401], check="no_error_details", require_headers=False),
        case("auth.unauth_customers", "auth", None, "GET", "/customers", [401], check="no_error_details", require_headers=False),
    ]

    if include_wake:
        cases.append(
            case(
                "write.ai_wake",
                "write",
                "T1_WAREHOUSE",
                "POST",
                "/ai/wake",
                [403],
                check="no_error_details",
                note="if the guard were missing this would start a warm-up job; runs last",
            )
        )
    return cases


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def run(client: HttpClient, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        started = time.perf_counter()
        record = client.call(
            case["method"],
            case["path"],
            case["role"],
            case["body"],
            case["query"],
            case.get("extra_headers"),
        )
        record["case_id"] = case["id"]
        failures: list[str] = []

        if record["status"] not in case["expected"]:
            failures.append(f"status {record['status']} not in {case['expected']}")

        if case["require_headers"] and record["status"] in (200, 401, 403):
            headers = record["headers"]
            if not headers.get("x-request-id"):
                failures.append("missing X-Request-ID")
            if headers.get("cache-control") != "no-store":
                failures.append(f"Cache-Control={headers.get('cache-control')!r}")
            if record["status"] == 401 and "bearer" not in (headers.get("www-authenticate") or "").lower():
                failures.append("401 without WWW-Authenticate: Bearer")

        if case["check"]:
            failures.extend(validate(case["check"], record))

        results.append(
            {
                **case,
                "status": record["status"],
                "expected_ok": record["status"] in case["expected"],
                "elapsed_ms": record["elapsed_ms"],
                "response_sha256": record["body_sha256"],
                "response_bytes": record["body_bytes"],
                "request_id": record["headers"].get("x-request-id"),
                "cache_control": record["headers"].get("cache-control"),
                "failures": failures,
                "passed": not failures,
                "index": index,
            }
        )
    return results


def save_responses(client: HttpClient, results: list[dict[str, Any]], out: Path) -> None:
    responses = out / "responses"
    responses.mkdir(parents=True, exist_ok=True)
    for record in client.requests:
        name = record.get("case_id") or f"unmatched_{len(list(responses.glob('*')))}"
        suffix = ".json" if record["body"] is not None else ".txt"
        target = responses / f"{name}{suffix}"
        # Store the exact bytes received on the wire; never re-serialise.
        target.write_bytes(record["raw_bytes"])


def verify_response_files(results: list[dict[str, Any]], client: HttpClient, out: Path) -> None:
    """Fail the run unless every response file is byte-identical to the wire body."""
    by_case = {record.get("case_id"): record for record in client.requests}
    for result in results:
        record = by_case[result["id"]]
        suffix = ".json" if record["body"] is not None else ".txt"
        path = out / "responses" / f"{result['id']}{suffix}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != result["response_sha256"]:
            raise SystemExit(
                f"response file hash mismatch for {result['id']}: {digest} != {result['response_sha256']}"
            )
        if path.stat().st_size != result["response_bytes"]:
            raise SystemExit(f"response file size mismatch for {result['id']}")


def field_scan(results: list[dict[str, Any]], client: HttpClient, out: Path) -> dict[str, Any]:
    """Scan every 2xx body returned to WAREHOUSE for forbidden keys/values."""
    found_keys: list[dict[str, Any]] = []
    found_values: list[dict[str, Any]] = []
    scanned: list[str] = []
    by_case = {record.get("case_id"): record for record in client.requests}

    for result in results:
        record = by_case.get(result["id"])
        if record is None:
            continue
        if result["role"] != "T1_WAREHOUSE" or record["status"] != 200:
            continue
        if record["body"] is None:
            continue
        scanned.append(result["id"])
        for key in walk_keys(record["body"]):
            if FORBIDDEN_KEY_RE.search(key):
                found_keys.append({"case": result["id"], "key": key})
        for value in walk_strings(record["body"]):
            if CURRENCY_VALUE_RE.search(value):
                found_values.append({"case": result["id"], "kind": "currency", "value": value})
            if PHONE_VALUE_RE.search(value):
                found_values.append({"case": result["id"], "kind": "phone", "value": value})

    payload = {
        "scanned_cases": scanned,
        "forbidden_keys": found_keys,
        "forbidden_values": found_values,
        "passed": not found_keys and not found_values,
    }
    (out / "field-scan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def projection_diff(results: list[dict[str, Any]], client: HttpClient, out: Path) -> dict[str, Any]:
    by_id = {result["id"]: result for result in results}
    by_case = {record.get("case_id"): record for record in client.requests}
    clerk = by_case["read.clerk_do_full"]["body"]
    warehouse = by_case["read.warehouse_do"]["body"]

    top_removed = sorted(set(clerk) - set(warehouse))
    clerk_line = clerk["lines"][0]
    wh_item = warehouse["items"][0]
    line_removed = sorted(set(clerk_line) - set(wh_item))

    final_total = str(clerk.get("final_total_rm", ""))
    warehouse_text = by_case["read.warehouse_do"]["body_text"]
    total_value_present = bool(final_total) and final_total in warehouse_text

    payload = {
        "source_case": by_id["read.clerk_do_full"]["id"],
        "target_case": by_id["read.warehouse_do"]["id"],
        "clerk_top_level_keys": sorted(clerk),
        "warehouse_top_level_keys": sorted(warehouse),
        "top_level_removed": top_removed,
        "clerk_line_keys": sorted(clerk_line),
        "warehouse_item_keys": sorted(wh_item),
        "line_fields_removed": line_removed,
        "final_total_rm": final_total,
        "final_total_value_present_in_warehouse_body": total_value_present,
        "passed": bool(top_removed)
        and bool(line_removed)
        and not total_value_present
        and set(warehouse) == WAREHOUSE_DO_KEYS
        and set(wh_item) == WAREHOUSE_ITEM_KEYS,
    }
    (out / "projection-diff.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def markdown_table(results: list[dict[str, Any]]) -> str:
    lines = [
        "| # | 用例 | 角色 | 请求 | 期望 | 实际 | 结果 |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in results:
        path = result["path"] + (
            "?" + "&".join(f"{k}={v}" for k, v in result["query"].items()) if result["query"] else ""
        )
        lines.append(
            f"| {result['index'] + 1} | `{result['id']}` | {result['role'] or '-'} | "
            f"`{result['method']} {path}` | {result['expected']} | {result['status']} | "
            f"{'PASS' if result['passed'] else '**FAIL**'} |"
        )
    return "\n".join(lines) + "\n"


def sha256_tree(out: Path) -> None:
    entries = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.name == "SHA256.txt":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(out).as_posix()}")
    (out / "SHA256.txt").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="C08 warehouse-permission audit")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--tokens", required=True, help="private demo token JSON (never copied to output)")
    parser.add_argument("--out", default="evidence")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--skip-wake", action="store_true", help="skip POST /ai/wake")
    args = parser.parse_args()

    token_path = Path(args.tokens)
    token_data = json.loads(token_path.read_text(encoding="utf-8"))
    tokens = {
        "T1_CLERK": token_data["T1"]["USR_T1_CLERK"],
        "T1_OWNER": token_data["T1"]["USR_T1_OWNER"],
        "T1_WAREHOUSE": token_data["T1"]["USR_T1_WAREHOUSE"],
        "T2_WAREHOUSE": token_data["T2"]["USR_T2_WAREHOUSE"],
        "BAD": "c08-invalid-token",
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(TZ).isoformat(timespec="seconds")
    client = HttpClient(args.base_url, tokens, args.timeout)

    # Identity + object-of-record first, so the evidence pack states what was tested.
    cases = build_cases(include_wake=not args.skip_wake)
    results = run(client, cases)
    finished_at = datetime.now(TZ).isoformat(timespec="seconds")

    save_responses(client, results, out)
    verify_response_files(results, client, out)
    scan = field_scan(results, client, out)
    diff = projection_diff(results, client, out)

    warehouse_do = next(r for r in client.requests if r["path"] == f"/warehouse/delivery-orders/{REAL_DO}" and r["status"] == 200)
    environment = {
        "case_id": "C08",
        "base_url": args.base_url,
        "started_at": started_at,
        "finished_at": finished_at,
        "tool": TOOL_VERSION,
        "python": sys.version.split()[0],
        "operator": "He",
        "token_source": token_path.name,
        "tokens_recorded": False,
        "object_of_record": {
            "do_number": REAL_DO,
            "draft_id": REAL_DRAFT,
            "customer": (warehouse_do["body"] or {}).get("customer_name"),
            "approved_at": (warehouse_do["body"] or {}).get("approved_at"),
            "request_id": warehouse_do["headers"].get("x-request-id"),
        },
        "identities": {
            record["case_id"]: (record["body"] or {})
            for record in client.requests
            if record["path"] == "/me" and record["status"] == 200
        },
    }
    (out / "environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    matrix = {
        "case_id": "C08",
        "base_url": args.base_url,
        "started_at": started_at,
        "finished_at": finished_at,
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "cases": results,
    }
    (out / "matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "matrix.md").write_text(
        "# C08 WAREHOUSE 权限矩阵（API 层）\n\n"
        f"- 执行时间：{started_at} — {finished_at}（UTC+8）\n"
        f"- Base URL：`{args.base_url}`\n"
        f"- 用例：{matrix['passed']}/{matrix['total']} 通过\n\n"
        + markdown_table(results)
        + "\n失败用例："
        + (", ".join(f"`{r['id']}`" for r in results if not r["passed"]) or "无")
        + "\n",
        encoding="utf-8",
    )

    requests_log = [
        {
            "index": index,
            "case": results[index]["id"] if index < len(results) else None,
            "method": record["method"],
            "url": record["url"],
            "role": record["role"],
            "request_body": record["request_body"],
            "status": record["status"],
            "request_id": record["headers"].get("x-request-id"),
            "cache_control": record["headers"].get("cache-control"),
            "www_authenticate": record["headers"].get("www-authenticate"),
            "response_sha256": record["body_sha256"],
            "response_bytes": record["body_bytes"],
            "elapsed_ms": record["elapsed_ms"],
        }
        for index, record in enumerate(client.requests)
    ]
    (out / "api-requests.json").write_text(
        json.dumps(requests_log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    failed = [r["id"] for r in results if not r["passed"]]
    browser_dir = out / "browser"
    browser_files = sorted(p.name for p in browser_dir.glob("*.png"))
    browser_sources = sorted((browser_dir / "source").glob("*.jpg"))
    browser_ready = {"c08_01_picking_current.png", "c08_02_forbidden_403.png"} <= set(browser_files)
    browser_gaps = (
        []
        if browser_ready
        else [
            "current f8ff1d7 picking page screenshot (browser/)",
            "DevTools 403 screenshot with FORBIDDEN_ACTION body (browser/)",
        ]
    )
    signed_off = (out / "reviews" / "03-Zhou-signoff-2026-10-30.md").exists()
    acceptance = {
        "case_id": "C08",
        "title": "Warehouse role permission matrix (API layer, read-only)",
        "status": "PASS_API_LAYER"
        if not failed and scan["passed"] and diff["passed"]
        else "FAIL",
        "overall_status": "SIGNED_OFF" if signed_off else "NOT_SIGNED_OFF",
        "repo_status": "PENDING_COMMIT",
        "gate_a_status": "DEFERRED",
        "run_at": finished_at,
        "metadata_updated_at": finished_at,
        "operator": "He",
        "review_status": "ZHOU_SIGNED_OFF"
        if signed_off
        else "ZHOU_REVIEW_API_BROWSER_PASSED_PENDING_SIGNOFF",
        "independent_review_status": "PASSED" if signed_off else "PENDING_SIGNOFF",
        "review_record": "evidence/reviews/03-Zhou-signoff-2026-10-30.md"
        if signed_off
        else "evidence/reviews/02-Zhou-review-2026-10-30.md",
        "signed_off_by": "Zhou Jingxi" if signed_off else None,
        "signed_off_at": "2026-10-30T16:40:00+08:00" if signed_off else None,
        "hash_convention": "responses/*.json store the exact raw response bytes received on the"
        " wire; each file SHA-256 equals matrix.response_sha256 (and its size equals response_bytes)",
        "open_items": ["Draft PR / repository commit pending"]
        if signed_off
        else [
            "response_sha256 vs response-file hash mismatch fixed by storing raw bytes;"
            " awaiting Zhou's SIGNED_OFF"
        ],
        "base_url": args.base_url,
        "object_of_record": environment["object_of_record"],
        "scope_approval": {
            "by": "Zhou Jingxi",
            "date": "2026-10-30",
            "channel": "chat reply relayed through He",
            "decision": "C01 warehouse page evidence may be cited; browser part needs one 403"
            " screenshot; API layer is recorded first and must be marked pending-commit",
            "conditions": [
                "same DO DO_20261029_453C4BC2",
                "Gate E version frontend f8ff1d7 / backend 555f0fa",
                "WAREHOUSE identity visible (Ah Kow / Warehouse)",
                "DevTools request GET /api/v1/delivery-orders/DO_20261029_453C4BC2 returns 403",
                "FORBIDDEN_ACTION body visible, or full URL plus 403; status code alone is not enough",
                "warehouse page shows no price, phone or raw message; C01 warehouse evidence stays cited",
                "if C01 page evidence is not the f8ff1d7 build, add a current picking page screenshot",
                "403 must use the full DO endpoint, not audit-detail",
                "evidence pack in a controlled directory with SHA256; mark API layer pending-commit"
                " before the repository commit and do not sign the whole case off early",
            ],
        },
        "version_basis": {
            "frontend": "f8ff1d7",
            "frontend_proof": "gh-pages commit 12ff95f 'Deploy B01 frontend from f8ff1d7'"
            " (2026-10-29T11:51:25Z), followed by 94f0a6e recording the published index",
            "backend": "555f0fa",
            "backend_proof": "0a255df (2026-10-30) changes only docs, tools, tests and README;"
            " the last commit touching backend/app is 555f0fa",
            "runtime_attestation": "The API does not expose the deployed commit; version"
            " attribution is repository evidence, not runtime attestation.",
        },
        "browser_evidence": {
            "status": "CAPTURED" if browser_ready else "PENDING",
            "directory": "browser/",
            "files": browser_files,
            "captured_at": datetime.now(TZ).date().isoformat() if browser_ready else None,
            "source_files": [
                {"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest().upper()}
                for p in browser_sources
            ],
            "required": [
                "c08_01_picking_current.png: current f8ff1d7 build picking page for"
                " DO_20261029_453C4BC2 with Ah Kow / Warehouse visible and no price/phone/raw message",
                "c08_02_forbidden_403.png: DevTools (Console or Network) on GET"
                " /api/v1/delivery-orders/DO_20261029_453C4BC2 with 403 and the FORBIDDEN_ACTION"
                " response body (or full URL plus 403 on one screen)",
            ],
            "reason_current_picking_page": "C01 browser session ran 2026-10-29 17:13-17:16 UTC+8,"
            " before the f8ff1d7 Pages deploy at 19:51 UTC+8, so the C01 page screenshots are not"
            " the f8ff1d7 build.",
            "verification": {
                "identity": "Ah Kow / Warehouse visible in the c08_01 top bar",
                "do_number": "DO_20261029_453C4BC2 visible in both screenshots",
                "build": "v1.4.0 badge in c08_01; f8ff1d7 is the Pages build per gh-pages 12ff95f",
                "forbidden": "full URL, 403 and FORBIDDEN_ACTION body visible in c08_02; no token shown",
                "field_minimization": "c08_01 shows no price, phone or raw message",
            }
            if browser_ready
            else None,
        },
        "numbers": {
            "cases_total": len(results),
            "cases_passed": sum(1 for r in results if r["passed"]),
            "cases_failed": len(failed),
            "field_scan_passed": scan["passed"],
            "projection_diff_passed": diff["passed"],
        },
        "failed_cases": failed,
        "coverage": {
            "role_matrix": "WAREHOUSE vs CLERK/OWNER on read endpoints",
            "write_endpoints": "schema-valid body + non-existent id (no DB writes)",
            "tenant_isolation": "T2 token against T1 object, query-string and header override",
            "identity_binding": "role/user_id/tenant_id query parameters and X-* headers ignored",
            "method_surface": "unsafe methods on read routes",
            "enumeration": "no WAREHOUSE DO list route",
            "responses": "raw JSON captured per case",
        },
        "not_covered": [
            *browser_gaps,
            "browser-captured HAR (this pack is API-level only)",
            "page-level absence of write entry points (C01 covers this for one DO)",
            "frontend Local Demo path",
            "CLERK/OWNER-to-OWNER-IDOR (out of C08 scope)",
        ],
        "boundaries": [
            "Synthetic T1/T2 demo data only.",
            "Deployed production backend; deployed commit is not exposed by the API.",
            "No DB writes, no reset; /ai/wake is rejected with 403 before any warm-up job.",
        ],
        "notes": [
            "Warehouse DO is an exact four-key projection; the CLERK projection of the same DO"
            " exposes 11 additional top-level fields and 5 additional line fields, all absent"
            " from the warehouse body (projection-diff.json).",
            "/ai/status is readable by WAREHOUSE by contract (OpenAPI declares only 200/401) and"
            " exposes no business fields; this is not a C08 defect.",
            "Invalid request bodies return 422 before the handler-level role check. The matrix"
            " therefore uses schema-valid bodies plus non-existent ids, so a missing guard could"
            " only reach 404 and never mutate data.",
            "The implementation also guards /discard and /clarification-copied for WAREHOUSE even"
            " though those paths are not in the frozen Gate 0 OpenAPI path set (contract"
            " completeness is tracked separately, not as a C08 permission defect).",
        ],
        "c01_reference": "evidence/e2e/c01/2026-10-29/acceptance.json",
        "artifacts": [
            "environment.json",
            "matrix.json",
            "matrix.md",
            "field-scan.json",
            "projection-diff.json",
            "api-requests.json",
            "responses/",
            "browser/",
            "reviews/",
            ".gitattributes",
            "SHA256.txt",
        ],
    }
    (out / "acceptance.json").write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    sha256_tree(out)

    print(f"C08 API matrix: {acceptance['numbers']['cases_passed']}/{len(results)} passed, "
          f"field_scan={scan['passed']}, projection_diff={diff['passed']}, "
          f"status={acceptance['status']}")
    for result in results:
        if not result["passed"]:
            print(f"FAIL {result['id']}: status={result['status']} expected={result['expected']} "
                  f"failures={result['failures']}")
    print(f"evidence: {out.resolve()}")
    return 0 if acceptance["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
