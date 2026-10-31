"""B03 recovery with both hash-verified tenant seeds and synthetic role sessions."""

from decimal import Decimal

import pytest
from test_b03_manual_recovery import EmptyProvider, _state
from test_catalog import _headers
from test_catalog import catalog_client as catalog_client

from app.db import connect

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("tenant", ["T1", "T2"])
@pytest.mark.parametrize("role", ["CLERK", "OWNER"])
def test_canonical_directory_to_manual_recovery_do_and_tenant_isolation(
    catalog_client, db_settings, tenant, role
):
    client = catalog_client
    client.app.state.extraction_provider = EmptyProvider()
    headers = _headers(tenant, role)
    with connect(db_settings) as conn:
        customer, tier = conn.execute(
            "SELECT customer_id, tier FROM customers "
            "WHERE tenant_id=%s AND active AND credit_flag='NONE' ORDER BY customer_id LIMIT 1",
            (tenant,),
        ).fetchone()
        sku, unit, price, stock = conn.execute(
            "SELECT p.product_id, p.base_unit, tp.unit_price_rm, i.available_qty "
            "FROM products p JOIN customer_tier_prices tp USING (tenant_id,product_id) "
            "JOIN inventory i USING (tenant_id,product_id) "
            "JOIN product_families f USING (tenant_id,family_id) "
            "WHERE p.tenant_id=%s AND p.active AND f.active AND tp.tier=%s "
            "AND i.available_qty > 0 ORDER BY tp.unit_price_rm,p.product_id LIMIT 1",
            (tenant, tier),
        ).fetchone()
    products = client.get("/api/v1/catalog/products", headers=headers)
    assert products.status_code == 200, products.text
    assert sku in {product["sku_id"] for product in products.json()["items"]}
    parsed = client.post(
        "/api/v1/orders/parse-draft",
        headers=headers,
        json={"customer_id": customer, "message_text": "Please add the confirmed product"},
    )
    assert parsed.status_code == 200, parsed.text
    draft = parsed.json()
    assert draft["lines"] == []
    before = _state(db_settings)
    path = f"/api/v1/orders/drafts/{draft['draft_id']}"
    saved = client.put(
        path + "/lines",
        headers=headers,
        json={
            "expected_version": draft["version"],
            "lines": [
                {
                    "client_line_ref": f"manual-{tenant}-{role}",
                    "sku_id": sku,
                    "confirmed_qty": 1,
                    "uom": unit,
                    "match_source": "MANUAL_SELECTED",
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    draft = saved.json()
    assert draft["status"] == "READY_FOR_APPROVAL"
    assert draft["lines"][0]["tier_unit_price"] == format(price, ".2f")
    assert Decimal(draft["totals"]["order_total"]) == price
    after = _state(db_settings)
    for table in ("inventory", "delivery_orders", "approval_requests", "inbound_messages"):
        assert after[table] == before[table], table
    other = "T2" if tenant == "T1" else "T1"
    assert client.get(path, headers=_headers(other)).status_code == 404
    assert (
        client.put(
            path + "/lines", headers=_headers(other), json={"expected_version": 2, "lines": []}
        ).status_code
        == 404
    )
    approved = client.post(
        f"/api/v1/orders/{draft['draft_id']}/approve",
        headers=headers,
        json={"expected_version": draft["version"]},
    )
    assert approved.status_code == 200, approved.text
    do = approved.json()
    assert do["lines"][0]["sku_id"] == sku
    assert do["lines"][0]["quantity"] == 1
    assert Decimal(do["final_total_rm"]) == price
    assert (
        client.get(
            f"/api/v1/delivery-orders/{do['do_number']}", headers=_headers(other)
        ).status_code
        == 404
    )
    warehouse = client.get(
        f"/api/v1/warehouse/delivery-orders/{do['do_number']}",
        headers=_headers(tenant, "WAREHOUSE"),
    )
    assert warehouse.status_code == 200, warehouse.text
    assert warehouse.json()["items"][0]["sku_id"] == sku
    with connect(db_settings) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE tenant_id=%s AND product_id=%s",
            (tenant, sku),
        ).fetchone() == (stock - 1,)
