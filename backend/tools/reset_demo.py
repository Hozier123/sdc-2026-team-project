"""Rebuild the T1 trial database from a version-pinned template (Gate 0 plan A).

Why a database-level rebuild instead of DELETE:
    Six of the eight runtime tables are append-only/immutable in the frozen DDL
    (``draft_versions``, ``delivery_orders``, ``activity_log``, ``audit_logs``,
    ``field_diffs`` and ``approval_requests``). A row-level reset is impossible
    without changing Gate 0, so the trial database is recreated from a template.

What one ``--apply`` does:
    1. preflight  - template exists, is the pinned seed version, has 18 tables
    2. evidence   - export the finished order's DO text plus audit/field-diff
                    summaries, because the rebuild also discards the audit trail
    3. rebuild    - DROP/CREATE the target database from the template
    4. verify     - 18 tables, ledger hash, inventory 40/795, alias_cache 2,
                    no runtime rows left
    5. hook       - optional command to restart API/AI and refresh clients

The stopwatch must be stopped before this command and started again after the
hook returns; the rebuild and cold start are never part of a measured order.

Usage (from ``backend/``):
    python -m tools.reset_demo --dry-run
    python -m tools.reset_demo --apply \\
        --expect-seed-version T1-0.1 --expect-seed-sha256 <sha256> \\
        --hook "powershell -ExecutionPolicy Bypass -File ../scripts/restart-demo.ps1"

Template creation (after Zhou re-freezes the canonical T1 seed):
    python -m tools.reset_demo --init-template --seed-sql ../data/seed/seed_T1.sql \\
        --seed-version T1-0.1 --seed-sha256 <sha256>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4

import psycopg
from psycopg import sql as pgsql
from psycopg.conninfo import conninfo_to_dict

from app.config import REPO_ROOT, Settings
from app.migrations import HASH_LIST_SHA256, SQL_SHA256, VERSION, migrate, verify_schema
from app.seed import SeedError, validate_data_only_sql

DEFAULT_TEMPLATE = "kiraorder_t1_seed"
DEFAULT_TARGET = "kiraorder_trial"
SAFE_TARGET = re.compile(r"^kiraorder_(trial|demo)[a-z0-9_]*$")
SAFE_TEMPLATE = re.compile(r"^kiraorder_[a-z0-9_]*(seed|tpl|template)[a-z0-9_]*$")
FLOW_TABLES = (
    "inbound_messages",
    "orders",
    "draft_versions",
    "delivery_orders",
    "activity_log",
    "audit_logs",
    "field_diffs",
)
# field_diffs has no tenant_id; it is scoped through its audit_logs parent.
FLOW_COUNT_SQL = {
    "field_diffs": (
        "SELECT count(*) FROM field_diffs f "
        "JOIN audit_logs a ON a.audit_id = f.audit_id WHERE a.tenant_id = %s"
    ),
}
FORBIDDEN_DATABASES = {"postgres", "template0", "template1"}
SEED_MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS kiraorder_meta.seed_manifest (
    tenant_id       text PRIMARY KEY,
    seed_version    text NOT NULL,
    seed_sha256     text NOT NULL,
    product_count   integer NOT NULL,
    inventory_total integer NOT NULL,
    family_count    integer NOT NULL,
    customer_count  integer NOT NULL,
    price_count     integer NOT NULL,
    price_total_a   numeric(12,2) NOT NULL,
    price_total_b   numeric(12,2) NOT NULL,
    seed_content_sha256 text NOT NULL,
    applied_at      timestamptz NOT NULL DEFAULT now()
)
"""


class ResetError(Exception):
    """A controlled failure that is safe to show to the operator."""


@dataclass
class Report:
    action: str
    template: str
    target: str
    tenant: str
    started_at: str
    checks: dict[str, Any] = field(default_factory=dict)
    evidence_files: list[str] = field(default_factory=list)
    hook_exit_code: int | None = None
    status: str = "pending"
    error: str | None = None


def utc_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")


def connect_admin(url: str) -> psycopg.Connection:
    try:
        return psycopg.connect(url, autocommit=True, connect_timeout=5)
    except psycopg.Error as exc:
        raise ResetError(
            f"cannot connect with RESET_ADMIN_DATABASE_URL (SQLSTATE {exc.sqlstate})"
        ) from None


