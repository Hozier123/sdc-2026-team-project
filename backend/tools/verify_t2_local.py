"""Run B04 T2 DEV cases on a newly created loopback PostgreSQL/API; never reset a database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
NAMES = ("direct", "owner-approve", "owner-reject", "stock-blocked")
SKU = "SKU_PENCUCI_1L"


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", "utf-8")


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def source_hashes() -> dict[str, str]:
    files = [
        *sorted((ROOT / "backend/app").rglob("*.py")),
        ROOT / "backend/tools/run_workflow.py",
        ROOT / "backend/tools/verify_t2_local.py",
        ROOT / "data/seed/SEED_MANIFEST.json",
        ROOT / "data/seed/T1_seed.sql",
        ROOT / "data/seed/T2_seed.sql",
        *(ROOT / f"docs/ops/b04-cases/t2-{name}.json" for name in NAMES),
    ]
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def serve() -> None:
    import uvicorn

    from app.ai.adapter import OrderAiAdapter
    from app.ai.extractor import RunPodExtractor
    from app.config import Settings
    from app.extraction.runpod_adapter import RunPodAdapterProvider
    from app.main import create_app

    url = os.environ["B04_T2_LOCAL_DATABASE_URL"]
    if not url.startswith("postgresql://postgres@127.0.0.1:"):
        raise ValueError("Only the runner's loopback database is allowed")
    settings = Settings(_env_file=None, database_url=url, ai_provider="stub")
    app = create_app(settings)
    extractor = RunPodExtractor()
    if extractor.api_key or extractor.api_url:
        raise ValueError("Local fallback verification must have no model credentials or endpoint")
    app.state.extraction_provider = RunPodAdapterProvider(OrderAiAdapter(extractor=extractor))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["B04_T2_LOCAL_API_PORT"]))


def snapshot(url: str, tenant: str, draft: str | None = None) -> dict:
    with psycopg.connect(url, connect_timeout=5) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout='5s'")
        stock = dict(
            conn.execute(
                "SELECT product_id,available_qty FROM inventory "
                "WHERE tenant_id=%s ORDER BY product_id",
                (tenant,),
            ).fetchall()
        )
        if draft is None:
            aliases = conn.execute(
                "SELECT alias_id,phrase,target_type,family_id,product_id,active "
                "FROM alias_cache WHERE tenant_id=%s ORDER BY alias_id",
                (tenant,),
            ).fetchall()
            orders = conn.execute(
                "SELECT draft_id,status,version FROM orders WHERE tenant_id=%s ORDER BY draft_id",
                (tenant,),
            ).fetchall()
            return {"inventory": stock, "aliases": aliases, "orders": orders}
        dos = conn.execute(
            "SELECT do_number,final_total_rm,approval_mode FROM delivery_orders "
            "WHERE tenant_id=%s AND draft_id=%s ORDER BY do_number",
            (tenant, draft),
        ).fetchall()
        audits = conn.execute(
            "SELECT action,actor_role FROM audit_logs WHERE tenant_id=%s AND draft_id=%s "
            "ORDER BY action,actor_role",
            (tenant, draft),
        ).fetchall()
        approvals = conn.execute(
            "SELECT approval_id,status FROM approval_requests WHERE tenant_id=%s AND draft_id=%s",
            (tenant, draft),
        ).fetchall()
        state = conn.execute(
            "SELECT status,version FROM orders WHERE tenant_id=%s AND draft_id=%s",
            (tenant, draft),
        ).fetchone()
    return {
        "inventory": stock,
        "delivery_orders": dos,
        "audit_rows": audits,
        "approvals": approvals,
        "order_state": state,
    }


def verify_db(case: dict, result: dict, before: dict, after: dict) -> dict:
    success = case["route"] in {"direct", "owner_approve"}
    delta = {
        key: before[key] - after["inventory"][key]
        for key in before
        if before[key] != after["inventory"][key]
    }
    expected_delta = {SKU: 2} if success else {}
    counts = Counter(row[0] for row in after["audit_rows"])
    checks = {
        "all_16_sku_stock_delta": delta == expected_delta,
        "delivery_count": len(after["delivery_orders"]) == int(success),
        "deduction_audit_count": counts["INVENTORY_DEDUCT"] == int(success),
        "direct_audit_count": counts["APPROVE"] == int(case["route"] == "direct"),
        "owner_approve_audit_count": counts["DECIDE_APPROVE"]
        == int(case["route"] == "owner_approve"),
        "owner_reject_audit_count": counts["DECIDE_REJECT"] == int(case["route"] == "owner_reject"),
        "driver_business_pass": result["status"] == "API_PASS",
        "actual_mode_is_fallback": result.get("actual_ai_mode") == "FALLBACK",
    }
    if case["route"].startswith("owner_"):
        terminal = "REJECTED" if case["route"] == "owner_reject" else "APPROVED"
        checks["owner_terminal_state"] = (
            len(after["approvals"]) == 1 and after["approvals"][0][1] == terminal
        )
    return {
        "inventory_before": before,
        "after": after,
        "stock_delta": delta,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def run(postgres_bin: Path, tokens_file: Path, cluster_encoding: str = "UTF8") -> bool:
    from app.config import Settings
    from app.migrations import migrate
    from app.seed import load_seed
    from tools.run_workflow import Driver

    if cluster_encoding not in {"UTF8", "EUC_CN"}:
        raise ValueError("Unsupported isolated cluster encoding")
    binary = postgres_bin.resolve()
    for executable in ("postgres.exe", "initdb.exe", "pg_ctl.exe"):
        if not (binary / executable).is_file():
            raise ValueError("Provide the existing PostgreSQL Windows bin directory")
    batch = (
        "b04-t2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:6]
    )
    work = (ROOT / ".tmp" / batch).resolve()
    if not work.is_relative_to((ROOT / ".tmp").resolve()):
        raise ValueError("Invalid local work directory")
    work.mkdir(parents=True, exist_ok=False)
    out = ROOT / "evidence/b04-runs" / batch
    out.mkdir(parents=True, exist_ok=False)
    pg_port, api_port = port(), port()
    while pg_port == api_port:
        api_port = port()
    database = "kira_b04_t2_" + uuid4().hex[:12]
    url = f"postgresql://postgres@127.0.0.1:{pg_port}/{database}"
    base_url = f"http://127.0.0.1:{api_port}/api/v1"
    tokens = json.loads(tokens_file.read_text("utf-8-sig"))
    original_env = {
        f"B04_T2_{role}_TOKEN": os.environ.get(f"B04_T2_{role}_TOKEN")
        for role in ("CLERK", "OWNER", "WAREHOUSE")
    }
    for role in ("CLERK", "OWNER", "WAREHOUSE"):
        os.environ[f"B04_T2_{role}_TOKEN"] = tokens["T2"][f"USR_T2_{role}"]
    manifest = json.loads((ROOT / "data/seed/SEED_MANIFEST.json").read_text("utf-8"))
    initial_sources = source_hashes()
    metadata = {
        "batch_id": batch,
        "scope": "LOCAL_ISOLATED_REAL_HTTP_AND_POSTGRESQL",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "database": database,
        "database_host": "127.0.0.1",
        "database_port": pg_port,
        "cluster_path": str(work / "data"),
        "source_hashes": initial_sources,
        "mock_transport": False,
        "gpu_calls": 0,
        "remote_mutations": 0,
        "reset_performed": False,
        "requested_cluster_encoding": cluster_encoding,
        "requested_business_database_encoding": "UTF8",
        "results": [],
        "status": "RUNNING",
    }
    save(out / "batch-summary.json", metadata)
    server, started = None, False
    try:
        with (work / "initdb.log").open("wb") as log:
            init = subprocess.run(
                [
                    str(binary / "initdb.exe"),
                    "-D",
                    str(work / "data"),
                    "-U",
                    "postgres",
                    "--auth=trust",
                    f"--encoding={cluster_encoding}",
                    "--locale=C",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
                timeout=30,
            )
        if init.returncode:
            raise RuntimeError("Fresh local initdb failed; see the local log")
        with (work / "startup.log").open("wb") as log:
            control = subprocess.run(
                [
                    str(binary / "pg_ctl.exe"),
                    "-D",
                    str(work / "data"),
                    "-l",
                    str(work / "postgres.log"),
                    "-o",
                    f"-h 127.0.0.1 -p {pg_port}",
                    "-w",
                    "start",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
                timeout=25,
            )
        if control.returncode:
            raise RuntimeError("Fresh local PostgreSQL did not start")
        started = True
        with psycopg.connect(
            f"postgresql://postgres@127.0.0.1:{pg_port}/postgres", autocommit=True
        ) as conn:
            conn.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(database)
                )
            )
            metadata["actual_cluster_encoding"] = conn.execute("SHOW server_encoding").fetchone()[0]
        with psycopg.connect(url) as conn:
            metadata["actual_business_database_encoding"] = conn.execute(
                "SHOW server_encoding"
            ).fetchone()[0]
            if metadata["actual_business_database_encoding"] != "UTF8":
                raise ValueError("The business database must use UTF8")
        settings = Settings(_env_file=None, database_url=url)
        migrate(settings)
        for tenant in ("T1", "T2"):
            seed = manifest["tenants"][tenant]
            load_seed(
                settings,
                tenant=tenant,
                seed_path=ROOT / f"data/seed/{tenant}_seed.sql",
                seed_version=seed["seed_version"],
                expect_sha256=seed["sql_sha256"],
                expect_products=seed["products"],
                expect_inventory=seed["inventory_sum"],
            )
        with psycopg.connect(url) as conn:
            users = conn.execute("SELECT tenant_id,user_id,demo_token_hash FROM users").fetchall()
        if not all(
            hashlib.sha256(tokens[t][user].encode()).hexdigest() == hashed
            for t, user, hashed in users
        ):
            raise ValueError("Private role sessions do not match canonical seed hashes")
        protected = snapshot(url, "T1")
        save(out / "t1-baseline.json", protected)
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("RUNPOD_", "AI_"))
        }
        env.update(B04_T2_LOCAL_DATABASE_URL=url, B04_T2_LOCAL_API_PORT=str(api_port))
        with (work / "api.log").open("wb") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "tools.verify_t2_local", "--serve"],
                env=env,
                cwd=ROOT / "backend",
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=FLAGS,
            )
        with httpx.Client(timeout=1, trust_env=False) as client:
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError("Local API exited before readiness")
                try:
                    if client.get(base_url.removesuffix("/api/v1") + "/readyz").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError("Local API did not become ready")
        for name in NAMES:
            case = json.loads((ROOT / f"docs/ops/b04-cases/t2-{name}.json").read_text("utf-8"))
            before = snapshot(url, "T2")["inventory"]
            driver = Driver(case, base_url, out, run_id=name, environment=batch)
            try:
                result = driver.execute()
            finally:
                driver.client.close()
            probe = verify_db(case, result, before, snapshot(url, "T2", result.get("draft_id")))
            probe["checks"]["t1_unchanged"] = snapshot(url, "T1") == protected
            probe["status"] = "PASS" if all(probe["checks"].values()) else "FAIL"
            save(driver.path / "database-verification.json", probe)
            entry = {
                "case_id": case["case_id"],
                "run_id": name,
                "status": result["status"],
                "db_status": probe["status"],
                "stock_delta": probe["stock_delta"],
                "draft_id": result.get("draft_id"),
                "do_number": result.get("do_number"),
                "actual_ai_mode": result.get("actual_ai_mode"),
                "reason": result["reason"],
            }
            metadata["results"].append(entry)
            save(out / "batch-summary.json", metadata)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            if name == "direct" and result["status"] == "API_PASS":
                before_retry = snapshot(url, "T2", result["draft_id"])
                paths = [
                    (
                        "repeat_approval",
                        "POST",
                        f"/orders/{result['draft_id']}/approve",
                        tokens["T2"]["USR_T2_CLERK"],
                        {"expected_version": driver.state["draft_version"]},
                        409,
                    ),
                    (
                        "t1_cannot_read_t2_draft",
                        "GET",
                        f"/orders/drafts/{result['draft_id']}",
                        tokens["T1"]["USR_T1_CLERK"],
                        None,
                        404,
                    ),
                    (
                        "t1_cannot_read_t2_warehouse",
                        "GET",
                        f"/warehouse/delivery-orders/{result['do_number']}",
                        tokens["T1"]["USR_T1_WAREHOUSE"],
                        None,
                        404,
                    ),
                ]
                extra = []
                with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
                    for label, method, path, token, body, expected in paths:
                        sent_id = "b04-t2-" + uuid4().hex
                        response = client.request(
                            method,
                            base_url + path,
                            json=body,
                            headers={"Authorization": "Bearer " + token, "X-Request-ID": sent_id},
                        )
                        payload = response.json()
                        extra.append(
                            {
                                "name": label,
                                "method": method,
                                "path": path,
                                "status_code": response.status_code,
                                "body": payload,
                                "sent_request_id": sent_id,
                                "request_id": response.headers.get("X-Request-ID"),
                                "status_matches": response.status_code == expected,
                            }
                        )
                retry_unchanged = before_retry == snapshot(url, "T2", result["draft_id"])
                extra_checks = {
                    "all_http_statuses_match": all(item["status_matches"] for item in extra),
                    "all_request_ids_returned": all(item["request_id"] for item in extra),
                    "repeat_is_already_approved": extra[0]["body"].get("error_code")
                    == "ALREADY_APPROVED",
                    "repeat_does_not_change_stock_do_or_audit": retry_unchanged,
                    "t1_unchanged": snapshot(url, "T1") == protected,
                }
                metadata["additional_checks"] = {
                    "scope": "serial duplicate approval and tenant reads; no concurrency/reset",
                    "requests": extra,
                    "checks": extra_checks,
                    "status": "PASS" if all(extra_checks.values()) else "FAIL",
                }
                save(out / "duplicate-and-tenant-checks.json", metadata["additional_checks"])
        metadata["source_files_unchanged_during_run"] = source_hashes() == initial_sources
        passed = all(
            item["status"] == "API_PASS" and item["db_status"] == "PASS"
            for item in metadata["results"]
        )
        passed &= metadata.get("additional_checks", {}).get("status") == "PASS"
        passed &= metadata["source_files_unchanged_during_run"]
        metadata["status"] = "PASS" if passed else "FAIL"
    except Exception as exc:
        metadata.update(status="SETUP_OR_RUN_FAILED", error_type=type(exc).__name__)
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            server.wait(timeout=10)
        if started:
            with (work / "shutdown.log").open("wb") as log:
                stopped = subprocess.run(
                    [
                        str(binary / "pg_ctl.exe"),
                        "-D",
                        str(work / "data"),
                        "-m",
                        "fast",
                        "-w",
                        "stop",
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=FLAGS,
                    timeout=25,
                )
            metadata["isolated_postgres_stopped"] = stopped.returncode == 0
        metadata["isolated_api_stopped"] = server is None or server.poll() is not None
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        metadata["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        save(out / "batch-summary.json", metadata)
        print(
            json.dumps(
                {
                    "batch_status": metadata["status"],
                    "evidence": str(out),
                    "error_type": metadata.get("error_type"),
                }
            ),
            flush=True,
        )
    return metadata["status"] == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("--tokens-file", type=Path)
    parser.add_argument("--cluster-encoding", choices=("UTF8", "EUC_CN"), default="UTF8")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.serve:
        serve()
    elif args.postgres_bin and args.tokens_file:
        try:
            raise SystemExit(
                0 if run(args.postgres_bin, args.tokens_file, args.cluster_encoding) else 1
            )
        except Exception as exc:
            print(json.dumps({"status": "SETUP_FAILED", "error_type": type(exc).__name__}))
            raise SystemExit(2) from None
    else:
        parser.error("--postgres-bin and --tokens-file are required for a fresh local run")
