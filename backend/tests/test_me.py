import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token, permission_summary_for, permissions_for
from app.db import connect
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

TOKENS = {
    "clerk": "tok_t1_clerk",
    "owner": "tok_t1_owner",
    "warehouse": "tok_t1_warehouse",
    "inactive": "tok_t1_inactive",
    "t2": "tok_t2_clerk",
}


@pytest.fixture
def seeded_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, amount_threshold_rm) VALUES "
            "('T1', 'Tenant One', 1500), ('T2', 'Tenant Two', 1500)"
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO users "
                "(user_id, tenant_id, display_name, demo_token_hash, role, active) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [
                    ("USR_T1_CLERK", "T1", "T1 Clerk", hash_token(TOKENS["clerk"]), "CLERK", True),
                    ("USR_T1_OWNER", "T1", "T1 Owner", hash_token(TOKENS["owner"]), "OWNER", True),
                    (
                        "USR_T1_WAREHOUSE",
                        "T1",
                        "T1 Warehouse",
                        hash_token(TOKENS["warehouse"]),
                        "WAREHOUSE",
                        True,
                    ),
                    (
                        "USR_T1_INACTIVE",
                        "T1",
                        "T1 Inactive",
                        hash_token(TOKENS["inactive"]),
                        "CLERK",
                        False,
                    ),
                    ("USR_T2_CLERK", "T2", "T2 Clerk", hash_token(TOKENS["t2"]), "CLERK", True),
                ],
            )
    return db_settings


def _client(settings):
    return TestClient(create_app(settings))


def test_me_rejects_missing_and_malformed_token(seeded_db):
    with _client(seeded_db) as client:
        for headers in ({}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer"}):
            response = client.get("/api/v1/me", headers=headers)
            assert response.status_code == 401
            assert response.json() == {
                "error_code": "INVALID_TOKEN",
                "message": "Invalid or missing token.",
                "details": {},
            }
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert response.headers["X-Request-ID"]


def test_me_rejects_unknown_and_inactive_token(seeded_db):
    with _client(seeded_db) as client:
        for token in ("does-not-exist", TOKENS["inactive"]):
            response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 401
            assert response.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.parametrize(
    ("token", "user_id", "role", "tenant"),
    [
        (TOKENS["clerk"], "USR_T1_CLERK", "CLERK", ("T1", "Tenant One")),
        (TOKENS["owner"], "USR_T1_OWNER", "OWNER", ("T1", "Tenant One")),
        (
            TOKENS["warehouse"],
            "USR_T1_WAREHOUSE",
            "WAREHOUSE",
            ("T1", "Tenant One"),
        ),
        (TOKENS["t2"], "USR_T2_CLERK", "CLERK", ("T2", "Tenant Two")),
    ],
)
def test_me_returns_identity_and_server_authoritative_permissions(
    seeded_db, token, user_id, role, tenant
):
    with _client(seeded_db) as client:
        response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "user_id",
        "tenant",
        "display_name",
        "role",
        "permissions",
        "permission_summary",
    }
    assert body["user_id"] == user_id
    assert body["role"] == role
    assert body["tenant"] == {"id": tenant[0], "name": tenant[1]}
    assert body["permissions"] == list(permissions_for(role))
    assert body["permission_summary"] == permission_summary_for(role)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]


def test_me_never_uses_query_tenant_or_leaks_token(seeded_db):
    with _client(seeded_db) as client:
        response = client.get(
            "/api/v1/me?tenant_id=T2",
            headers={"Authorization": f"Bearer {TOKENS['clerk']}"},
        )
    assert response.status_code == 200
    assert response.json()["tenant"]["id"] == "T1"
    assert TOKENS["clerk"] not in response.text
    assert hash_token(TOKENS["clerk"]) not in response.text


def test_me_echoes_valid_request_id(seeded_db):
    with _client(seeded_db) as client:
        response = client.get(
            "/api/v1/me",
            headers={
                "Authorization": f"Bearer {TOKENS['clerk']}",
                "X-Request-ID": "test-request-123",
            },
        )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"
