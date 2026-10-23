"""Integration tests for the tenant family catalog derived from DB rows."""

import pytest
from test_drafts_approve_do import seeded_db as seeded_db  # noqa: F401

from app.ai.catalog import load_family_catalog
from app.db import connect

pytestmark = pytest.mark.integration


def test_family_catalog_is_built_per_tenant_from_db(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute(
            "INSERT INTO family_aliases "
            "(alias_id, tenant_id, family_id, phrase, phrase_norm) "
            "VALUES ('ALS_TEST_T1', 'T1', 'FAM_MILO', 'Milo', 'milo')"
        )
        conn.execute(
            "INSERT INTO product_families (family_id, tenant_id, family_name) "
            "VALUES ('FAM_T2_MILO', 'T2', 'T2 Milo')"
        )
        conn.execute(
            "INSERT INTO family_aliases "
            "(alias_id, tenant_id, family_id, phrase, phrase_norm) "
            "VALUES ('ALS_TEST_T2', 'T2', 'FAM_T2_MILO', 'Milo T2', 'milo t2')"
        )
        t1 = load_family_catalog(conn, "T1")
        t2 = load_family_catalog(conn, "T2")

    assert set(t1) == {"FAM_MILO"}
    assert t1["FAM_MILO"][0] == "Milo"
    assert "milo" in t1["FAM_MILO"]
    assert set(t2) == {"FAM_T2_MILO"}
    assert t2["FAM_T2_MILO"][0] == "T2 Milo"
    assert "milo t2" in t2["FAM_T2_MILO"]


def test_family_catalog_excludes_inactive_families(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute(
            "UPDATE product_families SET active=false WHERE tenant_id='T1' AND family_id='FAM_MILO'"
        )
        catalog = load_family_catalog(conn, "T1")

    assert catalog == {}


def test_family_catalog_does_not_use_another_tenant(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute(
            "INSERT INTO product_families (family_id, tenant_id, family_name) "
            "VALUES ('FAM_T2_ONLY', 'T2', 'T2 Only')"
        )
        t1 = load_family_catalog(conn, "T1")
        t2 = load_family_catalog(conn, "T2")

    assert "FAM_T2_ONLY" not in t1
    assert "FAM_T2_ONLY" in t2
