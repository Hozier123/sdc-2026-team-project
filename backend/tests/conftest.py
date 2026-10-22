"""Each integration test owns a fresh database, never an existing application database."""

import os
import uuid

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo


@pytest.fixture
def database_url():
    admin_url = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if not admin_url:
        pytest.fail("Integration tests require TEST_DATABASE_ADMIN_URL; see backend/README.md")
    name = "kiraorder_test_" + uuid.uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            # Return a libpq conninfo for test connections; app Settings uses a PostgreSQL URI.
            yield make_conninfo(admin_url, dbname=name)
        finally:
            # The exact generated name is owned by this fixture, never a user-supplied name.
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def db_settings(database_url):
    from urllib.parse import quote

    from psycopg.conninfo import conninfo_to_dict

    from app.config import Settings

    parts = conninfo_to_dict(database_url)
    credentials = quote(parts.get("user", "postgres"), safe="")
    if parts.get("password"):
        credentials += ":" + quote(parts["password"], safe="")
    host = parts.get("host", "127.0.0.1")
    if ":" in host:
        host = "[" + host + "]"
    url = f"postgresql://{credentials}@{host}:{parts.get('port', '5432')}/{parts['dbname']}"
    return Settings(_env_file=None, database_url=url)
