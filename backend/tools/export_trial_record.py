"""Export delivery orders at line level for trial records (Zhou r2 requirement).

The manual baseline records each order line by line (L1, L2, ...). An order-level
total cannot tell "wrong pack size" from "wrong quantity" from "wrong price", so
the tool group must hand in rows with the same values per line:

    sku_id, pack_size, grade, quantity, unit, applied_unit_price, subtotal_rm

Rules confirmed by the test side (A1/B1/C1) plus Zhou's supplements:

* line order is the ``lines[]`` array order, labelled ``L1..Ln``; no sorting.
  The export also compares that order with the draft's ``working_lines``; a
  mismatch means L1/L2 no longer match the message lines and the record is not
  usable (exit code 2).
* every row carries ``do_number``, ``customer_id`` and ``ai_mode``
* ``final_total_rm`` is exported next to the line subtotals so a wrong order
  total is visible instead of being hidden by line-level sums
* ``pack_size``/``grade`` come from the products table; ``--products-version``
  and ``--products-sha256`` record which snapshot they were read from
* ``ai_mode == MIXED`` (automatic degradation during a trial) is flagged per row
  and listed separately; such orders must not enter the median
* only ``delivery_orders`` rows are read: drafts are never exported

Usage (from ``backend/``)::

    python -m tools.export_trial_record --fixture ../gate0/contracts/fixtures/delivery_order.json \\
        --case-id TEST-01 --out-dir ../evidence/records

    python -m tools.export_trial_record --database-url "$DATABASE_URL" \\
        --tenant T1 --case-id TEST-01 --out-dir ../evidence/records \\
        --products-version T1-0.1 --products-sha256 <sha>
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import psycopg

REQUIRED_LINE_FIELDS = ("sku_id", "quantity", "applied_unit_price", "subtotal_rm")
COLUMNS = (
    "case_id",
    "do_number",
    "customer_id",
    "ai_mode",
    "ai_mode_mixed",
    "line_no",
    "sku_id",
    "pack_size",
    "grade",
    "quantity",
    "unit",
    "applied_unit_price",
    "subtotal_rm",
    "final_total_rm",
    "display_name",
)
SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class ExportError(Exception):
    """A controlled failure safe to show to the operator."""


@dataclass
class DoExport:
    case_id: str
    tenant_id: str
    do_number: str
    customer_id: str
    ai_mode: str
    final_total_rm: str
    rows: list[dict[str, Any]]
    sum_subtotal_rm: str
    totals_match: bool
    order_mismatch: bool
    errors: list[str]

    @property
    def ai_mode_mixed(self) -> bool:
        return self.ai_mode.upper() == "MIXED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "do_number": self.do_number,
            "customer_id": self.customer_id,
            "ai_mode": self.ai_mode,
            "ai_mode_mixed": self.ai_mode_mixed,
            "final_total_rm": self.final_total_rm,
            "sum_subtotal_rm": self.sum_subtotal_rm,
            "totals_match": self.totals_match,
            "order_mismatch": self.order_mismatch,
            "lines": self.rows,
            "errors": self.errors,
        }


def money(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ExportError(f"not a decimal value: {value!r}") from None
    if not result.is_finite() or result < 0:
        raise ExportError("amount must be finite and non-negative")
    return result


def rows_from_do(
    case_id: str,
    do: dict[str, Any],
    products: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    lines = do.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ExportError("DO has no non-empty lines array")
    products = products or {}
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        missing = [field for field in REQUIRED_LINE_FIELDS if field not in line]
        if missing:
            raise ExportError(f"line {index} is missing {', '.join(missing)}")
        if type(line["quantity"]) is not int or line["quantity"] <= 0:
            raise ExportError(f"line {index} quantity must be a positive integer")
        if not line.get("unit"):
            raise ExportError(f"line {index} is missing unit")
        product = products.get(line["sku_id"], {})
        frozen_line = next(
            (
                saved
                for saved in do.get("working_lines", [])
                if saved.get("line_id") == line.get("line_id")
            ),
            {},
        )
        rows.append(
            {
                "case_id": case_id,
                "do_number": do.get("do_number", ""),
                "customer_id": do.get("customer_id", ""),
                "ai_mode": do.get("ai_mode", ""),
                "ai_mode_mixed": str(do.get("ai_mode", "")).upper() == "MIXED",
                "line_no": f"L{index}",
                "sku_id": line["sku_id"],
                "pack_size": frozen_line.get("pack_size", product.get("pack_size")) or "",
                "grade": frozen_line.get("grade", product.get("grade")) or "",
                "quantity": line["quantity"],
                "unit": line.get("unit", ""),
                "applied_unit_price": str(line["applied_unit_price"]),
                "subtotal_rm": str(line["subtotal_rm"]),
                "final_total_rm": str(do.get("final_total_rm", "")),
                "display_name": line.get("display_name", ""),
            }
        )
    return rows


def build_export(
    case_id: str,
    tenant_id: str,
    do: dict[str, Any],
    products: dict[str, dict[str, Any]] | None = None,
    working_lines: list[dict[str, Any]] | None = None,
) -> DoExport:
    rows = rows_from_do(case_id, do, products)
    errors: list[str] = []
    for row in rows:
        expected = money(row["quantity"]) * money(row["applied_unit_price"])
        if money(row["subtotal_rm"]) != expected:
            errors.append(
                f"{row['line_no']}: subtotal {row['subtotal_rm']} != quantity x price {expected}"
            )

    final_total = money(do.get("final_total_rm", "0"))
    line_sum = sum((money(row["subtotal_rm"]) for row in rows), Decimal("0"))
    if line_sum != final_total:
        errors.append(f"sum(subtotal_rm) {line_sum} != final_total_rm {final_total}")

    order_mismatch = False
    if working_lines is not None:
        draft_ids = [line.get("line_id") for line in working_lines]
        do_ids = [line.get("line_id") for line in do.get("lines", [])]
        if draft_ids != do_ids:
            order_mismatch = True
            errors.append(
                f"line order differs from the draft working_lines order: {draft_ids} != {do_ids}"
            )

    return DoExport(
        case_id=case_id,
        tenant_id=tenant_id,
        do_number=str(do.get("do_number", "")),
        customer_id=str(do.get("customer_id", "")),
        ai_mode=str(do.get("ai_mode", "")),
        final_total_rm=str(final_total),
        rows=rows,
        sum_subtotal_rm=str(line_sum),
        totals_match=line_sum == final_total and not any("subtotal" in e for e in errors),
        order_mismatch=order_mismatch,
        errors=errors,
    )


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = payload.get("body", payload)
    if not isinstance(body, dict) or "lines" not in body:
        raise ExportError("fixture does not contain a delivery order body")
    return body


def fetch_orders(
    database_url: str, tenant_id: str, do_number: str | None
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return DOs plus the product snapshot used for pack_size/grade."""
    where = "d.tenant_id = %s" + (" AND d.do_number = %s" if do_number else "")
    params: tuple[Any, ...] = (tenant_id, do_number) if do_number else (tenant_id,)
    query = (
        "SELECT to_jsonb(d) || jsonb_build_object("
        "  'ai_mode', o.ai_mode,"
        "  'working_lines', COALESCE(dv.snapshot->'lines', o.working_lines)"
        ") "
        "FROM delivery_orders d "
        "LEFT JOIN orders o ON o.tenant_id = d.tenant_id AND o.draft_id = d.draft_id "
        "LEFT JOIN draft_versions dv ON dv.tenant_id=d.tenant_id AND dv.draft_id=d.draft_id "
        "AND dv.version=d.draft_version "
        f"WHERE {where} ORDER BY d.approved_at"
    )
    try:
        with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as conn:
            orders = [row[0] for row in conn.execute(query, params).fetchall()]
            products = {
                row[0]: {"pack_size": row[1], "grade": row[2]}
                for row in conn.execute(
                    "SELECT product_id, pack_size, grade FROM products WHERE tenant_id = %s",
                    (tenant_id,),
                )
            }
            return orders, products
    except psycopg.Error as exc:
        raise ExportError(f"cannot read delivery orders (SQLSTATE {exc.sqlstate})") from None