def with_dbname(url: str, dbname: str) -> str:
    """Return a PostgreSQL URI pointing at ``dbname`` on the same server.

    ``make_conninfo`` returns a libpq keyword string, which the backend's
    ``Settings`` rejects because it requires a ``postgresql://`` URI.
    """
    parts = conninfo_to_dict(url)
    credentials = quote(parts.get("user", "postgres"), safe="")
    if parts.get("password"):
        credentials += ":" + quote(parts["password"], safe="")
    host = parts.get("host", "127.0.0.1")
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    port = parts.get("port", "5432")
    options = {
        k: v for k, v in parts.items() if k not in {"user", "password", "host", "port", "dbname"}
    }
    suffix = "?" + urlencode(options) if options else ""
    return f"postgresql://{credentials}@{host}:{port}/{quote(dbname, safe='')}{suffix}"


def database_exists(admin: psycopg.Connection, name: str) -> bool:
    row = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
    return row is not None


def ensure_safe_names(target: str, template: str, allow_any_target: bool) -> None:
    if not all(re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value) for value in (target, template)):
        raise ResetError("database names must be safe lowercase identifiers")
    if target == template:
        raise ResetError("target and template must differ")
    if target in FORBIDDEN_DATABASES or template in FORBIDDEN_DATABASES:
        raise ResetError("refusing to touch a PostgreSQL system database")
    if not SAFE_TEMPLATE.match(template):
        raise ResetError(f"template name {template!r} does not look like a KiraOrder seed template")
    if not allow_any_target and not SAFE_TARGET.match(target):
        raise ResetError(f"target name {target!r} is not a KiraOrder trial database")


def read_seed_manifest(conn: psycopg.Connection, tenant: str) -> dict[str, Any] | None:
    exists = conn.execute("SELECT to_regclass('kiraorder_meta.seed_manifest')").fetchone()[0]
    if exists is None:
        return None
    row = conn.execute(
        "SELECT to_jsonb(m) FROM kiraorder_meta.seed_manifest m WHERE tenant_id=%s", (tenant,)
    ).fetchone()
    if row is None:
        return None
    manifest = row[0]
    if not manifest.get("seed_content_sha256"):
        raise ResetError("legacy template lacks row-level digest; create a new versioned template")
    for key in ("price_total_a", "price_total_b"):
        manifest[key] = f"{manifest[key]:.2f}"
    return manifest


def seed_content_hash(conn, tenant):
    """Detect compensating changes that leave aggregate counts/sums unchanged."""
    tables = (
        "tenants",
        "users",
        "customers",
        "product_families",
        "family_aliases",
        "products",
        "uom_aliases",
        "customer_tier_prices",
        "inventory",
        "alias_cache",
    )
    snapshot = {}
    for table in tables:
        rows = conn.execute(
            pgsql.SQL(
                "SELECT to_jsonb(t) - 'created_at' - 'updated_at' FROM {} t WHERE tenant_id=%s"
            ).format(pgsql.Identifier(table)),
            (tenant,),
        ).fetchall()
        snapshot[table] = sorted(
            json.dumps(row[0], sort_keys=True, ensure_ascii=False) for row in rows
        )
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def seed_snapshot(conn: psycopg.Connection, tenant: str) -> dict[str, Any]:
    """Read every value the trial depends on, not just inventory.

    The manifest proves "the file did not change"; this snapshot proves "the
    values in this database are the frozen ones". A price typo passes an
    inventory-only check, so prices, families and customers are read here too.
    """
    row = conn.execute(
        "SELECT "
        " (SELECT count(*) FROM products WHERE tenant_id = %s),"
        " (SELECT count(*) FROM product_families WHERE tenant_id = %s),"
        " (SELECT count(*) FROM customers WHERE tenant_id = %s),"
        " (SELECT count(*) FROM customer_tier_prices WHERE tenant_id = %s),"
        " (SELECT coalesce(sum(unit_price_rm) FILTER (WHERE tier = 'A'), 0)"
        "  FROM customer_tier_prices WHERE tenant_id = %s)::numeric(12,2)::text,"
        " (SELECT coalesce(sum(unit_price_rm) FILTER (WHERE tier = 'B'), 0)"
        "  FROM customer_tier_prices WHERE tenant_id = %s)::numeric(12,2)::text,"
        " (SELECT count(*) FROM inventory WHERE tenant_id = %s),"
        " (SELECT coalesce(sum(available_qty), 0)::int FROM inventory WHERE tenant_id = %s),"
        " (SELECT count(*) FROM ("
        "   SELECT product_id FROM customer_tier_prices WHERE tenant_id = %s"
        "   GROUP BY product_id HAVING count(*) <> 2) tier_check)",
        (tenant,) * 9,
    ).fetchone()
    return {
        "product_count": int(row[0]),
        "family_count": int(row[1]),
        "customer_count": int(row[2]),
        "price_count": int(row[3]),
        "price_total_a": row[4],
        "price_total_b": row[5],
        "inventory_rows": int(row[6]),
        "inventory_total": int(row[7]),
        "products_without_two_tiers": int(row[8]),
    }


