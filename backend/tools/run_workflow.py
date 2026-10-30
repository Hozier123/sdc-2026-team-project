"""B04 HTTP workflow driver. No database access, reset, implicit retries, or AI wake."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("CLERK", "OWNER", "WAREHOUSE")
LINE_FIELDS = (
    "sku_id",
    "family_id",
    "confirmed_qty",
    "uom",
    "pack_size",
    "grade",
    "unit_price_override",
    "override_reason",
    "match_source",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")
    # Windows scanners may briefly hold a just-written checkpoint. Only retry the
    # local atomic replacement; HTTP mutations are never retried.
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.02 * (2**attempt))


class StopRun(Exception):
    def __init__(self, status: str, reason: str):
        self.status, self.reason = status, reason
        super().__init__(reason)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise StopRun("FAIL", reason)


def validate_case(case: dict) -> None:
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", case["case_id"])), "invalid case_id")
    require(
        case["route"] in {"direct", "owner_approve", "owner_reject", "stock_blocked"},
        "invalid route",
    )
    require(
        bool(case["tenant_id"]) and bool(case["parse"]["customer_id"]), "missing tenant/customer"
    )
    require(bool(case["parse"]["message_text"]), "missing synthetic message")
    require(bool(case["expected"]["lines"]), "expected business lines required")
    require(
        bool(case["allowed_ai_modes"])
        and set(case["allowed_ai_modes"]) <= {"LLM", "FALLBACK", "ALIAS_ONLY", "MIXED"},
        "invalid allowed_ai_modes",
    )
    require(set(case["token_env"]) == set(ROLES), "token_env must name all three role variables")
    for variable in case["token_env"].values():
        require(
            bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", variable)), "invalid env variable name"
        )
    if case["route"] == "owner_reject":
        require(bool(case.get("decision_note", "").strip()), "rejection note required")
    for line in case["expected"]["lines"]:
        require(
            isinstance(line["quantity"], int) and line["quantity"] > 0, "invalid expected quantity"
        )
        require(Decimal(line["applied_unit_price"]) >= 0, "invalid expected price")
    save = case.get("save", {})
    require("expected_version" not in save, "save version is always taken from the server")


def resolve(value: Any, draft: dict) -> Any:
    """A single {$draft: 'lines.0.line_id'} preserves JSON types."""
    if isinstance(value, dict):
        if set(value) == {"$draft"}:
            current: Any = draft
            try:
                for part in value["$draft"].split("."):
                    current = current[int(part)] if isinstance(current, list) else current[part]
                return current
            except (KeyError, IndexError, TypeError, ValueError):
                raise StopRun("BLOCKED", f"draft binding unavailable: {value['$draft']}") from None
        return {key: resolve(item, draft) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, draft) for item in value]
    return value


def save_body(case: dict, draft: dict) -> dict:
    body = resolve(case.get("save", {}), draft)
    if "lines" not in body:
        if not draft.get("lines") or any(not line.get("sku_id") for line in draft["lines"]):
            raise StopRun("BLOCKED", "parsed lines need explicit SKU/issue decisions in case.save")
        body["lines"] = [
            {
                "line_id": line["line_id"],
                **{k: line[k] for k in LINE_FIELDS if k in line},
                "save_to_alias_cache": False,
            }
            for line in draft["lines"]
        ]
    body["expected_version"] = draft["version"]
    return body


class Driver:
    def __init__(
        self,
        case: dict,
        base_url: str,
        out: Path,
        *,
        run_id: str | None = None,
        resume: bool = False,
        mock: bool = False,
        timeout: float = 20,
        client: httpx.Client | None = None,
        environment: str = "",
    ):
        validate_case(case)
        parsed = urlsplit(base_url)
        require(parsed.scheme in {"http", "https"} and bool(parsed.netloc), "invalid API URL")
        require(
            not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment,
            "API URL must not contain credentials, query, or fragment",
        )
        require(parsed.path.rstrip("/") == "/api/v1", "API URL must end in /api/v1")
        require(
            parsed.scheme == "https" or parsed.hostname in {"127.0.0.1", "localhost", "::1"},
            "remote API requires HTTPS",
        )
        require(bool(environment.strip()), "provide a non-secret isolated environment label")
        self.case, self.base, self.mock = case, base_url.rstrip("/"), mock
        self.run_id = run_id or f"b04-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        require(
            bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", self.run_id))
            and self.run_id not in {".", ".."},
            "invalid run_id",
        )
        self.path = out / self.run_id
        self.client = client or httpx.Client(
            timeout=timeout, follow_redirects=False, trust_env=False
        )
        self.tokens = {
            role: (
                f"b04-mock-{role}" if mock else os.environ.get(case["token_env"][role], "").strip()
            )
            for role in ROLES
        }
        self.verified: dict[str, str] = {}
        binding = {
            "case_sha256": digest(case),
            "base_url": self.base,
            "mock": mock,
            "environment": environment,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        if resume:
            self.state = json.loads((self.path / "checkpoint.json").read_text("utf-8"))
            require(self.state["binding"] == binding, "resume binding changed; use a new run_id")
            require(
                self.state["status"] not in {"INDETERMINATE", "FAIL"},
                "failed/uncertain run is sealed; reconcile it before a new run",
            )
        else:
            self.path.mkdir(parents=True, exist_ok=False)
            try:
                sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
            except (OSError, subprocess.CalledProcessError):
                sha = "unavailable"
            self.state = {
                "run_id": self.run_id,
                "case_id": case["case_id"],
                "started_at": now(),
                "binding": binding,
                "code_sha": sha,
                "status": "RUNNING",
                "steps": {},
                "identities": {},
                "pending_request": None,
                "actual_ai_mode": None,
                "planned_ai_modes": case["allowed_ai_modes"],
                "limitations": [
                    "HTTP evidence only; no direct database stock assertion",
                    "No browser UX, independent review, or live AI acceptance",
                ],
            }
            write_json(self.path / "case.json", case)
        # A crash between sending and checkpointing a mutation must never replay that mutation.
        pending = self.state.get("pending_request")
        if pending and pending["method"] != "GET":
            self.state.update(
                status="INDETERMINATE", reason="unfinished mutation; manual reconciliation"
            )
        self.checkpoint()

    def checkpoint(self) -> None:
        self.state["updated_at"] = now()
        write_json(self.path / "checkpoint.json", self.state)

    def redact(self, text: str) -> str:
        for token in sorted(filter(None, self.tokens.values()), key=len, reverse=True):
            text = text.replace(token, "[REDACTED_TOKEN]")
        return re.sub(r"(?i)Bearer\s+[^\s\"<>]+", "Bearer [REDACTED_TOKEN]", text)

    def call(
        self,
        name: str,
        role: str,
        method: str,
        path: str,
        body: dict | None = None,
        expected: tuple[int, ...] = (200,),
        *,
        cached: bool = True,
    ) -> dict:
        if cached and name in self.state["steps"]:
            return self.state["steps"][name]
        token = self.tokens[role]
        if not token:
            raise StopRun("BLOCKED", f"missing role session: {self.case['token_env'][role]}")
        number = len(list(self.path.glob("request-*.json"))) + 1
        sent_id = f"b04-{uuid4().hex}"
        record = {
            "run_id": self.run_id,
            "case_id": self.case["case_id"],
            "step": name,
            "role": role,
            "method": method,
            "path": path,
            "sent_request_id": sent_id,
            "request_id": None,
            "started_at": now(),
            "request_body": body,
            "status": "IN_FLIGHT",
            "response_body": None,
            "http_status": None,
        }
        record_path = self.path / f"request-{number:03d}-{name}.json"
        write_json(record_path, json.loads(self.redact(json.dumps(record))))
        self.state["pending_request"] = {"method": method, "step": name, "file": record_path.name}
        self.checkpoint()
        start = time.perf_counter()
        response = None
        try:
            response = self.client.request(
                method,
                self.base + path,
                headers={"Authorization": f"Bearer {token}", "X-Request-ID": sent_id},
                json=body,
            )
        except httpx.HTTPError as exc:
            record["transport_error"] = type(exc).__name__
        record["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
        record["finished_at"] = now()
        raw = b""
        parsed = None
        if response is not None:
            raw = response.content
            safe_raw = self.redact(response.text)
            record.update(
                http_status=response.status_code,
                request_id=self.redact(response.headers.get("X-Request-ID", "")) or None,
                response_headers={
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() in {"x-request-id", "content-type", "retry-after"}
                },
                raw_response_sha256=hashlib.sha256(raw).hexdigest(),
                raw_response_redacted=safe_raw != response.text,
            )
            response_bytes = raw if safe_raw == response.text else safe_raw.encode("utf-8")
            (self.path / f"response-{number:03d}-{name}.txt").write_bytes(response_bytes)
            try:
                parsed = json.loads(safe_raw)
            except (ValueError, UnicodeError):
                pass
            record["response_body"] = parsed
        uncertain = method != "GET" and (
            response is None
            or response.status_code >= 500
            or (response.is_success and not isinstance(parsed, dict))
        )
        good = (
            response is not None
            and response.status_code in expected
            and isinstance(parsed, dict)
            and bool(record["request_id"])
        )
        record["status"] = "PASS" if good else ("INDETERMINATE" if uncertain else "FAIL")
        write_json(record_path, json.loads(self.redact(json.dumps(record))))
        self.state["pending_request"] = None
        if not good:
            code = parsed.get("error_code") if isinstance(parsed, dict) else None
            status = (
                "INDETERMINATE"
                if uncertain
                else (
                    "BLOCKED"
                    if response is None or response.status_code in {401, 403, 429, 503}
                    else "FAIL"
                )
            )
            raise StopRun(
                status,
                f"{name}: HTTP {record['http_status']}, code={code}, "
                f"request_id={record['request_id']}; see {record_path.name}",
            )
        result = {
            "http_status": response.status_code,
            "body": parsed,
            "request_id": record["request_id"],
            "file": record_path.name,
        }
        self.state["steps"][name] = result
        self.checkpoint()
        return result

    def identity(self, role: str) -> None:
        if role in self.verified:
            return
        user = self.call(f"identity_{role.lower()}", role, "GET", "/me", cached=False)["body"]
        require(user.get("role") == role, f"{role}: session has wrong role")
        require(
            user.get("tenant", {}).get("id") == self.case["tenant_id"],
            f"{role}: session has wrong tenant",
        )
        old = self.state["identities"].get(role)
        require(old is None or old == user["user_id"], "resume identity changed; use a new run_id")
        self.state["identities"][role] = user["user_id"]
        self.verified[role] = user["user_id"]
        self.checkpoint()

    def business_lines(self, lines: list, *, draft: bool = False) -> None:
        actual = [
            (
                x["sku_id"],
                x["effective_qty"] if draft else x["quantity"],
                x["uom"] if draft else x["unit"],
                Decimal(x["effective_unit_price"] if draft else x["applied_unit_price"]),
            )
            for x in lines
        ]
        expected = [
            (x["sku_id"], x["quantity"], x["unit"], Decimal(x["applied_unit_price"]))
            for x in self.case["expected"]["lines"]
        ]
        require(
            actual == expected,
            "business lines differ from case.expected (SKU/qty/unit/price/order)",
        )
        for line, (_, quantity, _, price) in zip(lines, expected, strict=True):
            require(Decimal(line["subtotal_rm"]) == quantity * price, "line subtotal mismatch")

    def verify_do(self, delivery: dict, saved: dict) -> None:
        require(
            delivery["draft_id"] == saved["draft_id"]
            and delivery["draft_version"] == saved["version"],
            "DO references wrong draft/version",
        )
        require(
            delivery["customer_id"] == self.case["parse"]["customer_id"], "DO customer mismatch"
        )
        self.business_lines(delivery["lines"])
        require(
            Decimal(delivery["final_total_rm"])
            == sum(Decimal(x["subtotal_rm"]) for x in delivery["lines"]),
            "DO total mismatch",
        )
        mode = "DIRECT" if self.case["route"] == "direct" else "OWNER_APPROVED"
        require(delivery["approval_mode"] == mode, "unexpected approval mode")
        actor = "CLERK" if mode == "DIRECT" else "OWNER"
        require(
            delivery["approved_by"] == self.state["identities"][actor], "wrong approver identity"
        )

    def execute(self, until: str = "complete") -> dict:
        try:
            if self.state["status"] == "INDETERMINATE":
                raise StopRun("INDETERMINATE", self.state["reason"])
            self.identity("CLERK")
            parsed = self.call("parse", "CLERK", "POST", "/orders/parse-draft", self.case["parse"])[
                "body"
            ]
            self.state.update(draft_id=parsed["draft_id"], actual_ai_mode=parsed["ai_mode"])
            self.checkpoint()
            require(
                parsed["customer_id"] == self.case["parse"]["customer_id"],
                "parse customer mismatch",
            )
            require(
                parsed["ai_mode"] in self.case["allowed_ai_modes"],
                "actual ai_mode is outside planned path",
            )
            draft_path = "/orders/drafts/" + quote(parsed["draft_id"], safe="")
            saved = self.call(
                "save", "CLERK", "PUT", draft_path + "/lines", save_body(self.case, parsed)
            )["body"]
            require(
                saved["draft_id"] == parsed["draft_id"]
                and saved["version"] == parsed["version"] + 1,
                "save draft/version mismatch",
            )
            self.state["draft_version"] = saved["version"]
            require(saved["ai_mode"] == parsed["ai_mode"], "save changed historical ai_mode")
            self.business_lines(saved["lines"], draft=True)
            if until == "saved":
                raise StopRun("CHECKPOINT", "saved checkpoint reached; see steps for prior actions")
            route = self.case["route"]
            if route.startswith("owner_"):
                self.identity("OWNER")
            if route in {"direct", "owner_approve"} and until == "complete":
                self.identity("WAREHOUSE")  # Check before creating a DO.
            blocked = route == "stock_blocked"
            require(
                ("INSUFFICIENT_STOCK" in saved.get("blocking_issues", []))
                if blocked
                else saved["status"] == "READY_FOR_APPROVAL",
                "unexpected saved approval readiness",
            )
            if not blocked:
                require(
                    bool(saved.get("escalation_preview")) == route.startswith("owner_"),
                    "saved escalation does not match planned route",
                )
            response = self.call(
                "approve",
                "CLERK",
                "POST",
                "/orders/" + quote(saved["draft_id"], safe="") + "/approve",
                {"expected_version": saved["version"]},
                expected=(400,) if blocked else ((202,) if route.startswith("owner_") else (200,)),
            )
            delivery = response["body"]
            if blocked:
                require(
                    delivery.get("error_code")
                    in {"DISAMBIGUATION_UNRESOLVED", "INSUFFICIENT_STOCK"},
                    "approval failed for a reason other than stock blocking",
                )
            elif route.startswith("owner_"):
                approval_id = delivery["approval_id"]
                self.state["approval_id"] = approval_id
                approval_path = "/approvals/" + quote(approval_id, safe="")
                detail = self.call("owner_review", "OWNER", "GET", approval_path)["body"]
                require(
                    detail["draft_id"] == saved["draft_id"]
                    and detail["draft_version"] == saved["version"]
                    and detail["status"] == "PENDING",
                    "owner snapshot does not match pending saved version",
                )
                require(detail["approval_id"] == approval_id, "owner approval ID mismatch")
                self.business_lines(detail["snapshot"]["lines"], draft=True)
                delivery = self.call(
                    "owner_decide",
                    "OWNER",
                    "POST",
                    approval_path + "/decide",
                    {
                        "decision": "REJECT" if route == "owner_reject" else "APPROVE",
                        "note": self.case.get("decision_note", "B04 synthetic workflow"),
                    },
                )["body"]
                if route == "owner_reject":
                    require(
                        delivery.get("status") == "REJECTED"
                        and delivery.get("draft_id") == saved["draft_id"]
                        and delivery.get("approval_id") == approval_id
                        and delivery.get("termination_reason") == "OWNER_REJECTED"
                        and delivery.get("decision_note") == self.case["decision_note"]
                        and delivery.get("decided_by") == self.state["identities"]["OWNER"],
                        "rejection result mismatch",
                    )
            has_do = route in {"direct", "owner_approve"}
            if has_do:
                self.state["do_number"] = delivery["do_number"]
                self.verify_do(delivery, saved)
            else:
                require(not delivery.get("do_number"), "rejected/blocked order unexpectedly has DO")
            self.checkpoint()
            if until == "decision":
                raise StopRun("CHECKPOINT", "decision recorded; final reads not complete")
            final = self.call("final_draft", "CLERK", "GET", draft_path)["body"]
            expected_status = (
                "DO_GENERATED" if has_do else ("REJECTED" if not blocked else saved["status"])
            )
            require(
                final["status"] == expected_status
                and final["draft_id"] == saved["draft_id"]
                and final["version"] == saved["version"],
                "final draft state/version mismatch",
            )
            require(
                final.get("do_number") == self.state.get("do_number"), "final DO reference mismatch"
            )
            require(final["ai_mode"] == parsed["ai_mode"], "final historical ai_mode changed")
            if route == "owner_reject":
                require(
                    final.get("termination_reason") == "OWNER_REJECTED",
                    "final rejection termination reason mismatch",
                )
            if has_do:
                do_path = quote(delivery["do_number"], safe="")
                fetched = self.call(
                    "delivery_order", "CLERK", "GET", "/delivery-orders/" + do_path
                )["body"]
                self.verify_do(fetched, saved)
                self.identity("WAREHOUSE")
                warehouse = self.call(
                    "warehouse", "WAREHOUSE", "GET", "/warehouse/delivery-orders/" + do_path
                )["body"]
                require(
                    set(warehouse) <= {"do_number", "customer_name", "items", "approved_at"},
                    "warehouse exposes unexpected top-level fields",
                )
                require(
                    all(
                        set(x) <= {"sku_id", "display_name", "quantity", "unit", "picking_note"}
                        for x in warehouse["items"]
                    ),
                    "warehouse exposes sensitive line fields",
                )
                require(
                    warehouse["do_number"] == delivery["do_number"]
                    and [(x["sku_id"], x["quantity"], x["unit"]) for x in warehouse["items"]]
                    == [(x["sku_id"], x["quantity"], x["unit"]) for x in delivery["lines"]],
                    "warehouse picking differs from DO",
                )
                audit = self.call("audit", "CLERK", "GET", "/orders/" + do_path + "/audit-detail")[
                    "body"
                ]
                require(
                    audit["draft_id"] == saved["draft_id"]
                    and audit["do_number"] == delivery["do_number"],
                    "audit references wrong order",
                )
                self.verify_do(audit["final_snapshot"], saved)
                events = Counter(x["event_type"] for x in audit["events"])
                require(
                    events["INVENTORY_DEDUCT"] == 1
                    and events["APPROVE" if route == "direct" else "DECIDE_APPROVE"] == 1,
                    "missing or duplicate approval/stock audit event",
                )
            activities = self.activity(saved["draft_id"])
            events = Counter(x["event_type"] for x in activities)
            if has_do:
                require(
                    events["INVENTORY_DEDUCTED"] == 1
                    and events["DO_CREATED" if route == "direct" else "OWNER_APPROVED"] == 1,
                    "missing or duplicate workflow activity",
                )
            else:
                require(
                    not events["INVENTORY_DEDUCTED"]
                    and not events["DO_CREATED"]
                    and not events["OWNER_APPROVED"],
                    "rejected/blocked order has approval activity",
                )
                if route == "owner_reject":
                    require(events["OWNER_REJECTED"] == 1, "missing rejection activity")
            self.state.update(
                status="SIMULATED_PASS" if self.mock else "API_PASS",
                reason="HTTP workflow assertions passed",
            )
        except StopRun as exc:
            self.state.update(status=exc.status, reason=exc.reason)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError) as exc:
            self.state.update(
                status="FAIL", reason=f"unexpected response/case shape: {type(exc).__name__}"
            )
        self.checkpoint()
        summary = {k: v for k, v in self.state.items() if k not in {"steps", "pending_request"}}
        write_json(self.path / "summary.json", summary)
        return summary

    def activity(self, draft_id: str) -> list:
        items, cursor, seen = [], None, set()
        for page in range(20):
            path = "/activity?entity_id=" + quote(draft_id, safe="") + "&limit=100"
            if cursor:
                path += "&cursor=" + quote(cursor, safe="")
            result = self.call(f"activity_{page}", "CLERK", "GET", path)["body"]
            items.extend(result["items"])
            cursor = result.get("next_cursor")
            if not cursor:
                return items
            require(cursor not in seen, "activity pagination loop")
            seen.add(cursor)
        raise StopRun("FAIL", "activity pagination exceeded 20 pages; evidence incomplete")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument(
        "--base-url", default=os.environ.get("B04_API_BASE", "http://127.0.0.1:8000/api/v1")
    )
    parser.add_argument("--environment", default=os.environ.get("B04_ENVIRONMENT", ""))
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "b04-runs")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--until", choices=("saved", "decision", "complete"), default="complete")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument(
        "--mock", action="store_true", help="offline synthetic responses; never live evidence"
    )
    parser.add_argument(
        "--plan", action="store_true", help="validate and print plan; no HTTP/files"
    )
    args = parser.parse_args(argv)
    try:
        case = json.loads(args.case.read_text("utf-8-sig"))
        validate_case(case)
        if args.plan:
            print(
                json.dumps(
                    {
                        "case_id": case["case_id"],
                        "route": case["route"],
                        "until": args.until,
                        "planned_ai_modes": case["allowed_ai_modes"],
                        "token_env": case["token_env"],
                        "status": "PLAN_ONLY",
                    },
                    indent=2,
                )
            )
            return 0
        require(not args.resume or bool(args.run_id), "--resume requires --run-id")
        require(args.timeout > 0, "timeout must be positive")
        base, environment, client = args.base_url, args.environment, None
        if args.mock:
            from tools.workflow_mock import mock_client

            base, environment = "http://127.0.0.1:8000/api/v1", "offline-mock"
            client = mock_client(case)
        driver = Driver(
            case,
            base,
            args.out,
            run_id=args.run_id,
            resume=args.resume,
            mock=args.mock,
            timeout=args.timeout,
            client=client,
            environment=environment,
        )
        try:
            result = driver.execute(args.until)
        finally:
            driver.client.close()
        print(f"status={result['status']} case_id={result['case_id']} run_id={result['run_id']}")
        print(f"reason={result['reason']}\nevidence={driver.path}")
        return (
            0
            if result["status"] in {"API_PASS", "SIMULATED_PASS", "CHECKPOINT"}
            else (
                2
                if result["status"] == "BLOCKED"
                else 3
                if result["status"] == "INDETERMINATE"
                else 1
            )
        )
    except StopRun as exc:
        print(f"configuration error: {exc.reason}")
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            f"configuration error: {type(exc).__name__}; "
            "check case, URL, run directory and environment"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
