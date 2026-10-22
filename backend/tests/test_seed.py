import hashlib

import pytest

from app.auth import hash_token
from app.config import Settings
from app.db import connect
from app.migrations import migrate
from app.seed import SeedError, load_seed

pytestmark = pytest.mark.integration

TENANT = "T1"
SEED_SQL = """
INSERT INTO tenants (tenant_id, name, amount_threshold_rm)
VALUES ('T1', 'Tenant One', 1500.00);

INSERT INTO users (user_id, tenant_id, display_name, demo_token_hash, role)
VALUES ('USR_T1_CLERK', 'T1', 'T1 Clerk', '{token_hash}', 'CLERK');

INSERT INTO product_families (family_id, tenant_id, family_name)
VALUES ('FAM_MILO', 'T1', 'Milo');

INSERT INTO products (product_id, tenant_id, family_id, sku_code, name, base_unit)
VALUES ('SKU_MILO_1KG', 'T1', 'FAM_MILO', 'SKU_MILO_1KG', 'Milo 1kg', 'bag');

INSERT INTO customer_tier_prices (tenant_id, product_id, tier, unit_price_rm)
VALUES ('T1', 'SKU_MILO_1KG', 'A', 18.00);

INSERT INTO inventory (tenant_id, product_id, available_qty)
VALUES ('T1', 'SKU_MILO_1KG', 5);
""".format(token_hash=hash_token("tok_t1_clerk"))


def _args(path, *, products=1, inventory=5, sha=None, version="T1-0.1"):
    return {
        "tenant": TENANT,
        "seed_path": path,
        "seed_version": version,
        "expect_sha256": sha or hashlib.sha256(path.read_bytes()).hexdigest(),
        "expect_products": products,
        "expect_inventory": inventory,
    }


def _write(tmp_path, text=SEED_SQL):
    path = tmp_path / "seed_T1.sql"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_seed_then_repeat_is_idempotent(db_settings, tmp_path):
    migrate(db_settings)
    path = _write(tmp_path)

    first = load_seed(db_settings, **_args(path))
    assert first.status == "loaded"
    assert first.product_count == 1
    assert first.inventory_total == 5

    second = load_seed(db_settings, **_args(path))
    assert second.status == "already_loaded"

    with connect(db_settings) as conn:
        assert conn.execute("SELECT count(*) FROM products").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM inventory").fetchone() == (1,)
        assert conn.execute(
            "SELECT seed_version, product_count, inventory_total "
            "FROM kiraorder_meta.seed_manifest WHERE tenant_id = 'T1'"
        ).fetchone() == ("T1-0.1", 1, 5)


def test_checksum_mismatch_is_rejected_before_database(db_settings, tmp_path):
    migrate(db_settings)
    path = _write(tmp_path)
    args = _args(path, sha="0" * 64)

    with pytest.raises(SeedError, match="checksum"):
        load_seed(db_settings, **args)


def test_count_mismatch_rolls_back_seed_and_manifest(db_settings, tmp_path):
    migrate(db_settings)
    path = _write(tmp_path)
    args = _args(path, products=2)

    with pytest.raises(SeedError, match="counts"):
        load_seed(db_settings, **args)

    with connect(db_settings) as conn:
        assert conn.execute("SELECT to_regclass('public.tenants')").fetchone() != (None,)
        assert conn.execute("SELECT count(*) FROM tenants").fetchone() == (0,)
        assert conn.execute("SELECT to_regclass('kiraorder_meta.seed_manifest')").fetchone() == (
            None,
        )


def test_existing_tenant_without_manifest_is_not_adopted(db_settings, tmp_path):
    migrate(db_settings)
    path = _write(tmp_path)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, amount_threshold_rm) "
            "VALUES ('T1', 'Existing', 100)"
        )

    with pytest.raises(SeedError, match="without a seed manifest"):
        load_seed(db_settings, **_args(path))


def test_seed_file_cannot_contain_transaction_control(tmp_path):
    path = _write(tmp_path, "BEGIN;\n" + SEED_SQL + "\nCOMMIT;\n")
    with pytest.raises(SeedError, match="transaction"):
        load_seed(
            Settings(_env_file=None),
            **_args(path),
        )
