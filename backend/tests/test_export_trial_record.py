"""Tests for the line-level DO export used by trial records."""

import csv
import json
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from app.config import Settings
from app.migrations import migrate
from tools.export_trial_record import (
    ExportError,
    build_export,
    fetch_orders,
    load_fixture,
    load_products_file,
    main,
    sha256_file,
    verify_products_file,
    write_outputs,
)

DO = {
    "do_number": "DO-20261021-0003",
    "customer_id": "CUS_ALI",
    "final_total_rm": "360.00",
    "lines": [
        {
            "line_id": "LIN_001",
            "sku_id": "SKU_OIL_5KG",
            "display_name": "Minyak masak 食用油",
            "quantity": 3,
            "unit": "btl",
            "applied_unit_price": "120.00",
            "subtotal_rm": "360.00",
        }
    ],
}


def _db_url(admin_url: str, name: str) -> str:
    return admin_url.rsplit("/", 1)[0] + "/" + name


def test_lines_are_labelled_in_array_order():
    do = dict(DO)
    do["lines"] = [
        {
            **DO["lines"][0],
            "sku_id": "SKU_A",
            "quantity": 1,
            "applied_unit_price": "10.00",
            "subtotal_rm": "10.00",
        },
        {
            **DO["lines"][0],
            "sku_id": "SKU_B",
            "quantity": 2,
            "applied_unit_price": "10.00",
            "subtotal_rm": "20.00",
        },
    ]
    do["final_total_rm"] = "30.00"

    export = build_export("TEST-01", "T1", do)

    assert [row["line_no"] for row in export.rows] == ["L1", "L2"]
    assert [row["sku_id"] for row in export.rows] == ["SKU_A", "SKU_B"]
    assert export.totals_match is True


def test_subtotal_mismatch_is_flagged():
    do = dict(DO)
    do["lines"] = [{**DO["lines"][0], "subtotal_rm": "350.00"}]
    do["final_total_rm"] = "350.00"

    export = build_export("TEST-01", "T1", do)

    assert export.totals_match is False
    assert "subtotal" in export.errors[0]


def test_total_mismatch_is_flagged():
    do = dict(DO)
    do["final_total_rm"] = "999.00"

    export = build_export("TEST-01", "T1", do)

    assert export.totals_match is False
    assert "final_total_rm" in export.errors[0]


def test_missing_required_field_is_rejected():
    do = dict(DO)
    do["lines"] = [{"sku_id": "SKU_A", "quantity": 1, "subtotal_rm": "10.00"}]

    with pytest.raises(ExportError, match="missing applied_unit_price"):
        build_export("TEST-01", "T1", do)


def test_outputs_include_total_row_and_json(tmp_path):
    export = build_export("TEST-01", "T1", DO)

    csv_path, json_path = write_outputs(tmp_path, "TEST-01", [export], total_row=True)

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
    assert rows[0]["line_no"] == "L1"
    assert rows[0]["applied_unit_price"] == "120.00"
    assert rows[-1]["line_no"] == "合计"
    assert rows[-1]["subtotal_rm"] == "360.00"

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["totals_match"] is True
    assert payload["orders"][0]["lines"][0]["sku_id"] == "SKU_OIL_5KG"


