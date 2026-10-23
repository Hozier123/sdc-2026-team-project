"""Build the tenant family catalog injected into the AI adapter.

The catalog is derived from the same tenant tables used by the resolver:
active product families plus their configured family aliases. It is not a
second tenant mapping and contains no hard-coded family IDs.
"""

from __future__ import annotations


def load_family_catalog(conn, tenant: str) -> dict[str, list[str]]:
    """Return ``family_id -> [family_name, aliases...]`` for one tenant.

    Only active families are included. Alias phrases use the stored normalized
    form; the family name is kept as the first prompt phrase.
    """
    families = conn.execute(
        "SELECT family_id, family_name FROM product_families "
        "WHERE tenant_id=%s AND active=true ORDER BY family_id",
        (tenant,),
    ).fetchall()
    aliases = conn.execute(
        "SELECT family_id, phrase_norm FROM family_aliases "
        "WHERE tenant_id=%s ORDER BY family_id, phrase_norm",
        (tenant,),
    ).fetchall()

    catalog: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for family_id, family_name in families:
        key = str(family_name).strip()
        catalog[family_id] = [key] if key else []
        seen[family_id] = {key} if key else set()
    for family_id, phrase in aliases:
        if family_id not in catalog:
            continue
        key = str(phrase).strip()
        if not key or key in seen[family_id]:
            continue
        catalog[family_id].append(key)
        seen[family_id].add(key)
    return catalog
