"""Apply a version-pinned, data-only tenant seed exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

import psycopg
from pglast import ast, parse_sql
from pglast.parser import split

from app.config import Settings
from app.db import DatabaseConfigurationError, connect

SEED_MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS kiraorder_meta.seed_manifest (
    tenant_id       text PRIMARY KEY,
    seed_version    text NOT NULL,
    seed_sha256     text NOT NULL,
    product_count   integer NOT NULL,
    inventory_total integer NOT NULL,
    applied_at      timestamptz NOT NULL DEFAULT now()
)
"""


class SeedError(Exception):
    """A controlled seed failure with no connection string or raw SQL payload."""


@dataclass(frozen=True)
class SeedResult:
    status: str
    tenant: str
    seed_version: str
    sql_sha256: str
    product_count: int
    inventory_total: int


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest().lower()
    except OSError:
        raise SeedError(f"seed file is missing or unreadable: {path}") from None


def validate_data_only_sql(text: str) -> None:
    """Seed files must not open their own transaction around our transaction."""
    for statement in split(text):
        for node in parse_sql(statement):
            if isinstance(node.stmt, ast.TransactionStmt):
                raise SeedError("seed SQL must not contain BEGIN/COMMIT/ROLLBACK")


def _counts(conn: psycopg.Connection, tenant: str) -> tuple[int, int]:
    products = conn.execute(
        "SELECT count(*) FROM products WHERE tenant_id = %s", (tenant,)
    ).fetchone()[0]
    inventory = conn.execute(
        "SELECT coalesce(sum(available_qty), 0) FROM inventory WHERE tenant_id = %s",
        (tenant,),
    ).fetchone()[0]
    return int(products), int(inventory)


def load_seed(
    settings: Settings,
    *,
    tenant: str,
    seed_path: Path,
    seed_version: str,
    expect_sha256: str,
    expect_products: int,
    expect_inventory: int,
) -> SeedResult:
    actual_sha = sha256_file(seed_path)
    if actual_sha != expect_sha256.lower():
        raise SeedError("seed SQL checksum does not match --expect-sha256")

    try:
        text = seed_path.read_text(encoding="utf-8")
    except OSError:
        raise SeedError("seed file is unreadable") from None
    validate_data_only_sql(text)

    with connect(settings) as conn:
        conn.execute("BEGIN")
        try:
            conn.execute("SET LOCAL search_path TO public")
            conn.execute("CREATE SCHEMA IF NOT EXISTS kiraorder_meta")
            conn.execute(SEED_MANIFEST_DDL)
            row = conn.execute(
                "SELECT seed_version, seed_sha256, product_count, inventory_total "
                "FROM kiraorder_meta.seed_manifest WHERE tenant_id = %s",
                (tenant,),
            ).fetchone()

            if row is not None:
                version, sha, products, inventory = row
                if (version, sha, products, inventory) != (
                    seed_version,
                    actual_sha,
                    expect_products,
                    expect_inventory,
                ):
                    raise SeedError("seed manifest does not match this seed/version")
                status = "already_loaded"
            else:
                if conn.execute("SELECT 1 FROM tenants WHERE tenant_id = %s", (tenant,)).fetchone():
                    raise SeedError("tenant exists without a seed manifest; refusing adoption")
                conn.execute(text)
                products, inventory = _counts(conn, tenant)
                if products != expect_products or inventory != expect_inventory:
                    raise SeedError(
                        "loaded seed counts do not match --expect-products/--expect-inventory"
                    )
                conn.execute(
                    "INSERT INTO kiraorder_meta.seed_manifest "
                    "(tenant_id, seed_version, seed_sha256, product_count, inventory_total) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (tenant, seed_version, actual_sha, products, inventory),
                )
                status = "loaded"

            products, inventory = _counts(conn, tenant)
            if products != expect_products or inventory != expect_inventory:
                raise SeedError("seed counts changed before commit")
            conn.execute("COMMIT")
        except BaseException:
            with suppress(psycopg.Error):
                conn.execute("ROLLBACK")
            raise

    return SeedResult(
        status=status,
        tenant=tenant,
        seed_version=seed_version,
        sql_sha256=actual_sha,
        product_count=expect_products,
        inventory_total=expect_inventory,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply one tenant seed file exactly once.")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--seed-sql", required=True, type=Path)
    parser.add_argument("--seed-version", required=True)
    parser.add_argument("--expect-sha256", required=True)
    parser.add_argument("--expect-products", required=True, type=int)
    parser.add_argument("--expect-inventory", required=True, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = load_seed(
            Settings(),
            tenant=args.tenant,
            seed_path=args.seed_sql,
            seed_version=args.seed_version,
            expect_sha256=args.expect_sha256,
            expect_products=args.expect_products,
            expect_inventory=args.expect_inventory,
        )
    except SeedError as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    except DatabaseConfigurationError as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(
            f"seed failed: database error (SQLSTATE {exc.sqlstate or 'unavailable'})",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