def test_cli_fixture_mode(tmp_path):
    fixture = tmp_path / "delivery_order.json"
    fixture.write_text(json.dumps({"method": "GET", "status": 200, "body": DO}), encoding="utf-8")

    code = main(
        [
            "--fixture",
            str(fixture),
            "--case-id",
            "TEST-01",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    assert code == 0
    assert (tmp_path / "out" / "TEST-01_do_lines.csv").is_file()
    assert (tmp_path / "out" / "TEST-01_do_lines.json").is_file()


def test_cli_mismatch_exits_2(tmp_path):
    fixture = tmp_path / "delivery_order.json"
    bad = {**DO, "final_total_rm": "999.00"}
    fixture.write_text(json.dumps({"body": bad}), encoding="utf-8")

    code = main(
        ["--fixture", str(fixture), "--case-id", "TEST-01", "--out-dir", str(tmp_path / "out")]
    )

    assert code == 2


def test_cli_rejects_unsafe_case_id(tmp_path):
    fixture = tmp_path / "delivery_order.json"
    fixture.write_text(json.dumps({"body": DO}), encoding="utf-8")

    code = main(["--fixture", str(fixture), "--case-id", "../escape", "--out-dir", str(tmp_path)])

    assert code == 1


def test_fixture_without_lines_is_rejected(tmp_path):
    fixture = tmp_path / "bad.json"
    fixture.write_text(json.dumps({"body": {"do_number": "DO-1"}}), encoding="utf-8")

    with pytest.raises(ExportError):
        load_fixture(fixture)


@pytest.fixture
def admin():
    url = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if not url:
        pytest.fail("Integration tests require TEST_DATABASE_ADMIN_URL; see backend/README.md")
    with psycopg.connect(url, autocommit=True) as connection:
        yield connection


@pytest.mark.integration
def test_exports_real_do_from_database(admin, tmp_path):
    suffix = uuid.uuid4().hex[:10]
    name = f"kiraorder_trial_{suffix}"
    admin_url = os.environ["TEST_DATABASE_ADMIN_URL"]
    admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    url = _db_url(admin_url, name)
    try:
        migrate(Settings(_env_file=None, database_url=url))
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, amount_threshold_rm) "
                "VALUES ('T1', 'Sinaran Food Supply', 1500.00)"
            )
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, display_name, demo_token_hash, role) "
                "VALUES ('USR_T1_CLERK', 'T1', 'T1 Clerk', 'synthetic-hash', 'CLERK')"
            )
            conn.execute(
                "INSERT INTO customers (customer_id, tenant_id, name, tier) "
                "VALUES ('CUS_ALI', 'T1', 'Restoran Ali', 'A')"
            )
            conn.execute(
                "INSERT INTO orders (tenant_id, draft_id, customer_id, status, ai_mode, "
                "working_lines) "
                "VALUES ('T1', 'DRF_001', 'CUS_ALI', 'DO_GENERATED', 'ALIAS_ONLY', %s::jsonb)",
                (json.dumps([{"line_id": "LIN_001"}]),),
            )
            conn.execute(
                "INSERT INTO draft_versions (tenant_id, draft_id, version, snapshot, created_by) "
                "VALUES ('T1', 'DRF_001', 1, '{}'::jsonb, 'USR_T1_CLERK')"
            )
            conn.execute(
                "INSERT INTO delivery_orders (do_number, tenant_id, draft_id, draft_version, "
                "customer_id, lines, final_total_rm, prepared_by, approved_by, "
                "approval_mode, reply_draft) "
                "VALUES ('DO-20261021-0003', 'T1', 'DRF_001', 1, 'CUS_ALI', %s::jsonb, 360.00, "
                "'USR_T1_CLERK', 'USR_T1_CLERK', 'DIRECT', '{}'::jsonb)",
                (json.dumps(DO["lines"]),),
            )

        orders, products = fetch_orders(url, "T1", "DO-20261021-0003")
        assert len(orders) == 1

        export = build_export(
            "TEST-01",
            "T1",
            orders[0],
            products=products,
            working_lines=orders[0]["working_lines"],
        )
        assert export.order_mismatch is False
        assert export.totals_match is True
        assert export.rows[0]["sku_id"] == "SKU_OIL_5KG"
        assert export.rows[0]["line_no"] == "L1"
        assert export.rows[0]["customer_id"] == "CUS_ALI"
        assert export.ai_mode == "ALIAS_ONLY"

        csv_path, json_path = write_outputs(tmp_path, "TEST-01", [export], total_row=False)
        assert csv_path.is_file() and json_path.is_file()
    finally:
        admin.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
        )


def test_mixed_ai_mode_is_flagged():
    do = {**DO, "ai_mode": "MIXED"}

    export = build_export("TEST-01", "T1", do)

    assert export.ai_mode_mixed is True
    assert export.as_dict()["ai_mode_mixed"] is True


def test_line_order_mismatch_is_flagged():
    export = build_export("TEST-01", "T1", DO, working_lines=[{"line_id": "LIN_OTHER"}])

    assert export.order_mismatch is True
    assert any("working_lines" in error for error in export.errors)