def expected_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "product_count": args.expect_products,
        "family_count": args.expect_families,
        "customer_count": args.expect_customers,
        "price_count": args.expect_prices,
        "price_total_a": args.expect_price_a,
        "price_total_b": args.expect_price_b,
        "inventory_rows": args.expect_products,
        "inventory_total": args.expect_inventory,
        "products_without_two_tiers": 0,
    }


def snapshot_differences(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    return [
        f"{key}: actual {actual.get(key)!r} != expected {value!r}"
        for key, value in expected.items()
        if actual.get(key) != value
    ]


def check_template(args: argparse.Namespace, admin: psycopg.Connection) -> dict[str, Any]:
    if not database_exists(admin, args.template):
        raise ResetError(
            f"template database {args.template!r} does not exist; run --init-template first"
        )

    url = with_dbname(args.admin_url, args.template)
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        verify_schema(conn)  # 18 public tables, 6 triggers, 12 events, unique indexes
        manifest = read_seed_manifest(conn, args.tenant)
        if manifest is None:
            raise ResetError("template has no seed manifest; rebuild it with --init-template")
        if manifest["seed_version"] != args.expect_seed_version:
            raise ResetError(
                "template seed version "
                f"{manifest['seed_version']!r} != expected {args.expect_seed_version!r}"
            )
        if manifest["seed_sha256"].lower() != args.expect_seed_sha256.lower():
            raise ResetError("template seed sha256 does not match --expect-seed-sha256")
        snapshot = seed_snapshot(conn, args.tenant)

        if seed_content_hash(conn, args.tenant) != manifest["seed_content_sha256"]:
            raise ResetError("template row-level seed content digest mismatch")
        if conn.execute("SELECT count(*) FROM tenants").fetchone()[0] != 1:
            raise ResetError("trial template must contain only the selected tenant")

    # The manifest is only a "file unchanged" witness; the expectations come
    # from products.csv, so a drifted value cannot certify itself.
    manifest_expected = {key: manifest[key] for key in snapshot if key in manifest}
    manifest_drift = snapshot_differences(snapshot, manifest_expected)
    if manifest_drift:
        raise ResetError(f"template drifted from its manifest: {manifest_drift}")

    differences = snapshot_differences(snapshot, expected_snapshot(args))
    if differences:
        raise ResetError(f"template values do not match products.csv: {differences}")

    # All checks must run BEFORE a destructive rebuild, not only afterwards.
    template_args = argparse.Namespace(**vars(args))
    template_args.target = args.template
    verify_target(template_args)
    return {"manifest": manifest, "snapshot": snapshot}


def collect_evidence(url: str, tenant: str) -> dict[str, Any]:
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        counts = {
            table: int(
                conn.execute(
                    FLOW_COUNT_SQL.get(table, f"SELECT count(*) FROM {table} WHERE tenant_id = %s"),
                    (tenant,),
                ).fetchone()[0]
            )
            for table in FLOW_TABLES + ("approval_requests",)
        }
        orders = conn.execute(
            "SELECT to_jsonb(d) FROM delivery_orders d WHERE tenant_id = %s ORDER BY approved_at",
            (tenant,),
        ).fetchall()
        audits = conn.execute(
            "SELECT audit_id, draft_id, draft_version, do_number, actor_role, action, created_at "
            "FROM audit_logs WHERE tenant_id = %s ORDER BY created_at",
            (tenant,),
        ).fetchall()
        diffs = conn.execute(
            "SELECT to_jsonb(f) FROM field_diffs f "
            "JOIN audit_logs a ON a.audit_id = f.audit_id WHERE a.tenant_id = %s",
            (tenant,),
        ).fetchall()

    return {
        "tenant_id": tenant,
        "exported_at": datetime.now().astimezone().isoformat(),
        "row_counts": counts,
        "delivery_orders": [row[0] for row in orders],
        "audit_logs": [
            {
                "audit_id": row[0],
                "draft_id": row[1],
                "draft_version": row[2],
                "do_number": row[3],
                "actor_role": row[4],
                "action": row[5],
                "created_at": row[6].isoformat(),
            }
            for row in audits
        ],
        "field_diffs": [row[0] for row in diffs],
    }


def write_evidence(
    evidence_dir: Path, stamp: str, target: str, payload: dict[str, Any]
) -> list[str]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    base = f"reset_{target}_{stamp}"
    json_path = evidence_dir / f"{base}.json"
    md_path = evidence_dir / f"{base}.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    counts = payload["row_counts"]
    lines = [
        f"# 试次证据导出（{target}）",
        "",
        f"- 租户：`{payload['tenant_id']}`",
        f"- 导出时间：{payload['exported_at']}",
        "- 目的：库级重建会连同审计一起清除，本文件是重建前的唯一证据",
        "",
        "## 行数",
        "",
        "| 表 | 行数 |",
        "|---|---:|",
        *[f"| `{name}` | {value} |" for name, value in counts.items()],
        "",
        f"## DO 原文（{len(payload['delivery_orders'])} 条）",
        "",
        "见同名 `.json` 的 `delivery_orders` 数组（完整 JSONB，未裁剪）。",
        "",
        f"## 审计摘要（{len(payload['audit_logs'])} 条）",
        "",
    ]
    if payload["audit_logs"]:
        lines += ["| do_number | action | actor_role | 时间 |", "|---|---|---|---|"]
        for row in payload["audit_logs"][:50]:
            lines.append(
                f"| `{row['do_number'] or '-'}` | `{row['action']}` "
                f"| {row['actor_role'] or '-'} | {row['created_at']} |"
            )
    else:
        lines.append("（无）")
    lines += [
        "",
        f"## 字段差异（{len(payload['field_diffs'])} 条）",
        "",
        "见同名 `.json` 的 `field_diffs` 数组。",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return [str(json_path), str(md_path)]


def rebuild(admin: psycopg.Connection, template: str, target: str) -> None:
    # Build before touching the old database; preserve the old DB for recovery.
    suffix = uuid4().hex[:8]
    candidate = f"{target[:42]}_candidate_{suffix}"
    backup = f"{target[:42]}_backup_{suffix}"
    admin.execute(
        pgsql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            pgsql.Identifier(candidate), pgsql.Identifier(template)
        )
    )
    try:
        if database_exists(admin, target):
            # Active writers must be stopped explicitly by the operator. Do not
            # kill sessions and discard an in-flight order/evidence transaction.
            active = admin.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (target,)
            ).fetchone()[0]
            if active:
                raise ResetError("target has active connections; stop API/AI before reset")
            admin.execute(
                pgsql.SQL("ALTER DATABASE {} RENAME TO {}").format(
                    pgsql.Identifier(target), pgsql.Identifier(backup)
                )
            )
        admin.execute(
            pgsql.SQL("ALTER DATABASE {} RENAME TO {}").format(
                pgsql.Identifier(candidate), pgsql.Identifier(target)
            )
        )
    except Exception:
        # Restore the original name if installation failed after renaming it.
        if not database_exists(admin, target) and database_exists(admin, backup):
            admin.execute(
                pgsql.SQL("ALTER DATABASE {} RENAME TO {}").format(
                    pgsql.Identifier(backup), pgsql.Identifier(target)
                )
            )
        raise ResetError(
            "reset installation failed; original database preserved; inspect candidate databases"
        ) from None


