import shutil
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import migrations
from app.config import Settings
from app.db import connect
from app.main import create_app


@pytest.mark.parametrize("filename", ["migrations/0001_baseline.sql", "docs/gate0-hashes.txt"])
def test_changed_baseline_rejected_before_connect(tmp_path, monkeypatch, filename):
    for relative in ("migrations/0001_baseline.sql", "docs/gate0-hashes.txt"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(migrations.GATE0_ROOT / relative, target)
    with (tmp_path / filename).open("ab") as changed:
        changed.write(b"\n-- changed")

    def forbidden_connect(*args):
        pytest.fail("Hash validation must precede the connection")

    monkeypatch.setattr(migrations, "connect", forbidden_connect)
    with pytest.raises(migrations.MigrationError, match="checksum mismatch"):
        migrations.migrate(Settings(_env_file=None), tmp_path)


def test_missing_baseline_has_safe_error(tmp_path):
    with pytest.raises(migrations.MigrationError, match="missing or unreadable"):
        migrations.verified_statements(tmp_path)


@pytest.mark.integration
def test_apply_repeat_and_readiness(db_settings):
    with TestClient(create_app(db_settings)) as client:
        assert client.get("/readyz").status_code == 503
        assert migrations.migrate(db_settings).status == "applied"
        assert client.get("/readyz").status_code == 200
        with connect(db_settings) as conn:
            conn.execute(
                "INSERT INTO public.tenants (tenant_id,name,amount_threshold_rm) "
                "VALUES ('test-preserved','Synthetic',100)"
            )
        assert migrations.migrate(db_settings).status == "already_applied"
        with connect(db_settings) as conn:
            migrations.verify_schema(conn)
            assert conn.execute(
                "SELECT count(*) FROM kiraorder_meta.schema_migrations"
            ).fetchone() == (1,)
            assert conn.execute("SELECT count(*) FROM public.tenants").fetchone() == (1,)


@pytest.mark.integration
def test_concurrent_migrations_execute_once(db_settings):
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=10)
        return migrations.migrate(db_settings).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == ["already_applied", "applied"]


@pytest.mark.integration
def test_failure_rolls_back_schema_and_ledger_then_retry_works(db_settings, monkeypatch):
    real_verify = migrations.verify_schema

    def fail_late(conn):
        real_verify(conn)
        # Real server error after the DDL and ledger INSERT, before COMMIT.
        conn.execute("SELECT 1/0")

    monkeypatch.setattr(migrations, "verify_schema", fail_late)
    with pytest.raises(psycopg.errors.DivisionByZero):
        migrations.migrate(db_settings)
    with connect(db_settings) as conn:
        assert conn.execute("SELECT to_regclass('public.tenants')").fetchone() == (None,)
        assert conn.execute("SELECT to_regnamespace('kiraorder_meta')").fetchone() == (None,)
    monkeypatch.setattr(migrations, "verify_schema", real_verify)
    assert migrations.migrate(db_settings).status == "applied"


@pytest.mark.integration
def test_ledger_checksum_mismatch_rejected(db_settings):
    migrations.migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute("UPDATE kiraorder_meta.schema_migrations SET sql_sha256='wrong'")
    with pytest.raises(migrations.MigrationError, match="ledger"):
        migrations.migrate(db_settings)
    with TestClient(create_app(db_settings)) as client:
        assert client.get("/readyz").status_code == 503


@pytest.mark.integration
def test_existing_untracked_tables_never_adopted(db_settings):
    with connect(db_settings) as conn:
        conn.execute("CREATE TABLE public.keep_me (id integer)")
        conn.execute("INSERT INTO public.keep_me VALUES (42)")
    with pytest.raises(migrations.MigrationError, match="Untracked public"):
        migrations.migrate(db_settings)
    with connect(db_settings) as conn:
        assert conn.execute("SELECT * FROM public.keep_me").fetchall() == [(42,)]
        assert conn.execute("SELECT to_regnamespace('kiraorder_meta')").fetchone() == (None,)


@pytest.mark.integration
def test_disabled_trigger_detected_on_repeat(db_settings):
    migrations.migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "ALTER TABLE public.approval_requests DISABLE TRIGGER approval_request_snapshot_guard"
        )
    with pytest.raises(migrations.MigrationError, match="enabled"):
        migrations.migrate(db_settings)


@pytest.mark.integration
def test_snapshot_guards_enforce_update_and_delete(db_settings):
    migrations.migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO public.tenants (tenant_id,name,amount_threshold_rm) "
            "VALUES ('t','Synthetic',100)"
        )
        conn.execute(
            "INSERT INTO public.users (user_id,tenant_id,display_name,demo_token_hash,role) "
            "VALUES ('u','t','Test owner','synthetic-hash','OWNER')"
        )
        conn.execute(
            "INSERT INTO public.customers (customer_id,tenant_id,name,tier) "
            "VALUES ('c','t','Synthetic customer','A')"
        )
        conn.execute(
            "INSERT INTO public.orders (tenant_id,draft_id,customer_id,status,ai_mode) "
            "VALUES ('t','d','c','PENDING_OWNER_APPROVAL','FALLBACK')"
        )
        conn.execute(
            "INSERT INTO public.draft_versions (tenant_id,draft_id,version,snapshot,created_by) "
            "VALUES ('t','d',1,'{}','u')"
        )
        conn.execute(
            "INSERT INTO public.approval_requests "
            "(approval_id,tenant_id,draft_id,draft_version,status,reasons,snapshot,requested_by) "
            "VALUES ('a','t','d',1,'PENDING','[]','{}','u')"
        )
        for statement in (
            "DELETE FROM public.approval_requests WHERE approval_id='a'",
            "UPDATE public.approval_requests SET snapshot='{\"changed\":true}' "
            "WHERE approval_id='a'",
            "UPDATE public.draft_versions SET snapshot='{\"changed\":true}'",
            "DELETE FROM public.draft_versions",
        ):
            with pytest.raises(psycopg.Error) as error:
                conn.execute(statement)
            assert error.value.sqlstate == "55000"
        conn.execute(
            "UPDATE public.approval_requests SET status='APPROVED', "
            "decided_by='u', decided_at=now() WHERE approval_id='a'"
        )
        with pytest.raises(psycopg.Error) as error:
            conn.execute(
                "UPDATE public.approval_requests SET decision_note='changed' WHERE approval_id='a'"
            )
        assert error.value.sqlstate == "55000"
