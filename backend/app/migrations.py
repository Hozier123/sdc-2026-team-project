"""Apply the frozen baseline exactly once, with its ledger in the same transaction."""

import hashlib
import json
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

import psycopg
from pglast import ast, parse_sql
from pglast.parser import split

from app.config import REPO_ROOT, Settings
from app.db import DatabaseConfigurationError, connect

VERSION = "0001_baseline"
BASELINE_TAG = "gate0-baseline-v1"
HASH_LIST_SHA256 = "6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770"
SQL_SHA256 = "6DDFD6160A2416237A73ADC16A3B26F4DDE0657FD42BDB2A7C355682711FE471"
GATE0_ROOT = REPO_ROOT / "gate0"
MIGRATION_LOCK = 0x4B4952410001
EXPECTED_TABLES = {
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
    "inbound_messages",
    "orders",
    "draft_versions",
    "approval_requests",
    "delivery_orders",
    "activity_log",
    "audit_logs",
    "field_diffs",
}
EXPECTED_TRIGGERS = {
    ("draft_versions", "draft_versions_immutable"),
    ("delivery_orders", "delivery_orders_immutable"),
    ("activity_log", "activity_log_append_only"),
    ("audit_logs", "audit_logs_append_only"),
    ("field_diffs", "field_diffs_append_only"),
    ("approval_requests", "approval_request_snapshot_guard"),
}
EXPECTED_UNIQUE_INDEXES = {
    "customers_tenant_phone_unique",
    "alias_cache_scope_phrase_unique",
    "one_pending_approval_per_draft",
}


class MigrationError(Exception):
    """A controlled failure with no connection strings or raw SQL payloads."""


@dataclass(frozen=True)
class MigrationResult:
    status: str
    version: str = VERSION
    sql_sha256: str = SQL_SHA256
    table_count: int = 18
    trigger_count: int = 6
    trigger_event_count: int = 12


def verified_statements(gate0_root: Path = GATE0_ROOT) -> tuple[str, ...]:
    """Hash raw bytes before decoding; parser boundaries preserve SQL statement text."""
    try:
        hash_list = (gate0_root / "docs/gate0-hashes.txt").read_bytes()
        raw_sql = (gate0_root / "migrations/0001_baseline.sql").read_bytes()
    except OSError:
        raise MigrationError("Frozen baseline files are missing or unreadable") from None
    if hashlib.sha256(hash_list).hexdigest().upper() != HASH_LIST_SHA256:
        raise MigrationError("Frozen hash-list checksum mismatch")
    if hashlib.sha256(raw_sql).hexdigest().upper() != SQL_SHA256:
        raise MigrationError("Frozen SQL checksum mismatch")
    statements = split(raw_sql.decode("utf-8"))
    if statements[0].strip().upper() != "BEGIN" or statements[-1].strip().upper() != "COMMIT":
        raise MigrationError("Unsupported baseline transaction boundaries")
    if any(
        isinstance(node.stmt, ast.TransactionStmt)
        for statement in statements[1:-1]
        for node in parse_sql(statement)
    ):
        raise MigrationError("Unexpected intermediate transaction control")
    return statements


def verify_schema(conn: psycopg.Connection) -> None:
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        )
    }
    if tables != EXPECTED_TABLES:
        raise MigrationError("Expected exactly the 18 Gate 0 public tables")
    triggers = conn.execute(
        "SELECT c.relname, t.tgname, t.tgtype, t.tgenabled "
        "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND NOT t.tgisinternal"
    ).fetchall()
    if {(row[0], row[1]) for row in triggers} != EXPECTED_TRIGGERS:
        raise MigrationError("Expected the six Gate 0 trigger objects")
    # pg_trigger bits: ROW=1, BEFORE=2, DELETE=8, UPDATE=16.
    if any(row[2] != 27 or row[3] != "O" for row in triggers):
        raise MigrationError("Gate 0 triggers must be enabled BEFORE UPDATE OR DELETE FOR EACH ROW")
    events = set(
        conn.execute(
            "SELECT event_object_table, trigger_name, event_manipulation "
            "FROM information_schema.triggers WHERE trigger_schema='public'"
        ).fetchall()
    )
    if events != {
        (table, name, event) for table, name in EXPECTED_TRIGGERS for event in ("UPDATE", "DELETE")
    }:
        raise MigrationError("Expected all twelve Gate 0 trigger event records")
    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT c.relname FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND i.indisunique AND i.indisvalid"
        )
    }
    if not EXPECTED_UNIQUE_INDEXES <= indexes:
        raise MigrationError("Gate 0 unique indexes are missing")


def migrate(settings: Settings, gate0_root: Path = GATE0_ROOT) -> MigrationResult:
    statements = verified_statements(gate0_root)  # Before any database side effect.
    with connect(settings) as conn:
        try:
            # Execute the baseline's own BEGIN/COMMIT; do not wrap it in another transaction.
            conn.execute(statements[0])
            conn.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            conn.execute("SET LOCAL search_path TO public")
            conn.execute("SET LOCAL statement_timeout TO '30s'")
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
            conn.execute("CREATE SCHEMA IF NOT EXISTS kiraorder_meta")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kiraorder_meta.schema_migrations ("
                "version text PRIMARY KEY, sql_sha256 text NOT NULL, "
                "baseline_hash_sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            rows = conn.execute(
                "SELECT version, sql_sha256, baseline_hash_sha256 "
                "FROM kiraorder_meta.schema_migrations"
            ).fetchall()
            if rows:
                if rows != [(VERSION, SQL_SHA256, HASH_LIST_SHA256)]:
                    raise MigrationError("Migration ledger does not match the frozen baseline")
                status = "already_applied"
            else:
                if conn.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE' LIMIT 1"
                ).fetchone():
                    raise MigrationError(
                        "Untracked public tables exist; refusing automatic adoption"
                    )
                for statement in statements[1:-1]:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO kiraorder_meta.schema_migrations "
                    "(version, sql_sha256, baseline_hash_sha256) VALUES (%s, %s, %s)",
                    (VERSION, SQL_SHA256, HASH_LIST_SHA256),
                )
                status = "applied"
            verify_schema(conn)
            conn.execute(statements[-1])
        except BaseException:
            with suppress(psycopg.Error):
                conn.execute("ROLLBACK")
            raise
    return MigrationResult(status=status)


def main() -> int:
    try:
        result = migrate(Settings())
    except (MigrationError, DatabaseConfigurationError) as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        # Never echo the driver exception: it may contain a DSN or server data.
        print(
            f"Migration failed: database error (SQLSTATE {exc.sqlstate or 'unavailable'})",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(asdict(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
