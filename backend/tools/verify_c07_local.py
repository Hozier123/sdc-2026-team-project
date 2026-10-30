"""C07 only: isolated real HTTP/PostgreSQL duplicate, concurrency and rollback evidence.

Every invocation snapshots the application, creates its own PostgreSQL cluster and
synthetic identities, and stops only the processes it owns. No deployed API,
existing database, role token file, model endpoint or reset command is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
PLAN = {
    "C07-01": "Serial direct approval retry: 200 then 409 ALREADY_APPROVED; no second write",
    "C07-02": "Four simultaneous direct approvals: one 200, three 409; one DO/deduction",
    "C07-03": "Serial owner retry: terminal decision returns 409 ALREADY_APPROVED, no writes",
    "C07-04": "Four owner decisions: one 200, three 409 ALREADY_APPROVED; one DO/deduction",
    "C07-05": "Two drafts competing for last unit: one 200, one 400; stock zero, one DO",
    "C07-06": "Injected failure after DO insertion: 500 with full rollback; clean retry succeeds",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", "utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def environment():
    # Do not inherit database credentials or AI/provider settings into the snapshot.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("AI_", "RUNPOD_", "DATABASE_", "TEST_DATABASE_", "PG", "C07_"))
        and k not in {"PYTHONPATH", "PYTHONHOME"}
    }
    env.update(AI_PROVIDER="stub", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


def snapshot_sources(destination):
    paths = [
        *sorted((ROOT / "backend/app").rglob("*.py")),
        ROOT / "backend/tools/verify_c07_local.py",
        ROOT / "backend/tests/conftest.py",
        ROOT / "backend/tests/test_approval_concurrency.py",
        ROOT / "backend/tests/test_c07_terminal_decisions.py",
        ROOT / "backend/pyproject.toml",
        ROOT / "backend/requirements.lock",
        ROOT / "gate0/docs/gate0-hashes.txt",
        ROOT / "gate0/migrations/0001_baseline.sql",
        *sorted(p for p in (ROOT / "gate0/contracts").rglob("*") if p.is_file()),
    ]
    entries = []
    for path in paths:
        relative = path.relative_to(ROOT)
        raw = path.read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if digest(path) != sha:
            raise RuntimeError(f"Source changed while copying: {relative}")
        entries.append({"path": relative.as_posix(), "size": len(raw), "sha256": sha})
    if any(digest(ROOT / entry["path"]) != entry["sha256"] for entry in entries):
        raise RuntimeError("Source changed during snapshot; retry after the current edit finishes")
    return entries


def serve():
    import uvicorn

    from app.config import Settings
    from app.main import create_app

    url = os.environ["C07_DATABASE_URL"]
    if not url.startswith("postgresql://postgres@127.0.0.1:") or "/c07_" not in url:
        raise ValueError("C07 accepts only its generated loopback database")
    app = create_app(Settings(_env_file=None, database_url=url, ai_provider="stub"))
    if os.environ.get("C07_INJECT_ROLLBACK") == "1":
        import app.approvals as approvals

        def injected_failure(*args, **kwargs):
            raise RuntimeError("C07 test-only failure after DO insert, before inventory deduction")

        approvals._deduct_stock = injected_failure
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["C07_API_PORT"]))


class Probe:
    def __init__(self, url, base, folder, case_id, batch):
        self.url, self.base, self.folder = url, base, folder
        self.case_id = case_id
        self.tenant = case_id.replace("-", "_")
        self.sku, self.customer = "SKU_" + self.tenant, "CUS_" + self.tenant
        self.tokens = {role: "c07-local-only-" + uuid4().hex for role in ("CLERK", "OWNER")}
        self.batch = batch
        self.records = []
        self.checks = {}
        self.snaps = {}
        self.folder.mkdir(parents=True, exist_ok=False)

    def request(self, label, method, path, body=None, role="CLERK", base=None):
        request_id = self.batch + ":" + self.case_id + ":" + label
        started = now()
        clock = time.perf_counter()
        with httpx.Client(timeout=12, trust_env=False) as client:
            response = client.request(
                method,
                (base or self.base) + path,
                json=body,
                headers={
                    "Authorization": "Bearer " + self.tokens[role],
                    "X-Request-ID": request_id,
                },
            )
        record = {
            "label": label,
            "started_at_utc": started,
            "finished_at_utc": now(),
            "elapsed_ms": round((time.perf_counter() - clock) * 1000, 3),
            "request": {
                "method": method,
                "url": str(response.request.url),
                "json": body,
                "actor_user_id": "USR_" + self.tenant + "_" + role,
                "role": role,
                "headers": {
                    "Authorization": "[REDACTED_SYNTHETIC_TOKEN]",
                    "X-Request-ID": request_id,
                },
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json(),
                "raw_text": response.text,
            },
        }
        save(self.folder / "http" / (label + ".json"), record)
        self.records.append(record)
        return record["response"]

    def seed(self):
        from app.auth import hash_token

        tenant, customer, sku = self.tenant, self.customer, self.sku
        family = "FAM_" + tenant
        with psycopg.connect(self.url) as conn:
            conn.execute(
                "INSERT INTO tenants(tenant_id,name,amount_threshold_rm) VALUES(%s,%s,10)",
                (tenant, "C07 synthetic " + tenant),
            )
            for role, token in self.tokens.items():
                conn.execute(
                    "INSERT INTO users(user_id,tenant_id,display_name,demo_token_hash,role) "
                    "VALUES(%s,%s,%s,%s,%s)",
                    ("USR_" + tenant + "_" + role, tenant, "C07 " + role, hash_token(token), role),
                )
            conn.execute(
                "INSERT INTO customers(customer_id,tenant_id,name,tier) VALUES(%s,%s,%s,'A')",
                (customer, tenant, "C07 synthetic customer"),
            )
            conn.execute(
                "INSERT INTO product_families(family_id,tenant_id,family_name) "
                "VALUES(%s,%s,'Milo')",
                (family, tenant),
            )
            conn.execute(
                "INSERT INTO products(product_id,tenant_id,family_id,sku_code,name,base_unit) "
                "VALUES(%s,%s,%s,%s,'C07 Milo 1kg','ctn')",
                (sku, tenant, family, sku),
            )
            conn.execute(
                "INSERT INTO customer_tier_prices(tenant_id,product_id,tier,unit_price_rm) "
                "VALUES(%s,%s,'A',5.00)",
                (tenant, sku),
            )
            conn.execute(
                "INSERT INTO inventory(tenant_id,product_id,available_qty) VALUES(%s,%s,10)",
                (tenant, sku),
            )
        save(
            self.folder / "fixture.json",
            {
                "tenant_id": tenant,
                "customer_id": customer,
                "sku_id": sku,
                "initial_stock": 10,
                "tier_unit_price_rm": "5.00",
                "owner_threshold_rm": "10.00",
                "data_origin": "synthetic C07 fixture, not canonical/shared seed",
            },
        )

    def ready(self, label="draft", qty=1):
        parsed = self.request(
            label + "-parse",
            "POST",
            "/orders/parse-draft",
            {"customer_id": self.customer, "message_text": f"Milo {qty} ctn"},
        )
        assert parsed["status_code"] == 200, parsed
        draft = parsed["body"]["draft_id"]
        saved = self.request(
            label + "-save",
            "PUT",
            f"/orders/drafts/{draft}/lines",
            {
                "expected_version": parsed["body"]["version"],
                "lines": [
                    {
                        "client_line_ref": label,
                        "sku_id": self.sku,
                        "confirmed_qty": qty,
                        "uom": "ctn",
                        "match_source": "MANUAL_SELECTED",
                    }
                ],
            },
        )
        assert saved["status_code"] == 200, saved
        assert saved["body"]["status"] == "READY_FOR_APPROVAL", saved
        assert saved["body"]["version"] == 2, saved
        return draft

    def snapshot(self, label):
        tables = (
            "inventory",
            "orders",
            "draft_versions",
            "delivery_orders",
            "approval_requests",
            "audit_logs",
            "inbound_messages",
            "alias_cache",
        )
        with psycopg.connect(self.url) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            data = {
                table: [
                    row[0]
                    for row in conn.execute(
                        sql.SQL(
                            "SELECT to_jsonb(t) FROM {} t WHERE tenant_id=%s "
                            "ORDER BY to_jsonb(t)::text"
                        ).format(sql.Identifier(table)),
                        (self.tenant,),
                    ).fetchall()
                ]
                for table in tables
            }
        self.snaps[label] = data
        save(self.folder / "db" / (label + ".json"), data)
        return data

    def one_delivery(self, data, qty=1, owner=False):
        counts = Counter(row["action"] for row in data["audit_logs"])
        self.checks.update(
            {
                "one_delivery_order": len(data["delivery_orders"]) == 1,
                "stock_deducted_once": data["inventory"][0]["available_qty"] == 10 - qty,
                "one_deduction_audit": counts["INVENTORY_DEDUCT"] == 1,
                "one_approval_audit": counts["DECIDE_APPROVE" if owner else "APPROVE"] == 1,
                "order_is_do_generated": len(data["orders"]) == 1
                and data["orders"][0]["status"] == "DO_GENERATED",
                "correct_delivery_quantity": len(data["delivery_orders"]) == 1
                and data["delivery_orders"][0]["lines"][0]["quantity"] == qty,
                "correct_delivery_amount": len(data["delivery_orders"]) == 1
                and float(data["delivery_orders"][0]["final_total_rm"]) == 5 * qty,
            }
        )
        approvals = [r for r in data["audit_logs"] if r["action"] in {"APPROVE", "DECIDE_APPROVE"}]
        self.checks["correct_audit_actor"] = len(approvals) == 1 and (
            approvals[0]["actor_user_id"]
            == "USR_" + self.tenant + ("_OWNER" if owner else "_CLERK")
        )
        successes = [
            r["response"]["body"].get("do_number")
            for r in self.records
            if r["response"]["status_code"] == 200
            and r["request"]["method"] == "POST"
            and r["response"]["body"].get("do_number")
        ]
        self.checks["response_do_matches_database"] = len(successes) == 1 and (
            successes[0] == data["delivery_orders"][0]["do_number"]
        )

    def concurrent(self, label, requests, lock_table, lock_key):
        """Hold a real row lock until all HTTP handlers are observed waiting in PG."""
        barrier = Barrier(len(requests))
        telemetry = {
            "started_at_utc": now(),
            "participants": len(requests),
            "lock_table": lock_table,
            "lock_key": lock_key,
            "observations": [],
        }
        holder = psycopg.connect(self.url)
        try:
            key_column = "draft_id" if lock_table == "orders" else "product_id"
            holder.execute(
                sql.SQL("SELECT {} FROM {} WHERE tenant_id=%s AND {}=%s FOR UPDATE").format(
                    sql.Identifier(key_column),
                    sql.Identifier(lock_table),
                    sql.Identifier(key_column),
                ),
                (self.tenant, lock_key),
            ).fetchone()
            telemetry["lock_holder_pid"] = holder.info.backend_pid

            def send(index, spec):
                barrier.wait(timeout=5)
                path, body, role = spec
                return self.request(f"{label}-{index + 1}", "POST", path, body, role)

            with ThreadPoolExecutor(max_workers=len(requests)) as pool:
                futures = [pool.submit(send, i, spec) for i, spec in enumerate(requests)]
                deadline = time.monotonic() + 3.5
                with psycopg.connect(self.url, autocommit=True, row_factory=dict_row) as observer:
                    while time.monotonic() < deadline:
                        rows = observer.execute(
                            "SELECT pid,application_name,state,wait_event_type,wait_event,query,"
                            "pg_blocking_pids(pid) AS blocked_by FROM pg_stat_activity "
                            "WHERE datname=current_database() "
                            "AND application_name='kiraorder-backend' "
                            "AND wait_event_type='Lock' ORDER BY pid"
                        ).fetchall()
                        if rows:
                            telemetry["observations"].append({"at_utc": now(), "sessions": rows})
                        if len(rows) == len(requests):
                            break
                        time.sleep(0.02)
                telemetry["all_requests_waiting_on_database_locks"] = len(rows) == len(requests)
                telemetry["released_at_utc"] = now()
                holder.rollback()
                results = [future.result(timeout=15) for future in futures]
        finally:
            holder.close()
            save(self.folder / (label + "-overlap.json"), telemetry)
        self.checks[label + "_database_overlap_proven"] = telemetry[
            "all_requests_waiting_on_database_locks"
        ]
        return results

    def finish(self):
        self.checks["all_request_ids_echoed"] = all(
            r["request"]["headers"]["X-Request-ID"] == r["response"]["headers"].get("x-request-id")
            for r in self.records
        )
        self.checks["no_unexpected_5xx"] = all(
            r["response"]["status_code"] < 500
            or (
                self.case_id == "C07-06"
                and r["label"] == "injected-failure"
                and r["response"]["status_code"] == 500
            )
            for r in self.records
        )
        self.checks["no_negative_inventory_in_saved_snapshots"] = all(
            row["available_qty"] >= 0 for snap in self.snaps.values() for row in snap["inventory"]
        )
        result = {
            "case_id": self.case_id,
            "description": PLAN[self.case_id],
            "checks": self.checks,
            "status": "PASS" if self.checks and all(self.checks.values()) else "FAIL",
            "http_requests": len(self.records),
            "completed_at_utc": now(),
        }
        save(self.folder / "result.json", result)
        print(json.dumps(result), flush=True)
        return result


def scenarios(url, base, out, batch, fault_base):
    results = []
    for case in PLAN:
        p = Probe(url, base, out / "cases" / case, case, batch)
        p.seed()
        try:
            qty = 3 if case in {"C07-03", "C07-04"} else 1
            draft = p.ready(qty=qty)
            approve = f"/orders/{draft}/approve"
            body = {"expected_version": 2}
            p.snapshot("before")
            if case == "C07-01":
                first = p.request("first-approve", "POST", approve, body)
                initial = p.snapshot("after-first")
                retry = p.request("repeat-approve", "POST", approve, body)
                final = p.snapshot("after-repeat")
                p.checks.update(
                    first_200=first["status_code"] == 200,
                    repeat_409_already_approved=retry["status_code"] == 409
                    and retry["body"].get("error_code") == "ALREADY_APPROVED",
                    retry_changes_nothing=initial == final,
                )
                p.one_delivery(final)
            elif case == "C07-02":
                responses = p.concurrent(
                    "concurrent-approve", [(approve, body, "CLERK")] * 4, "orders", draft
                )
                p.checks["one_200_three_409"] = sorted(r["status_code"] for r in responses) == [
                    200,
                    409,
                    409,
                    409,
                ]
                p.checks["conflicts_are_already_approved"] = all(
                    r["body"].get("error_code") == "ALREADY_APPROVED"
                    for r in responses
                    if r["status_code"] == 409
                )
                p.one_delivery(p.snapshot("after"))
            elif case in {"C07-03", "C07-04"}:
                submitted = p.request("submit-owner", "POST", approve, body)
                assert submitted["status_code"] == 202, submitted
                approval_id = submitted["body"]["approval_id"]
                pending = p.snapshot("pending-owner")
                p.checks["one_pending_no_delivery_no_deduction"] = (
                    len(pending["approval_requests"]) == 1
                    and not pending["delivery_orders"]
                    and pending["inventory"][0]["available_qty"] == 10
                )
                decide = f"/approvals/{approval_id}/decide"
                decision = {
                    "decision": "APPROVE",
                    "note": "C07 synthetic duplicate/concurrency test",
                }
                if case == "C07-03":
                    retry_submit = p.request("repeat-submit", "POST", approve, body)
                    p.checks["submit_retry_409"] = retry_submit["status_code"] == 409 and (
                        retry_submit["body"].get("error_code") == "PENDING_OWNER_APPROVAL"
                    )
                    p.checks["submit_retry_changes_nothing"] = pending == p.snapshot(
                        "after-repeat-submit"
                    )
                    first = p.request("owner-approve", "POST", decide, decision, "OWNER")
                    initial = p.snapshot("after-first-decision")
                    retry = p.request("repeat-owner", "POST", decide, decision, "OWNER")
                    final = p.snapshot("after-repeat-decision")
                    p.checks.update(
                        owner_first_200=first["status_code"] == 200,
                        owner_repeat_409=retry["status_code"] == 409
                        and retry["body"].get("error_code") == "ALREADY_APPROVED",
                        owner_retry_changes_nothing=initial == final,
                    )
                else:
                    responses = p.concurrent(
                        "concurrent-owner", [(decide, decision, "OWNER")] * 4, "orders", draft
                    )
                    p.checks["one_200_three_409"] = sorted(r["status_code"] for r in responses) == [
                        200,
                        409,
                        409,
                        409,
                    ]
                    p.checks["conflicts_are_terminal_approval"] = all(
                        r["body"].get("error_code") == "ALREADY_APPROVED"
                        for r in responses
                        if r["status_code"] == 409
                    )
                    final = p.snapshot("after")
                p.checks["one_approved_request"] = len(final["approval_requests"]) == 1 and (
                    final["approval_requests"][0]["status"] == "APPROVED"
                )
                p.checks["terminal_error_message_is_correct"] = all(
                    "waiting" not in r["response"]["body"].get("message", "").lower()
                    for r in p.records
                    if r["request"]["url"].endswith("/decide")
                    and r["response"]["status_code"] == 409
                )
                p.one_delivery(final, qty=3, owner=True)
            elif case == "C07-05":
                second = p.ready("second")
                with psycopg.connect(url) as conn:
                    conn.execute(
                        "UPDATE inventory SET available_qty=1 WHERE tenant_id=%s AND product_id=%s",
                        (p.tenant, p.sku),
                    )
                p.snapshot("before-race-last-unit")
                responses = p.concurrent(
                    "stock-race",
                    [(approve, body, "CLERK"), (f"/orders/{second}/approve", body, "CLERK")],
                    "inventory",
                    p.sku,
                )
                final = p.snapshot("after")
                counts = Counter(r["action"] for r in final["audit_logs"])
                p.checks.update(
                    one_200_one_400=sorted(r["status_code"] for r in responses) == [200, 400],
                    failure_is_insufficient_stock=all(
                        r["body"].get("error_code") == "INSUFFICIENT_STOCK"
                        for r in responses
                        if r["status_code"] == 400
                    ),
                    final_stock_zero=final["inventory"][0]["available_qty"] == 0,
                    one_delivery=len(final["delivery_orders"]) == 1,
                    one_deduction_audit=counts["INVENTORY_DEDUCT"] == 1,
                    one_approve_audit=counts["APPROVE"] == 1,
                    winner_and_loser_states=sorted(r["status"] for r in final["orders"])
                    == ["DO_GENERATED", "READY_FOR_APPROVAL"],
                )
            else:
                failed = p.request("injected-failure", "POST", approve, body, base=fault_base)
                rolled_back = p.snapshot("after-injected-failure")
                p.checks.update(
                    injected_failure_500=failed["status_code"] == 500,
                    full_transaction_rollback=p.snaps["before"] == rolled_back,
                )
                save(
                    p.folder / "fault-injection.json",
                    {
                        "location": "test runner monkeypatch of app.approvals._deduct_stock",
                        "point": "after real DO insert, before inventory deduction",
                        "dedicated_fault_api": fault_base,
                        "application_source_modified": False,
                    },
                )
                recovered = p.request("clean-retry", "POST", approve, body)
                p.checks["clean_retry_200"] = recovered["status_code"] == 200
                p.one_delivery(p.snapshot("after-clean-retry"))
        except Exception as exc:
            p.checks["scenario_completed"] = False
            save(p.folder / "exception.json", {"type": type(exc).__name__, "message": str(exc)})
        results.append(p.finish())
    return results


def execute(args):
    from app.config import Settings
    from app.migrations import migrate

    out, work, binary = args.run_dir.resolve(), args.work_dir.resolve(), args.postgres_bin.resolve()
    if not (work / "c07-owner.json").is_file():
        raise ValueError("Missing C07 ownership marker")
    summary = json.loads((out / "summary.json").read_text("utf-8"))
    pg_port, api_port, fault_port = free_port(), free_port(), free_port()
    if len({pg_port, api_port, fault_port}) != 3:
        raise RuntimeError("Port allocation collision; no services started")
    database = "c07_" + uuid4().hex[:12]
    url = f"postgresql://postgres@127.0.0.1:{pg_port}/{database}"
    admin_url = f"postgresql://postgres@127.0.0.1:{pg_port}/postgres"
    base = f"http://127.0.0.1:{api_port}/api/v1"
    fault_base = f"http://127.0.0.1:{fault_port}/api/v1"
    summary.update(
        database=database,
        postgres_port=pg_port,
        base_url=base,
        fault_api_url=fault_base,
        started_at_utc=now(),
        execution_source_root=str(ROOT),
    )
    processes, opened = [], []
    pg_attempted = False

    def command_log(label, command, timeout=40):
        with (out / (label + ".log")).open("wb") as log:
            return subprocess.run(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
                timeout=timeout,
                env=environment(),
            ).returncode

    try:
        code = command_log(
            "initdb",
            [
                str(binary / "initdb.exe"),
                "-D",
                str(work / "data"),
                "-U",
                "postgres",
                "--auth=trust",
                "--encoding=EUC_CN",
                "--locale=C",
            ],
        )
        if code:
            raise RuntimeError("C07 initdb failed; inspect initdb.log")
        pg_attempted = True
        code = command_log(
            "postgres-start",
            [
                str(binary / "pg_ctl.exe"),
                "-D",
                str(work / "data"),
                "-l",
                str(out / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {pg_port}",
                "-w",
                "start",
            ],
        )
        if code:
            raise RuntimeError("C07 PostgreSQL startup failed")
        with psycopg.connect(admin_url, autocommit=True) as conn:
            summary["postgres_version"] = conn.execute("SELECT version()").fetchone()[0]
            summary["cluster_encoding"] = conn.execute("SHOW server_encoding").fetchone()[0]
            conn.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(database)
                )
            )
        with psycopg.connect(url) as conn:
            summary["business_database_encoding"] = conn.execute("SHOW server_encoding").fetchone()[
                0
            ]
        migrate(Settings(_env_file=None, database_url=url, ai_provider="stub"))
        for port, fault, label in ((api_port, False, "api"), (fault_port, True, "fault-api")):
            env = environment()
            env.update(
                C07_DATABASE_URL=url, C07_API_PORT=str(port), C07_INJECT_ROLLBACK=str(int(fault))
            )
            log = (out / (label + ".log")).open("wb")
            opened.append(log)
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve"],
                cwd=ROOT / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
            )
            processes.append(proc)
            with httpx.Client(timeout=1, trust_env=False) as client:
                for _ in range(80):
                    if proc.poll() is not None:
                        raise RuntimeError(f"C07 {label} exited during startup")
                    try:
                        response = client.get(f"http://127.0.0.1:{port}/readyz")
                        if response.status_code == 200:
                            save(
                                out / (label + "-readiness.json"),
                                {
                                    "at_utc": now(),
                                    "status_code": 200,
                                    "body": response.json(),
                                    "pid": proc.pid,
                                    "fault_injection": fault,
                                },
                            )
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError(f"C07 {label} not ready")
        summary["results"] = scenarios(url, base, out, summary["batch_id"], fault_base)
        env = environment()
        env["TEST_DATABASE_ADMIN_URL"] = admin_url
        with (out / "existing-concurrency-tests.log").open("wb") as log:
            tested = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_approval_concurrency.py",
                    "--junitxml=" + str(out / "existing-concurrency-tests.xml"),
                    "-o",
                    "cache_dir=" + str(work / "pytest-cache"),
                ],
                cwd=ROOT / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
                timeout=60,
            )
        summary["existing_concurrency_tests_exit_code"] = tested.returncode
        with (out / "terminal-decision-regression.log").open("wb") as log:
            terminal_tests = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_c07_terminal_decisions.py",
                    "--junitxml=" + str(out / "terminal-decision-regression.xml"),
                    "-o",
                    "cache_dir=" + str(work / "pytest-cache"),
                ],
                cwd=ROOT / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
                timeout=60,
            )
        summary["terminal_decision_regression_exit_code"] = terminal_tests.returncode
        manifest = json.loads((out / "source-manifest.json").read_text("utf-8"))
        summary["source_snapshot_unchanged"] = all(
            digest(ROOT / item["path"]) == item["sha256"] for item in manifest["files"]
        )
        summary["status"] = (
            "PASS"
            if (
                all(r["status"] == "PASS" for r in summary["results"])
                and tested.returncode == 0
                and terminal_tests.returncode == 0
                and summary["source_snapshot_unchanged"]
            )
            else "FAIL"
        )
    except Exception as exc:
        summary.update(status="SETUP_OR_RUN_FAILED", error_type=type(exc).__name__, error=str(exc))
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        for log in opened:
            log.close()
        summary["owned_apis_stopped"] = all(proc.poll() is not None for proc in processes)
        if pg_attempted:
            stopped = command_log(
                "postgres-stop",
                [str(binary / "pg_ctl.exe"), "-D", str(work / "data"), "-m", "fast", "-w", "stop"],
            )
            summary["owned_postgres_stopped"] = stopped == 0
        summary["completed_at_utc"] = now()
        if summary["status"] == "PASS" and not (
            summary["owned_apis_stopped"] and summary.get("owned_postgres_stopped")
        ):
            summary["status"] = "CLEANUP_FAILED"
        summary["independent_review"] = "PENDING_ZHOU"
        save(out / "summary.json", summary)
        print(
            json.dumps(
                {"status": summary["status"], "evidence": str(out), "error": summary.get("error")}
            ),
            flush=True,
        )
    return 0 if summary["status"] == "PASS" else 1


def prepare(args):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch = "c07-" + stamp + "-" + uuid4().hex[:6]
    out = args.output.resolve() / batch
    out.mkdir(parents=True, exist_ok=False)
    work = ROOT.parent / ".tmp" / batch
    work.mkdir(parents=True, exist_ok=False)
    save(work / "c07-owner.json", {"batch_id": batch, "purpose": "C07 ONLY"})
    for name in ("postgres.exe", "initdb.exe", "pg_ctl.exe"):
        if not (args.postgres_bin / name).is_file():
            raise ValueError("PostgreSQL executable missing: " + name)
    source = out / "source"
    entries = snapshot_sources(source)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    changed = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True)
    save(
        out / "source-manifest.json",
        {
            "captured_at_utc": now(),
            "original_repo": str(ROOT),
            "git_head_reference_only": head.stdout.strip(),
            "git_status_at_capture": changed.stdout.splitlines(),
            "files": entries,
            "binding": "Byte-hashed source snapshot including current uncommitted files",
        },
    )
    save(
        out / "test-plan.json",
        {
            "frozen_before_execution_at_utc": now(),
            "cases": PLAN,
            "overlap_requirement": "All concurrent handlers observed waiting on PG locks",
            "ai_scope": "Stub parse, manual SKU/quantity save; no model-quality claim",
            "retry_semantics": "Duplicate writes rejected with 409; no same-key 200 replay claim",
            "independent_review": "He execution, Zhou independent acceptance pending",
        },
    )
    save(
        out / "summary.json",
        {
            "batch_id": batch,
            "status": "RUNNING",
            "scope": "C07_ONLY_LOCAL_HTTP_AND_POSTGRESQL",
            "python_version": sys.version,
            "python_executable": sys.executable,
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("fastapi", "psycopg", "httpx", "pytest", "uvicorn")
            },
            "gpu_calls": 0,
            "remote_mutations": 0,
            "existing_database_resets": 0,
            "execution_source": "immutable copied application files, not current git HEAD alone",
        },
    )
    command = [
        sys.executable,
        str(source / "backend/tools/verify_c07_local.py"),
        "--execute",
        "--postgres-bin",
        str(args.postgres_bin.resolve()),
        "--run-dir",
        str(out),
        "--work-dir",
        str(work),
    ]
    with (out / "runner.log").open("wb") as log:
        run = subprocess.run(
            command,
            cwd=source / "backend",
            env=environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=FLAGS,
            timeout=180,
        )
    print(json.dumps({"exit_code": run.returncode, "evidence": str(out)}), flush=True)
    return run.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--execute", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.serve:
        serve()
    elif options.execute:
        sys.exit(execute(options))
    elif options.postgres_bin and options.output:
        sys.exit(prepare(options))
    else:
        parser.error("Provide --postgres-bin and --output")
