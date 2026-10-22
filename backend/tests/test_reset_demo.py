"""Tests for the database-level trial reset (Gate 0 plan A)."""

import json
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from app.config import Settings
from app.migrations import migrate
from tools.reset_demo import (
    ResetError,
    build_parser,
    check_template,
    collect_evidence,
    ensure_safe_names,
    main,
    rebuild,
    verify_target,
    with_dbname,
    write_evidence,
)

SEED_SQL = """
INSERT INTO tenants (tenant_id, name, amount_threshold_rm)
VALUES ('T1', 'Sinaran Food Supply', 1500.00);
INSERT INTO users (user_id, tenant_id, display_name, demo_token_hash, role)
VALUES ('USR_T1_CLERK', 'T1', 'T1 Clerk', 'synthetic-hash-clerk', 'CLERK');
INSERT INTO product_families (family_id, tenant_id, family_name)
VALUES ('FAM_MILO', 'T1', 'Milo 美禄');
INSERT INTO products (product_id, tenant_id, family_id, sku_code, name, base_unit)
VALUES ('SKU_MILO_1KG', 'T1', 'FAM_MILO', 'SKU_MILO_1KG', 'Milo 美禄', 'bag');
INSERT INTO customer_tier_prices (tenant_id, product_id, tier, unit_price_rm)
VALUES ('T1', 'SKU_MILO_1KG', 'A', 18.00), ('T1', 'SKU_MILO_1KG', 'B', 19.00);
INSERT INTO inventory (tenant_id, product_id, available_qty)
VALUES ('T1', 'SKU_MILO_1KG', 5);
"""

DO_CHAIN_SQL = """
INSERT INTO customers (customer_id, tenant_id, name, tier)
VALUES ('CUS_ALI', 'T1', 'Restoran Ali', 'A');
INSERT INTO orders (tenant_id, draft_id, customer_id, status, ai_mode)
VALUES ('T1', 'DRF_001', 'CUS_ALI', 'DO_GENERATED', 'ALIAS_ONLY');
INSERT INTO draft_versions (tenant_id, draft_id, version, snapshot, created_by)
VALUES ('T1', 'DRF_001', 1, '{}'::jsonb, 'USR_T1_CLERK');
INSERT INTO delivery_orders (
    do_number, tenant_id, draft_id, draft_version, customer_id, lines,
    final_total_rm, prepared_by, approved_by, approval_mode, reply_draft
)
VALUES (
    'DO-20261022-0001', 'T1', 'DRF_001', 1, 'CUS_ALI', '[]'::jsonb,
    18.00, 'USR_T1_CLERK', 'USR_T1_CLERK', 'DIRECT', '{}'::jsonb
);
INSERT INTO audit_logs (
    audit_id, tenant_id, draft_id, draft_version, do_number, actor_user_id, actor_role, action
)
VALUES ('AUD_001', 'T1', 'DRF_001', 1, 'DO-20261022-0001', 'USR_T1_CLERK', 'CLERK', 'DO_GENERATED');
INSERT INTO field_diffs (
    audit_id, draft_version, line_id, field_path, before_value, after_value, source, reason_code
)
VALUES ('AUD_001', 1, 'LIN_001', 'quantity', '4'::jsonb, '5'::jsonb, 'CLERK', 'MANUAL_EDIT');
"""


def _args(admin_url: str, template: str, target: str) -> object:
    return build_parser().parse_args(
        [
            "--admin-url",
            admin_url,
            "--template",
            template,
            "--target",
            target,
            "--expect-seed-version",
            "T1-test",
            "--expect-seed-sha256",
            "a" * 64,
            "--expect-products",
            "1",
            "--expect-families",
            "1",
            "--expect-customers",
            "0",
            "--expect-prices",
            "2",
            "--expect-price-a",
            "18.00",
            "--expect-price-b",
            "19.00",
            "--expect-inventory",
            "5",
            "--expect-alias-cache",
            "0",
        ]
    )


def test_rejects_same_database_name():
    with pytest.raises(ResetError):
        ensure_safe_names("kiraorder_trial", "kiraorder_trial", False)


def test_rejects_system_database():
    with pytest.raises(ResetError):
        ensure_safe_names("postgres", "kiraorder_t1_seed", False)


def test_rejects_unsafe_target_name():
    with pytest.raises(ResetError):
        ensure_safe_names("production", "kiraorder_t1_seed", False)
    ensure_safe_names("production", "kiraorder_t1_seed", True)


def test_apply_requires_pinned_seed(capsys):
    code = main(["--admin-url", "postgresql://user@127.0.0.1/db", "--apply"])
    assert code == 2
    assert "expect-seed-version" in capsys.readouterr().err


