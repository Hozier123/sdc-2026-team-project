import pytest

from app.auth import (
    InvalidTokenError,
    hash_token,
    parse_authorization,
    permission_summary_for,
    permissions_for,
)


def test_hash_token_is_stable_lowercase_sha256():
    assert hash_token("demo-token") == hash_token("demo-token")
    assert len(hash_token("demo-token")) == 64
    assert hash_token("demo-token") == hash_token("demo-token").lower()


@pytest.mark.parametrize(
    "header",
    [None, "", "Bearer", "Basic token", "Bearer ", "Bearer one two"],
)
def test_parse_authorization_rejects_missing_or_malformed(header):
    with pytest.raises(InvalidTokenError):
        parse_authorization(header)


def test_parse_authorization_accepts_bearer_case_insensitively():
    assert parse_authorization("Bearer demo-token") == "demo-token"
    assert parse_authorization("bearer demo-token") == "demo-token"


def test_permissions_are_role_scoped_and_owner_includes_clerk():
    clerk = set(permissions_for("CLERK"))
    owner = set(permissions_for("OWNER"))
    assert clerk
    assert clerk <= owner
    assert {"OWNER_APPROVE", "OWNER_REJECT", "CANCEL_DRAFT"} <= owner
    assert permissions_for("WAREHOUSE") == ()


def test_permission_summaries_are_non_empty_and_distinct():
    summaries = {role: permission_summary_for(role) for role in ("CLERK", "OWNER", "WAREHOUSE")}
    assert all(summaries.values())
    assert len(set(summaries.values())) == 3