def _extract_working_lines(do: dict[str, Any]) -> list[dict[str, Any]] | None:
    value = do.get("working_lines")
    if value is None:
        return None
    return value if isinstance(value, list) else None


def write_outputs(
    out_dir: Path,
    case_id: str,
    exports: Iterable[DoExport],
    total_row: bool,
    products_meta: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{case_id}_do_lines.csv"
    json_path = out_dir / f"{case_id}_do_lines.json"
    exports = list(exports)
    if not exports:
        raise ExportError("cannot certify an empty export")

    def csv_safe(row):
        return {
            key: (
                "'" + value
                if isinstance(value, str)
                and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
            )
            for key, value in row.items()
        }

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for export in exports:
            writer.writerows(csv_safe(row) for row in export.rows)
            if total_row:
                writer.writerow(
                    csv_safe(
                        {
                            "case_id": export.case_id,
                            "do_number": export.do_number,
                            "customer_id": export.customer_id,
                            "ai_mode": export.ai_mode,
                            "ai_mode_mixed": export.ai_mode_mixed,
                            "line_no": "合计",
                            "sku_id": "",
                            "pack_size": "",
                            "grade": "",
                            "quantity": "",
                            "unit": "",
                            "applied_unit_price": "",
                            "subtotal_rm": export.final_total_rm,
                            "final_total_rm": export.final_total_rm,
                            "display_name": "" if export.totals_match else "总额或行金额不一致",
                        }
                    )
                )

    mixed = [export.do_number for export in exports if export.ai_mode_mixed]
    order_mismatch = [export.do_number for export in exports if export.order_mismatch]
    payload = {
        "case_id": case_id,
        "exported_at": datetime.now().astimezone().isoformat(),
        "products": {**(products_meta or {}), "verification": "OPERATOR_ASSERTED_NOT_VERIFIED"},
        "totals_match": all(export.totals_match for export in exports),
        "mixed_orders": mixed,
        "order_mismatch_orders": order_mismatch,
        "orders": [export.as_dict() for export in exports],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export delivery orders at line level for trial records."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    source.add_argument("--fixture")
    parser.add_argument("--tenant", default="T1")
    parser.add_argument("--do-number")
    parser.add_argument("--case-id", required=True, help="trial case id, e.g. TEST-01")
    parser.add_argument("--out-dir", default="evidence/records")
    parser.add_argument("--products-version", help="products snapshot version, e.g. T1-0.1")
    parser.add_argument("--products-sha256", help="products.csv SHA-256 used for pack_size/grade")
    parser.add_argument(
        "--no-total-row",
        action="store_true",
        help="omit the human-readable 合计 row from the CSV",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not SAFE_CASE_ID.match(args.case_id):
        print("export failed: --case-id may only contain letters, digits, dot, dash, underscore")
        return 1

    try:
        products: dict[str, dict[str, Any]] = {}
        if args.fixture:
            path = Path(args.fixture).expanduser().resolve()
            if not path.is_file():
                raise ExportError(f"fixture not found: {path}")
            orders = [load_fixture(path)]
        else:
            if not args.database_url:
                raise ExportError("DATABASE_URL (or --database-url) is required")
            orders, products = fetch_orders(args.database_url, args.tenant, args.do_number)
            if not orders:
                raise ExportError(
                    f"no delivery orders for tenant {args.tenant}"
                    + (f" and do_number {args.do_number}" if args.do_number else "")
                )

        exports = [
            build_export(
                args.case_id,
                args.tenant,
                do,
                products=products,
                working_lines=_extract_working_lines(do) if args.fixture is None else None,
            )
            for do in orders
        ]
        products_meta = {
            key: value
            for key, value in (
                ("version", args.products_version),
                ("sha256", args.products_sha256),
            )
            if value
        }
        csv_path, json_path = write_outputs(
            Path(args.out_dir), args.case_id, exports, not args.no_total_row, products_meta
        )
    except ExportError as exc:
        print(f"export failed: {exc}")
        return 1

    mismatched = [export.do_number for export in exports if not export.totals_match]
    order_mismatch = [export.do_number for export in exports if export.order_mismatch]
    mixed = [export.do_number for export in exports if export.ai_mode_mixed]
    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "orders": len(exports),
                "lines": sum(len(export.rows) for export in exports),
                "totals_match": not mismatched,
                "mismatched_orders": mismatched,
                "order_mismatch_orders": order_mismatch,
                "mixed_orders": mixed,
                "csv": str(csv_path),
                "json": str(json_path),
            },
            ensure_ascii=False,
        )
    )
    if mismatched or order_mismatch:
        print(
            "export warning: totals or line order do not match; files written "
            "but the record is not clean"
        )
        return 2
    if mixed:
        print("export warning: MIXED ai_mode detected; report these orders separately")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
