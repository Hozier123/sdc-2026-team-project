import json

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.config import REPO_ROOT
from app.db import connect
from app.main import create_app
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
                    "alias_cache": 2,
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
        assert conn.execute(
            "SELECT alias_id, phrase, product_id FROM alias_cache "
            "WHERE tenant_id='T1' ORDER BY alias_id"
        ).fetchall() == [
            ("ALS_CACHE_RASA_001", "老规矩辣椒酱", "SKU_CILI_1KG"),
            ("ALS_CACHE_RASA_002", "生抽王", "SKU_KICAP_CTN"),
        ]

    assert _load(db_settings, "T1").status == "already_loaded"
    assert _load(db_settings, "T2").status == "already_loaded"

    with connect(db_settings) as conn:
        assert conn.execute("SELECT count(*) FROM products").fetchone() == (56,)
        assert conn.execute("SELECT count(*) FROM kiraorder_meta.seed_manifest").fetchone() == (2,)


def test_canonical_seed_identity_and_order_flow(db_settings):
    migrate(db_settings)
    _load(db_settings, "T1")
    _load(db_settings, "T2")

    # The canonical plaintext tokens are delivered privately. This test replaces
    # only the test database hash so the seed data path can be exercised in CI.
    token = "canonical-test-clerk"
    with connect(db_settings) as conn:
        conn.execute(
            "UPDATE users SET demo_token_hash=%s WHERE user_id='USR_T1_CLERK'",
            (hash_token(token),),
        )
        sku_id, unit, price, available = conn.execute(
            "SELECT p.product_id, p.base_unit, ctp.unit_price_rm, i.available_qty "
            "FROM products p "
            "JOIN customer_tier_prices ctp "
            "  ON ctp.tenant_id=p.tenant_id AND ctp.product_id=p.product_id "
            "JOIN inventory i "
            "  ON i.tenant_id=p.tenant_id AND i.product_id=p.product_id "
            "WHERE p.tenant_id='T1' AND ctp.tier='A' AND i.available_qty > 0 "
            "ORDER BY ctp.unit_price_rm ASC LIMIT 1"
        ).fetchone()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(create_app(db_settings)) as client:
        me = client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["tenant"]["id"] == "T1"
        assert me.json()["role"] == "CLERK"

        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=headers,
            json={"customer_id": "CUS_ALI", "message_text": "Milo 5 ctn"},
        )
        assert parsed.status_code == 200, parsed.text
        draft_id = parsed.json()["draft_id"]

        saved = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=headers,
            json={
                "expected_version": 1,
                "lines": [
                    {
                        "client_line_ref": "canonical-1",
                        "sku_id": sku_id,
                        "confirmed_qty": 1,
                        "uom": unit,
                        "match_source": "MANUAL_SELECTED",
                    }
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["lines"][0]["tier_unit_price"] == str(price)

        approved = client.post(
            f"/api/v1/orders/{draft_id}/approve",
            headers=headers,
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        do = approved.json()
        fetched = client.get(f"/api/v1/delivery-orders/{do['do_number']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["lines"][0]["sku_id"] == sku_id

    with connect(db_settings) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE tenant_id='T1' AND product_id=%s",
            (sku_id,),
        ).fetchone() == (available - 1,)
