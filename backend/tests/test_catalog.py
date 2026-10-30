"""B02 acceptance against disposable PostgreSQL and the unchanged canonical seeds."""

import json

import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.auth import hash_token
from app.config import REPO_ROOT
from app.db import connect
from app.main import create_app
from app.migrations import migrate
from app.seed import load_seed

pytestmark = pytest.mark.integration
PATH = "/api/v1/catalog/products"
SEED_DIR = REPO_ROOT / "data" / "seed"
SEEDS = json.loads((SEED_DIR / "SEED_MANIFEST.json").read_text(encoding="utf-8"))


def _headers(tenant="T1", role="CLERK"):
    # Synthetic test credentials replace hashes only in the disposable test DB.
    return {"Authorization": f"Bearer b02-test-{tenant}-{role}"}


@pytest.fixture
def catalog_client(db_settings):
    migrate(db_settings)
    for tenant in ("T1", "T2"):
        meta = SEEDS["tenants"][tenant]
        load_seed(
            db_settings,
            tenant=tenant,
            seed_path=SEED_DIR / f"{tenant}_seed.sql",
            seed_version=meta["seed_version"],
            expect_sha256=meta["sql_sha256"],
            expect_products=meta["products"],
            expect_inventory=meta["inventory_sum"],
        )
        with connect(db_settings) as conn:
            for role in ("CLERK", "OWNER", "WAREHOUSE"):
                conn.execute(
                    "UPDATE users SET demo_token_hash=%s WHERE tenant_id=%s AND role=%s",
                    (hash_token(f"b02-test-{tenant}-{role}"), tenant, role),
                )
    with TestClient(create_app(db_settings)) as client:
        yield client


@pytest.mark.parametrize("tenant,count", [("T1", 40), ("T2", 16)])
@pytest.mark.parametrize("role", ["CLERK", "OWNER"])
def test_full_canonical_directory_without_commercial_fields(
    catalog_client, db_settings, tenant, count, role
):
    response = catalog_client.get(PATH, headers=_headers(tenant, role))
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    body = response.json()
    assert set(body) == {"items", "limit", "truncated"}
    assert body["limit"] == 100
    assert body["truncated"] is False
    assert len(body["items"]) == count
    with connect(db_settings) as conn:
        expected = conn.execute(
            "SELECT product_id, name, pack_size, grade, base_unit FROM products "
            "WHERE tenant_id=%s AND active=true",
            (tenant,),
        ).fetchall()
    expected.sort(key=lambda row: row[0])
    assert body["items"] == [
        dict(zip(("sku_id", "display_name", "pack_size", "grade", "base_unit"), row, strict=True))
        for row in expected
    ]


@pytest.mark.parametrize("tenant", ["T1", "T2"])
def test_warehouse_forbidden_even_with_spoofed_role(catalog_client, tenant):
    response = catalog_client.get(PATH + "?role=OWNER", headers=_headers(tenant, "WAREHOUSE"))
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN_ACTION"
    assert response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic ignored"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer b02-unknown-token"},
    ],
)
def test_missing_malformed_and_unknown_authentication(catalog_client, headers):
    response = catalog_client.get(PATH, headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"


def test_inactive_identity_cannot_read_catalog(catalog_client, db_settings):
    with connect(db_settings) as conn:
        conn.execute("UPDATE users SET active=false WHERE user_id='USR_T1_CLERK'")
    response = catalog_client.get(PATH, headers=_headers())
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.parametrize("tenant,other,count", [("T1", "T2", 40), ("T2", "T1", 16)])
def test_tenant_is_taken_only_from_authenticated_identity(catalog_client, tenant, other, count):
    expected = catalog_client.get(PATH, headers=_headers(tenant)).json()
    response = catalog_client.get(
        PATH + f"?tenant_id={other}&role=OWNER&limit=1&q=no-such-product",
        headers={**_headers(tenant), "X-Tenant-ID": other, "X-Role": "OWNER"},
    )
    assert response.status_code == 200
    assert response.json() == expected
    assert len(response.json()["items"]) == count


def test_inactive_product_excluded_without_affecting_other_tenant(catalog_client, db_settings):
    with connect(db_settings) as conn:
        conn.execute("UPDATE products SET active=false WHERE product_id='SKU_MILO_1KG'")
    response = catalog_client.get(PATH, headers=_headers())
    assert response.status_code == 200
    assert len(response.json()["items"]) == 39
    assert "SKU_MILO_1KG" not in {item["sku_id"] for item in response.json()["items"]}
    assert len(catalog_client.get(PATH, headers=_headers("T2")).json()["items"]) == 16


def test_empty_directory_is_explicit(catalog_client, db_settings):
    with connect(db_settings) as conn:
        conn.execute("UPDATE products SET active=false WHERE tenant_id='T1'")
    response = catalog_client.get(PATH, headers=_headers())
    assert response.status_code == 200
    assert response.json() == {"items": [], "limit": 100, "truncated": False}


@pytest.mark.parametrize("count,truncated", [(100, False), (101, True)])
def test_fixed_cap_is_reported_without_silent_truncation(
    catalog_client, db_settings, count, truncated
):
    with connect(db_settings) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO products "
                "(product_id, tenant_id, family_id, sku_code, name, pack_size, grade, base_unit) "
                "VALUES (%s, 'T1', 'FAM_MILO', %s, 'B02 extra', '1kg', 'test-grade', 'bag')",
                [(f"B02_{i:03}", f"B02_{i:03}") for i in range(count - 40)],
            )
    response = catalog_client.get(PATH, headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == body["limit"] == 100
    assert body["truncated"] is truncated
    ids = [item["sku_id"] for item in body["items"]]
    assert ids == sorted(ids)
    assert body == catalog_client.get(PATH, headers=_headers()).json()
    assert body["items"][0]["grade"] == "test-grade"


def _public_snapshot(settings):
    with connect(settings) as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ).fetchall()
        return {
            table: conn.execute(
                sql.SQL("SELECT to_jsonb(r) FROM {} r ORDER BY to_jsonb(r)::text").format(
                    sql.Identifier(table)
                )
            ).fetchall()
            for (table,) in tables
        }


def test_repeated_reads_leave_all_business_tables_unchanged(catalog_client, db_settings):
    before = _public_snapshot(db_settings)
    for tenant in ("T1", "T2"):
        for role in ("CLERK", "OWNER", "WAREHOUSE"):
            response = catalog_client.get(PATH, headers=_headers(tenant, role))
            assert response.status_code == (403 if role == "WAREHOUSE" else 200)
    assert _public_snapshot(db_settings) == before