def test_mode_is_required(capsys):
    code = main(["--admin-url", "postgresql://user@127.0.0.1/db"])
    assert code == 2
    assert "--dry-run" in capsys.readouterr().err


@pytest.fixture
def admin():
    url = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if not url:
        pytest.fail("Integration tests require TEST_DATABASE_ADMIN_URL; see backend/README.md")
    with psycopg.connect(url, autocommit=True) as connection:
        yield connection


def _create(admin: psycopg.Connection, name: str) -> None:
    admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))


def _drop(admin: psycopg.Connection, name: str) -> None:
    admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def _make_template(admin: psycopg.Connection, admin_url: str, name: str) -> None:
    _create(admin, name)
    settings = Settings(_env_file=None, database_url=with_dbname(admin_url, name))
    migrate(settings)
    with psycopg.connect(
        settings.database_url.get_secret_value(),
        autocommit=True,
        cursor_factory=psycopg.ClientCursor,
    ) as conn:
        conn.execute(SEED_SQL)
        conn.execute(
            "CREATE TABLE kiraorder_meta.seed_manifest ("
            "tenant_id text PRIMARY KEY, seed_version text NOT NULL, seed_sha256 text NOT NULL,"
            "product_count integer NOT NULL, inventory_total integer NOT NULL,"
            "family_count integer NOT NULL, customer_count integer NOT NULL,"
            "price_count integer NOT NULL, price_total_a numeric(12,2) NOT NULL,"
            "price_total_b numeric(12,2) NOT NULL,"
            "applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.execute(
            "INSERT INTO kiraorder_meta.seed_manifest "
            "(tenant_id, seed_version, seed_sha256, product_count, inventory_total,"
            " family_count, customer_count, price_count, price_total_a, price_total_b) "
            "VALUES ('T1', 'T1-test', %s, 1, 5, 1, 0, 2, 18.00, 19.00)",
            ("a" * 64,),
        )


@pytest.mark.integration
def test_rebuilds_target_from_pinned_template(admin):
    suffix = uuid.uuid4().hex[:10]
    template, target = f"kiraorder_{suffix}_seed", f"kiraorder_trial_{suffix}"
    admin_url = os.environ["TEST_DATABASE_ADMIN_URL"]
    try:
        _make_template(admin, admin_url, template)
        args = _args(admin_url, template, target)

        info = check_template(args, admin)
        assert info["snapshot"]["inventory_total"] == 5

        rebuild(admin, template, target)
        verified = verify_target(args)
        assert verified["snapshot"]["inventory_total"] == 5
        assert verified["alias_cache"] == 0
        assert all(value == 0 for value in verified["flow_rows"].values())

        # Idempotent: rebuilding again yields the same clean state.
        rebuild(admin, template, target)
        assert verify_target(args)["snapshot"]["inventory_total"] == 5
    finally:
        _drop(admin, target)
        _drop(admin, template)


@pytest.mark.integration
def test_template_version_mismatch_is_rejected(admin):
    suffix = uuid.uuid4().hex[:10]
    template = f"kiraorder_{suffix}_seed"
    admin_url = os.environ["TEST_DATABASE_ADMIN_URL"]
    try:
        _make_template(admin, admin_url, template)
        args = _args(admin_url, template, f"kiraorder_trial_{suffix}")
        args.expect_seed_version = "T1-other"
        with pytest.raises(ResetError, match="seed version"):
            check_template(args, admin)
    finally:
        _drop(admin, template)


@pytest.mark.integration
def test_evidence_export_captures_do_and_audit(admin, tmp_path):
    suffix = uuid.uuid4().hex[:10]
    name = f"kiraorder_trial_{suffix}"
    admin_url = os.environ["TEST_DATABASE_ADMIN_URL"]
    _create(admin, name)
    url = with_dbname(admin_url, name)
    try:
        migrate(Settings(_env_file=None, database_url=url))
        with psycopg.connect(url, autocommit=True, cursor_factory=psycopg.ClientCursor) as conn:
            conn.execute(SEED_SQL + DO_CHAIN_SQL)

        payload = collect_evidence(url, "T1")
        assert len(payload["delivery_orders"]) == 1
        assert payload["delivery_orders"][0]["do_number"] == "DO-20261022-0001"
        assert len(payload["audit_logs"]) == 1
        assert len(payload["field_diffs"]) == 1
        assert payload["row_counts"]["approval_requests"] == 0

        files = write_evidence(Path(tmp_path), "20261022T120000", name, payload)
        assert all(Path(path).is_file() for path in files)
        saved = json.loads(Path(files[0]).read_text(encoding="utf-8"))
        assert float(saved["delivery_orders"][0]["final_total_rm"]) == 18.0
    finally:
        _drop(admin, name)