def retained_backups(admin: psycopg.Connection, target: str) -> list[str]:
    return [
        row[0]
        for row in admin.execute(
            "SELECT datname FROM pg_database WHERE starts_with(datname, %s) ORDER BY datname",
            (f"{target[:42]}_backup_",),
        ).fetchall()
    ]


def verify_target(args: argparse.Namespace) -> dict[str, Any]:
    url = with_dbname(args.admin_url, args.target)
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        verify_schema(conn)
        manifest = read_seed_manifest(conn, args.tenant)
        if (
            manifest is None
            or seed_content_hash(conn, args.tenant) != manifest["seed_content_sha256"]
        ):
            raise ResetError("rebuilt database row-level content differs from pinned seed")
        ledger = conn.execute(
            "SELECT version, sql_sha256, baseline_hash_sha256 FROM kiraorder_meta.schema_migrations"
        ).fetchall()
        if ledger != [(VERSION, SQL_SHA256, HASH_LIST_SHA256)]:
            raise ResetError(
                "migration ledger in the rebuilt database does not match the frozen baseline"
            )
        flow = {
            table: int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in FLOW_TABLES + ("approval_requests",)
        }
        alias_rows = int(conn.execute("SELECT count(*) FROM alias_cache").fetchone()[0])
        snapshot = seed_snapshot(conn, args.tenant)

    leftovers = {name: value for name, value in flow.items() if value != 0}
    if leftovers:
        raise ResetError(f"rebuilt database still contains runtime rows: {leftovers}")
    if alias_rows != args.expect_alias_cache:
        raise ResetError(
            f"rebuilt database alias_cache {alias_rows} != expected {args.expect_alias_cache}"
        )

    differences = snapshot_differences(snapshot, expected_snapshot(args))
    if differences:
        raise ResetError(f"rebuilt database does not match products.csv: {differences}")

    return {
        "flow_rows": flow,
        "alias_cache": alias_rows,
        "snapshot": snapshot,
        "ledger": ledger[0][0],
    }


