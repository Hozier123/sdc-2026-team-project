"""Deterministic catalog resolver and customer memory lookup for parse-draft.

This module is intentionally independent of the AI transport. It answers only
questions the backend can prove from the frozen catalog:

* which active product(s) match family + unit + pack + grade;
* whether a customer/tenant alias already pins a phrase to one SKU.

Ambiguous matches stay ambiguous; they are never silently resolved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from app.extraction.base import RawExtraction, RawRow
from app.extraction.evidence import exact_phrase, normalize, quantity_evidence


@dataclass(frozen=True)
class CatalogProduct:
    sku_id: str
    family_id: str
    name: str
    pack_size: str | None
    grade: str | None
    base_unit: str
    tier_price: Decimal | None
    available_qty: int


@dataclass(frozen=True)
class CatalogAlias:
    alias_id: str
    phrase: str
    target_type: str
    family_id: str | None
    product_id: str | None
    scope: str
    created_at: Any

    def record(self) -> dict[str, Any]:
        return {
            "alias_id": self.alias_id,
            "phrase": self.phrase,
            "target_type": self.target_type,
            "family_id": self.family_id,
            "product_id": self.product_id,
            "scope": self.scope,
            "active": True,
            "created_at": (
                self.created_at.isoformat()
                if hasattr(self.created_at, "isoformat")
                else self.created_at
            ),
        }


@dataclass(frozen=True)
class Catalog:
    products: tuple[CatalogProduct, ...]
    aliases: tuple[CatalogAlias, ...]

    @property
    def by_sku(self) -> dict[str, CatalogProduct]:
        return {product.sku_id: product for product in self.products}


@dataclass(frozen=True)
class Resolution:
    product: CatalogProduct | None
    candidates: tuple[CatalogProduct, ...]
    issue_code: str | None = None


def load_catalog(conn, tenant: str, customer_id: str, tier: str) -> Catalog:
    rows = conn.execute(
        "SELECT p.product_id, p.family_id, p.name, p.pack_size, p.grade, p.base_unit, "
        "ctp.unit_price_rm, COALESCE(i.available_qty, 0) "
        "FROM products p "
        "JOIN product_families f "
        "  ON f.tenant_id=p.tenant_id AND f.family_id=p.family_id "
        "LEFT JOIN customer_tier_prices ctp "
        "  ON ctp.tenant_id=p.tenant_id AND ctp.product_id=p.product_id AND ctp.tier=%s "
        "LEFT JOIN inventory i "
        "  ON i.tenant_id=p.tenant_id AND i.product_id=p.product_id "
        "WHERE p.tenant_id=%s AND p.active=true AND f.active=true "
        "ORDER BY p.product_id",
        (tier, tenant),
    ).fetchall()
    products = tuple(
        CatalogProduct(
            sku_id=row[0],
            family_id=row[1],
            name=row[2],
            pack_size=row[3],
            grade=row[4],
            base_unit=row[5],
            tier_price=Decimal(row[6]) if row[6] is not None else None,
            available_qty=int(row[7]),
        )
        for row in rows
    )
    alias_rows = conn.execute(
        "SELECT alias_id, phrase, target_type, family_id, product_id, "
        "CASE WHEN customer_id IS NULL THEN 'TENANT' ELSE 'CUSTOMER' END, created_at "
        "FROM alias_cache "
        "WHERE tenant_id=%s AND active=true AND (customer_id=%s OR customer_id IS NULL) "
        "ORDER BY (customer_id IS NULL), length(phrase) DESC, alias_id",
        (tenant, customer_id),
    ).fetchall()
    aliases = tuple(
        CatalogAlias(
            alias_id=row[0],
            phrase=row[1],
            target_type=row[2],
            family_id=row[3],
            product_id=row[4],
            scope=row[5],
            created_at=row[6],
        )
        for row in alias_rows
    )
    return Catalog(products=products, aliases=aliases)


def _grade_in_span(products: list[CatalogProduct], span: str) -> set[str]:
    grades = {product.grade for product in products if product.grade}
    return {grade for grade in grades if exact_phrase(grade, span)}


def resolve_row(row: RawRow, catalog: Catalog) -> Resolution:
    if not row.fam or row.fam == "UNKNOWN":
        return Resolution(product=None, candidates=())
    products = [product for product in catalog.products if product.family_id == row.fam]
    if not products:
        return Resolution(product=None, candidates=())

    if row.uom:
        wanted = normalize(row.uom)
        products = [product for product in products if product.base_unit == wanted]
    if row.pack_size:
        wanted = normalize(row.pack_size)
        products = [
            product
            for product in products
            if product.pack_size and normalize(product.pack_size) == wanted
        ]
    grades = _grade_in_span(products, row.span)
    if grades:
        products = [product for product in products if product.grade in grades]

    # A missing tier price cannot be a safe automatic selection.
    products = [product for product in products if product.tier_price is not None]
    if not products:
        return Resolution(product=None, candidates=())
    if len(products) == 1:
        return Resolution(product=products[0], candidates=())
    pack_sizes = {normalize(product.pack_size or "") for product in products}
    issue = (
        "MULTIPLE_GRADES"
        if len({product.grade for product in products if product.grade}) > 1
        and len(pack_sizes) == 1
        else "MULTIPLE_PACK_SIZES"
    )
    return Resolution(product=None, candidates=tuple(products), issue_code=issue)


def candidate_payload(product: CatalogProduct) -> dict[str, Any]:
    return {
        "sku_id": product.sku_id,
        "family_id": product.family_id,
        "display_name": product.name,
        "pack_size": product.pack_size,
        "grade": product.grade,
        "base_unit": product.base_unit,
        "tier_unit_price": format(product.tier_price, ".2f") if product.tier_price else "0.00",
        "available_qty": product.available_qty,
    }


def _exclusive_memory_line(line: str, catalog: Catalog) -> CatalogAlias | None:
    """Only a line that is just one confirmed alias + qty may bypass the provider."""
    hits = [alias for alias in catalog.aliases if exact_phrase(alias.phrase, line)]
    if len(hits) != 1:
        return None
    normalized = normalize(line)
    if re.search(r"[,;+&]", normalized):
        return None
    if re.search(r"(?<![a-z])(?:dan|and)(?![a-z])", normalized):
        return None
    if re.search(r"(?<![a-z])(?:kalau|if|rm|price|harga|stock)(?![a-z])", normalized):
        return None
    alias = hits[0]
    if len(normalized.split()) > len(normalize(alias.phrase).split()) + 4:
        return None
    return alias


def memory_rows(masked_text: str, catalog: Catalog) -> tuple[list[RawRow], bool]:
    """Return alias-backed rows and whether they cover every non-empty line."""
    rows: list[RawRow] = []
    lines = [line for line in masked_text.splitlines() if line.strip()]
    for line in lines:
        stripped = line.strip()
        hit = _exclusive_memory_line(stripped, catalog)
        if hit is None:
            continue
        if hit.target_type == "SKU" and hit.product_id:
            product = catalog.by_sku.get(hit.product_id)
            if product is None:
                continue
            family_id = product.family_id
            uom = product.base_unit
            pack_size = product.pack_size
        elif hit.target_type == "FAMILY" and hit.family_id:
            family_id = hit.family_id
            products = [p for p in catalog.products if p.family_id == family_id]
            if len(products) != 1:
                continue
            product = products[0]
            uom = product.base_unit
            pack_size = product.pack_size
        else:
            continue
        qty, reason, _, _ = quantity_evidence(stripped)
        if qty is None or reason:
            continue
        rows.append(
            RawRow(
                span=stripped,
                qty=qty,
                uom=uom,
                fam=family_id,
                pack_size=pack_size,
                memory=True,
                alias=hit.record(),
            )
        )
    return rows, bool(rows) and len(rows) == len(lines)


def merge_memory(raw: RawExtraction, memory: list[RawRow]) -> tuple[RawExtraction, bool]:
    if not memory:
        return raw, False
    rows: list[RawRow] = []
    used = False
    for row in raw.rows:
        hit = next(
            (
                item
                for item in memory
                if item.alias and exact_phrase(item.alias["phrase"], row.span)
            ),
            None,
        )
        if hit is None:
            rows.append(row)
            continue
        used = True
        rows.append(replace(hit, conds=row.conds))
    for item in memory:
        if not any(
            item.span == row.span or item.span in row.span or row.span in item.span
            for row in raw.rows
        ):
            rows.append(item)
            used = True
    return RawExtraction(rows=tuple(rows), ignored_spans=raw.ignored_spans), used
