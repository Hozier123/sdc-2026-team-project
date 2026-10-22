"""Export delivery orders at line level for trial records (Zhou r2 requirement).

The manual baseline records each order line by line (L1, L2, ...). An order-level
total cannot tell "wrong pack size" from "wrong quantity" from "wrong price", so
the tool group must hand in rows with the same four values per line:

    sku_id, quantity, applied_unit_price, subtotal_rm

Rules confirmed by the test side (A1/B1/C1):

* line order is the ``lines[]`` array order, labelled ``L1..Ln``; no sorting
* every row carries ``do_number`` so a trial with several DOs stays separable
* ``unit`` and ``display_name`` are included read-only for human reconciliation
* money is a decimal string; ``subtotal_rm == quantity * applied_unit_price``
  and ``sum(subtotal_rm) == final_total_rm`` must both hold, otherwise the file
  is written and the process exits with code 2 so the defect is not missed

Usage (from ``backend/``)::

    python -m tools.export_trial_record --fixture ../gate0/contracts/fixtures/delivery_order.json \\
        --case-id TEST-01 --out-dir ../evidence/records

    python -m tools.export_trial_record --database-url "$DATABASE_URL" \\
        --tenant T1 --case-id TEST-01 --out-dir ../evidence/records

``--fixture`` validates the format before P0-A can produce real orders; the
database mode is the one used during the trial.
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
    "line_no",
    "sku_id",
    "quantity",
    "unit",
    "applied_unit_price",
    "subtotal_rm",
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
    final_total_rm: str
    rows: list[dict[str, Any]]
    sum_subtotal_rm: str
    totals_match: bool
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "do_number": self.do_number,
            "customer_id": self.customer_id,
            "final_total_rm": self.final_total_rm,
            "sum_subtotal_rm": self.sum_subtotal_rm,
            "totals_match": self.totals_match,
            "lines": self.rows,
            "errors": self.errors,
        }


def money(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ExportError(f"not a decimal value: {value!r}") from None


def rows_from_do(case_id: str, do: dict[str, Any]) -> list[dict[str, Any]]:
    lines = do.get("lines")
    if not isinstance(lines, list):
        raise ExportError("DO has no lines array")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        missing = [field for field in REQUIRED_LINE_FIELDS if field not in line]
        if missing:
            raise ExportError(f"line {index} is missing {', '.join(missing)}")
        rows.append(
            {
                "case_id": case_id,
                "do_number": do.get("do_number", ""),
                "line_no": f"L{index}",
                "sku_id": line["sku_id"],
                "quantity": line["quantity"],
                "unit": line.get("unit", ""),
                "applied_unit_price": str(line["applied_unit_price"]),
                "subtotal_rm": str(line["subtotal_rm"]),
                "display_name": line.get("display_name", ""),
            }
        )
    return rows


def build_export(case_id: str, tenant_id: str, do: dict[str, Any]) -> DoExport:
    rows = rows_from_do(case_id, do)
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

    return DoExport(
        case_id=case_id,
        tenant_id=tenant_id,
        do_number=str(do.get("do_number", "")),
        customer_id=str(do.get("customer_id", "")),
        final_total_rm=str(final_total),
        rows=rows,
        sum_subtotal_rm=str(line_sum),
        totals_match=not errors,
        errors=errors,
    )


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = payload.get("body", payload)
    if not isinstance(body, dict) or "lines" not in body:
        raise ExportError("fixture does not contain a delivery order body")
    return body


def fetch_orders(database_url: str, tenant_id: str, do_number: str | None) -> list[dict[str, Any]]:
    query = (
        "SELECT to_jsonb(d) FROM delivery_orders d WHERE tenant_id = %s"
        + (" AND do_number = %s" if do_number else "")
        + " ORDER BY approved_at"
    )
    params: tuple[Any, ...] = (tenant_id, do_number) if do_number else (tenant_id,)
    try:
        with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as conn:
            return [row[0] for row in conn.execute(query, params).fetchall()]
    except psycopg.Error as exc:
        raise ExportError(f"cannot read delivery orders (SQLSTATE {exc.sqlstate})") from None


def write_outputs(
    out_dir: Path, case_id: str, exports: Iterable[DoExport], total_row: bool
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{case_id}_do_lines.csv"
    json_path = out_dir / f"{case_id}_do_lines.json"
    exports = list(exports)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for export in exports:
            writer.writerows(export.rows)
            if total_row:
                writer.writerow(
                    {
                        "case_id": export.case_id,
                        "do_number": export.do_number,
                        "line_no": "合计",
                        "sku_id": "",
                        "quantity": "",
                        "unit": "",
                        "applied_unit_price": "",
                        "subtotal_rm": export.final_total_rm,
                        "display_name": "" if export.totals_match else "总额或行金额不一致",
                    }
                )

    payload = {
        "case_id": case_id,
        "exported_at": datetime.now().astimezone().isoformat(),
        "totals_match": all(export.totals_match for export in exports),
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
        if args.fixture:
            path = Path(args.fixture).expanduser().resolve()
            if not path.is_file():
                raise ExportError(f"fixture not found: {path}")
            orders = [load_fixture(path)]
        else:
            if not args.database_url:
                raise ExportError("DATABASE_URL (or --database-url) is required")
            orders = fetch_orders(args.database_url, args.tenant, args.do_number)
            if not orders:
                raise ExportError(
                    f"no delivery orders for tenant {args.tenant}"
                    + (f" and do_number {args.do_number}" if args.do_number else "")
                )

        exports = [build_export(args.case_id, args.tenant, do) for do in orders]
        csv_path, json_path = write_outputs(
            Path(args.out_dir), args.case_id, exports, not args.no_total_row
        )
    except ExportError as exc:
        print(f"export failed: {exc}")
        return 1

    mismatched = [export.do_number for export in exports if not export.totals_match]
    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "orders": len(exports),
                "lines": sum(len(export.rows) for export in exports),
                "totals_match": not mismatched,
                "mismatched_orders": mismatched,
                "csv": str(csv_path),
                "json": str(json_path),
            },
            ensure_ascii=False,
        )
    )
    if mismatched:
        print("export warning: totals do not match; files written but the record is not clean")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