def run_hook(command: str, timeout: int) -> int:
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )
    if completed.returncode != 0:
        raise ResetError(f"post-reset hook failed ({completed.returncode}); output suppressed")
    return completed.returncode


def init_template(args: argparse.Namespace, admin: psycopg.Connection) -> Report:
    if not args.seed_sql:
        raise ResetError("--init-template requires --seed-sql")
    seed_path = Path(args.seed_sql).expanduser().resolve()
    if not seed_path.is_file():
        raise ResetError(f"seed file not found: {seed_path}")
    if not SAFE_TEMPLATE.match(args.template):
        raise ResetError("template name must look like kiraorder_<name>_seed")

    report = Report(
        action="init-template",
        template=args.template,
        target=args.target,
        tenant=args.tenant,
        started_at=utc_stamp(),
    )
    if not args.seed_version or not args.seed_sha256:
        raise ResetError("--init-template requires --seed-version and --seed-sha256")
    raw = seed_path.read_bytes()
    if hashlib.sha256(raw).hexdigest().lower() != args.seed_sha256.lower():
        raise ResetError("seed SQL checksum does not match --seed-sha256")
    try:
        seed_text = raw.decode("utf-8")
        validate_data_only_sql(seed_text, args.tenant)
    except (UnicodeDecodeError, SeedError):
        raise ResetError("seed SQL must be UTF-8 literal tenant-scoped INSERTs") from None
    if database_exists(admin, args.template):
        raise ResetError("template already exists; choose a new versioned template name")
    admin.execute(
        pgsql.SQL("CREATE DATABASE {} TEMPLATE template0").format(pgsql.Identifier(args.template))
    )
    url = with_dbname(args.admin_url, args.template)
    migrate(Settings(_env_file=None, database_url=url))

    with psycopg.connect(url, autocommit=False, cursor_factory=psycopg.ClientCursor) as conn:
        conn.execute(seed_text)
        conn.execute(SEED_MANIFEST_DDL)
        snapshot = seed_snapshot(conn, args.tenant)
        differences = snapshot_differences(snapshot, expected_snapshot(args))
        if differences:
            raise ResetError(f"seed does not match products.csv: {differences}")
        conn.execute(
            "INSERT INTO kiraorder_meta.seed_manifest "
            "(tenant_id, seed_version, seed_sha256, product_count, inventory_total, "
            "family_count, customer_count, price_count, price_total_a, price_total_b, "
            "seed_content_sha256) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (tenant_id) DO UPDATE SET seed_version = EXCLUDED.seed_version, "
            "seed_sha256 = EXCLUDED.seed_sha256, product_count = EXCLUDED.product_count, "
            "inventory_total = EXCLUDED.inventory_total, family_count = EXCLUDED.family_count, "
            "customer_count = EXCLUDED.customer_count, price_count = EXCLUDED.price_count, "
            "price_total_a = EXCLUDED.price_total_a, price_total_b = EXCLUDED.price_total_b, "
            "applied_at = now()",
            (
                args.tenant,
                args.seed_version,
                args.seed_sha256.lower(),
                snapshot["product_count"],
                snapshot["inventory_total"],
                snapshot["family_count"],
                snapshot["customer_count"],
                snapshot["price_count"],
                snapshot["price_total_a"],
                snapshot["price_total_b"],
                seed_content_hash(conn, args.tenant),
            ),
        )
        verify_schema(conn)

    report.checks = {"inventory": snapshot, "seed_version": args.seed_version}
    report.status = "ok"
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rebuild the T1 trial database from a pinned template."
    )
    parser.add_argument("--admin-url", default=os.environ.get("RESET_ADMIN_DATABASE_URL"))
    parser.add_argument("--template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--tenant", default="T1")
    parser.add_argument("--expect-seed-version")
    parser.add_argument("--expect-seed-sha256")
    parser.add_argument("--expect-products", type=int, default=40)
    parser.add_argument("--expect-families", type=int, default=25)
    parser.add_argument("--expect-customers", type=int, default=8)
    parser.add_argument("--expect-prices", type=int, default=80)
    parser.add_argument("--expect-price-a", default="1060.40")
    parser.add_argument("--expect-price-b", default="1150.50")
    parser.add_argument("--expect-inventory", type=int, default=795)
    parser.add_argument("--expect-alias-cache", type=int, default=2)
    parser.add_argument("--evidence-dir", default=str(REPO_ROOT / "evidence" / "reset"))
    parser.add_argument("--log-dir", default=str(REPO_ROOT / "logs"))
    parser.add_argument("--hook")
    parser.add_argument("--hook-timeout", type=int, default=180)
    parser.add_argument("--allow-any-target", action="store_true")
    parser.add_argument("--seed-sql")
    parser.add_argument("--seed-version")
    parser.add_argument("--seed-sha256")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--init-template", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.tenant):
        print("reset failed: invalid tenant identifier", file=sys.stderr)
        return 2
    if not args.admin_url:
        print(
            "reset failed: RESET_ADMIN_DATABASE_URL (or --admin-url) is required", file=sys.stderr
        )
        return 1
    if not (args.apply or args.dry_run or args.init_template):
        print("reset failed: choose --dry-run, --apply or --init-template", file=sys.stderr)
        return 2
    if args.apply and (not args.expect_seed_version or not args.expect_seed_sha256):
        print(
            "reset failed: --apply requires --expect-seed-version and --expect-seed-sha256",
            file=sys.stderr,
        )
        return 2

    report = Report(
        action="init-template" if args.init_template else ("apply" if args.apply else "dry-run"),
        template=args.template,
        target=args.target,
        tenant=args.tenant,
        started_at=utc_stamp(),
    )
    log_lines: list[str] = [f"reset_demo {report.action} {report.started_at}"]

    try:
        ensure_safe_names(args.target, args.template, args.allow_any_target)
        admin = connect_admin(args.admin_url)
        try:
            if args.init_template:
                report = init_template(args, admin)
                report.started_at = report.started_at or utc_stamp()
            else:
                template_info = check_template(args, admin)
                report.checks["template"] = template_info
                log_lines.append(f"template ok: {template_info['manifest']['seed_version']}")

                target_exists = database_exists(admin, args.target)
                log_lines.append(f"target exists: {target_exists}")
                if target_exists:
                    evidence = collect_evidence(
                        with_dbname(args.admin_url, args.target), args.tenant
                    )
                    report.evidence_files = write_evidence(
                        Path(args.evidence_dir), report.started_at, args.target, evidence
                    )
                    report.checks["pre_reset_counts"] = evidence["row_counts"]

                if args.apply:
                    rebuild(admin, args.template, args.target)
                    report.checks["retained_backup_databases"] = retained_backups(
                        admin, args.target
                    )
                    report.checks["post_reset"] = verify_target(args)
                    if args.hook:
                        report.hook_exit_code = run_hook(args.hook, args.hook_timeout)
                report.status = "ok"
        finally:
            admin.close()
    except ResetError as exc:
        report.status = "failed"
        report.error = str(exc)
    except Exception as exc:  # noqa: BLE001 - never leak a DSN or raw SQL
        report.status = "failed"
        report.error = f"unexpected {type(exc).__name__}; details suppressed"

    payload = {
        "action": report.action,
        "template": report.template,
        "target": report.target,
        "tenant": report.tenant,
        "started_at": report.started_at,
        "status": report.status,
        "checks": report.checks,
        "evidence_files": report.evidence_files,
        "hook_exit_code": report.hook_exit_code,
        "error": report.error,
    }
    log_lines.append(json.dumps(payload, ensure_ascii=False, default=str))

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"reset_{args.tenant}_{report.started_at}.log"
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, default=str))
    if report.status != "ok":
        print(f"reset failed: {report.error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
