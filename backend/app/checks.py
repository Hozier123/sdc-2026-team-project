"""Tenant-level soft checks controlled by ``tenants.checks_enabled``.

Hard rules (catalog integrity, pricing, stock) are deliberately not gated here.
"""

from __future__ import annotations

from typing import Any

from app.schemas import Issue, WorkingLine

CHECK_KEYS = ("customer_condition", "same_day_order", "unusual_qty")
_DEFAULTS = {
    "customer_condition": True,
    "same_day_order": True,
    "unusual_qty": False,
}


def normalize_checks(raw: Any) -> dict[str, bool]:
    """Only an explicit JSON true enables a soft check."""
    values = raw if isinstance(raw, dict) else {}
    return {key: values.get(key, _DEFAULTS[key]) is True for key in CHECK_KEYS}


def apply_checks(
    conn,
    *,
    tenant: str,
    customer: dict[str, Any],
    lines: list[WorkingLine],
    checks: dict[str, bool],
    draft_id: str,
) -> list[Issue]:
    """Return soft-check issues for this draft/version."""
    issues: list[Issue] = []
    if checks.get("same_day_order"):
        rows = conn.execute(
            "SELECT d.do_number FROM delivery_orders d "
            "JOIN tenants t ON t.tenant_id=d.tenant_id "
            "WHERE d.tenant_id=%s AND d.customer_id=%s "
            "AND (d.approved_at AT TIME ZONE t.timezone)::date = "
            "    (now() AT TIME ZONE t.timezone)::date "
            "ORDER BY d.approved_at DESC, d.do_number",
            (tenant, customer["customer_id"]),
        ).fetchall()
        if rows:
            existing = [row[0] for row in rows]
            issues.append(
                Issue(
                    issue_id=f"CHK_SAME_DAY_{draft_id}",
                    code="SAME_DAY_ORDER",
                    line_id=None,
                    ask="CLERK",
                    data_used={"existing_do_numbers": existing},
                    blocking=True,
                    resolved=False,
                )
            )
    if checks.get("unusual_qty"):
        for line in lines:
            if not line.sku_id:
                continue
            row = conn.execute(
                "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY "
                "       (item->>'quantity')::int), count(*) "
                "FROM delivery_orders d "
                "CROSS JOIN LATERAL jsonb_array_elements(d.lines) item "
                "WHERE d.tenant_id=%s AND d.customer_id=%s "
                "AND item->>'sku_id'=%s "
                "AND d.approved_at >= now() - interval '28 days'",
                (tenant, customer["customer_id"], line.sku_id),
            ).fetchone()
            median, count = (row[0], row[1]) if row else (None, 0)
            if median is None or count < 3 or median <= 0:
                continue
            qty = line.effective_qty
            if qty > median * 3 or qty < median / 3:
                issues.append(
                    Issue(
                        issue_id=f"CHK_UNUSUAL_{draft_id}_{line.line_id}",
                        code="UNUSUAL_QTY",
                        line_id=line.line_id,
                        ask="CLERK",
                        data_used={
                            "effective_qty": qty,
                            "median_qty": str(median),
                            "history_count": count,
                        },
                        blocking=True,
                        resolved=False,
                    )
                )
    return issues