def test_module_entry_point_is_wired():
    import subprocess
    import sys

    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tools.export_trial_record", "--help"],
        cwd=backend,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_products_file_hash_and_sku_binding(tmp_path):
    products = tmp_path / "products.csv"
    products.write_text(
        "sku_id,pack_size,grade\nSKU_OIL_5KG,5kg,\n",
        encoding="utf-8",
    )
    sha = sha256_file(products)
    mapped, meta = verify_products_file(
        products,
        expected_sha256=sha,
        version="T1-0.1",
        database_products={"SKU_OIL_5KG": {"pack_size": "5kg", "grade": None}},
        used_skus={"SKU_OIL_5KG"},
    )
    assert mapped["SKU_OIL_5KG"]["pack_size"] == "5kg"
    assert meta["verification"] == "FILE_HASH_AND_SKU_MATCH"
    assert meta["sha256"] == sha
    assert meta["matched_skus"] == ["SKU_OIL_5KG"]


def test_products_file_rejects_hash_mismatch(tmp_path):
    products = tmp_path / "products.csv"
    products.write_text("sku_id,pack_size,grade\nSKU_OIL_5KG,5kg,\n", encoding="utf-8")
    with pytest.raises(ExportError, match="SHA-256 mismatch"):
        verify_products_file(
            products,
            expected_sha256="0" * 64,
            version=None,
            database_products=None,
            used_skus={"SKU_OIL_5KG"},
        )


def test_products_file_rejects_database_value_mismatch(tmp_path):
    products = tmp_path / "products.csv"
    products.write_text("sku_id,pack_size,grade\nSKU_OIL_5KG,1kg,\n", encoding="utf-8")
    with pytest.raises(ExportError, match="pack_size mismatch"):
        verify_products_file(
            products,
            expected_sha256=None,
            version=None,
            database_products={"SKU_OIL_5KG": {"pack_size": "5kg", "grade": None}},
            used_skus={"SKU_OIL_5KG"},
        )


def test_cli_fixture_with_bound_products_file(tmp_path):
    fixture = tmp_path / "delivery_order.json"
    fixture.write_text(json.dumps({"body": DO}), encoding="utf-8")
    products = tmp_path / "products.csv"
    products.write_text("sku_id,pack_size,grade\nSKU_OIL_5KG,5kg,\n", encoding="utf-8")
    sha = sha256_file(products)

    code = main(
        [
            "--fixture",
            str(fixture),
            "--case-id",
            "TEST-01",
            "--out-dir",
            str(tmp_path / "out"),
            "--products-file",
            str(products),
            "--products-sha256",
            sha,
            "--products-version",
            "T1-0.1",
        ]
    )

    assert code == 0
    payload = json.loads((tmp_path / "out" / "TEST-01_do_lines.json").read_text(encoding="utf-8"))
    assert payload["products"]["verification"] == "FILE_HASH_AND_SKU_MATCH"
    assert payload["products"]["sha256"] == sha
    assert payload["products"]["source_file"].endswith("products.csv")


def test_cli_products_file_hash_mismatch_exits_1(tmp_path):
    fixture = tmp_path / "delivery_order.json"
    fixture.write_text(json.dumps({"body": DO}), encoding="utf-8")
    products = tmp_path / "products.csv"
    products.write_text("sku_id,pack_size,grade\nSKU_OIL_5KG,5kg,\n", encoding="utf-8")

    code = main(
        [
            "--fixture",
            str(fixture),
            "--case-id",
            "TEST-01",
            "--out-dir",
            str(tmp_path / "out"),
            "--products-file",
            str(products),
            "--products-sha256",
            "0" * 64,
        ]
    )

    assert code == 1
    assert not (tmp_path / "out" / "TEST-01_do_lines.json").exists()


def test_products_file_requires_sku_and_pack_columns(tmp_path):
    products = tmp_path / "products.csv"
    products.write_text("sku_id,grade\nSKU_A,A\n", encoding="utf-8")
    with pytest.raises(ExportError, match="pack_size"):
        load_products_file(products)
