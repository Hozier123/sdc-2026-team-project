import json

import pytest

from app.config import REPO_ROOT
from app.db import connect
from app.migrations import migrate
from app.seed import load_seed

pytestmark = pytest.mark.integration

SEED_DIR = REPO_ROOT / "data" / "seed"
MANIFEST = json.loads((SEED_DIR / "SEED_MANIFEST.json").read_text(encoding="utf-8"))


def _load(settings, tenant: str):
    meta = MANIFEST["tenants"][tenant]
    return load_seed(
        settings,
        tenant=tenant,
        seed_path=SEED_DIR / f"{tenant}_seed.sql",
        seed_version=meta["seed_version"],
        expect_sha256=meta["sql_sha256"],
        expect_products=meta["products"],
        expect_inventory=meta["inventory_sum"],
    )


def test_canonical_t1_t2_seed_loads_counts_and_is_idempotent(db_settings):
    migrate(db_settings)
    t1 = _load(db_settings, "T1")
    t2 = _load(db_settings, "T2")
    assert (t1.status, t2.status) == ("loaded", "loaded")

    with connect(db_settings) as conn:
        for tenant, expected in (
            (
                "T1",
                {
                    "users": 3,
                    "customers": 8,
                    "product_families": 25,
                    "family_aliases": 50,
                    "products": 40,
                    "uom_aliases": 26,
                    "customer_tier_prices": 80,
                    "inventory": 40,
                    "alias_cache": 0,
                },
            ),
            (
                "T2",
                {
                    "users": 3,
                    "customers": 5,
                    "product_families": 10,
                    "family_aliases": 30,
                    "products": 16,
                    "uom_aliases": 30,
                    "customer_tier_prices": 32,
                    "inventory": 16,
                    "alias_cache": 2,
                },
            ),
        ):
            for table, count in expected.items():
                actual = conn.execute(
                    f"SELECT count(*) FROM {table} WHERE tenant_id=%s", (tenant,)
                ).fetchone()[0]
                assert actual == count, (tenant, table, actual, count)

        assert conn.execute(
            "SELECT count(*) FROM users WHERE tenant_id IN ('T1','T2')"
        ).fetchone() == (6,)
        assert conn.execute(
            "SELECT sum(available_qty) FROM inventory WHERE tenant_id='T1'"
        ).fetchone() == (795,)
        assert conn.execute(
            "SELECT sum(available_qty) FROM inventory WHERE tenant_id='T2'"
        ).fetchone() == (450,)

    assert _load(db_settings, "T1").status == "already_loaded"
    assert _load(db_settings, "T2").status == "already_loaded"

    with connect(db_settings) as conn:
        assert conn.execute("SELECT count(*) FROM products").fetchone() == (56,)
        assert conn.execute("SELECT count(*) FROM kiraorder_meta.seed_manifest").fetchone() == (2,)
