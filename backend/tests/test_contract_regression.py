"""B33 contract regression: signed fixtures and actual error envelopes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient
from test_drafts_approve_do import CLERK, OWNER, WAREHOUSE, _headers, _line, _put
from test_drafts_approve_do import seeded_db as seeded_db

from app.config import REPO_ROOT
from app.db import connect
from app.main import create_app

CONTRACT = yaml.safe_load((REPO_ROOT / "gate0/contracts/openapi.yaml").read_text("utf-8"))
FIXTURES = REPO_ROOT / "gate0/contracts/fixtures"
COMPONENTS = CONTRACT["components"]


def _resolve(node):
    while isinstance(node, dict) and "$ref" in node:
        parts = node["$ref"].lstrip("#/").split("/")
        node = CONTRACT
        for part in parts:
            node = node[part]
    return node


def _fixture_schema(path: str, method: str, status: int):
    route = path.split("?", 1)[0].removeprefix("/api/v1")
    for template, operations in CONTRACT["paths"].items():
        pattern = (
            "^"
            + "/".join(
                "[^/]+" if part.startswith("{") else re.escape(part) for part in template.split("/")
            )
            + "$"
        )
        if not re.match(pattern, route):
            continue
        response = _resolve(operations[method.casefold()]["responses"][str(status)])
        schema = _resolve(response["content"]["application/json"]["schema"])
        if "$ref" in schema:
            return {"$ref": schema["$ref"], "components": COMPONENTS}
        schema = dict(schema)
        schema["components"] = COMPONENTS
        return schema
    raise KeyError(f"no OpenAPI operation for {method} {path}")


def _validate_body(body, schema):
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        body
    )


def _assert_error(response, status: int, code: str | None = None):
    assert response.status_code == status, response.text
    assert response.headers.get("X-Request-ID")
    body = response.json()
    _validate_body(body, {"$ref": "#/components/schemas/Error", "components": COMPONENTS})
    if code is not None:
        assert body["error_code"] == code, body


@pytest.mark.parametrize(
    "fixture",
    sorted(path for path in FIXTURES.glob("*.json") if path.name not in {"error_catalog.json"}),
    ids=lambda path: path.stem,
)
def test_signed_fixture_body_matches_openapi(fixture: Path):
    payload = json.loads(fixture.read_text("utf-8"))
    schema = _fixture_schema(payload["path"], payload["method"], payload["status"])
    _validate_body(payload["body"], schema)


def test_error_catalog_bodies_match_error_schema():
    catalog = json.loads((FIXTURES / "error_catalog.json").read_text("utf-8"))
    for _name, item in catalog.items():
        _validate_body(
            item["body"],
            {"$ref": "#/components/schemas/Error", "components": COMPONENTS},
        )


@pytest.mark.integration
def test_actual_error_envelopes(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        _assert_error(
            client.get("/api/v1/me"),
            401,
            "INVALID_TOKEN",
        )
        _assert_error(
            client.post(
                "/api/v1/orders/parse-draft",
                headers=_headers(WAREHOUSE),
                json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
            ),
            403,
            "FORBIDDEN_ACTION",
        )
        _assert_error(
            client.get("/api/v1/orders/drafts/DRF_MISSING", headers=_headers(CLERK)),
            404,
            "RESOURCE_NOT_FOUND",
        )
        _assert_error(_put(client, version=99), 409, "STALE_VERSION")
        _assert_error(
            client.put(
                "/api/v1/orders/drafts/DRF_T1/lines",
                headers=_headers(CLERK),
                json={"expected_version": 1, "lines": []},
            ),
            400,
            "EMPTY_ORDER",
        )
        _assert_error(
            client.post(
                "/api/v1/orders/parse-draft",
                headers=_headers(CLERK),
                json={"customer_id": "CUS_T1", "message_text": "x" * 4001},
            ),
            422,
            "MESSAGE_TOO_LONG",
        )


@pytest.mark.integration
def test_pending_rejection_and_stock_changed_errors(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        pending = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert pending.status_code == 202, pending.text
        approval_id = pending.json()["approval_id"]

        _assert_error(
            _put(client),
            409,
            "PENDING_OWNER_APPROVAL",
        )
        _assert_error(
            client.post(
                f"/api/v1/approvals/{approval_id}/decide",
                headers=_headers(OWNER),
                json={"decision": "REJECT"},
            ),
            422,
            "REJECTION_REASON_REQUIRED",
        )
        with connect(seeded_db) as conn:
            conn.execute("UPDATE inventory SET available_qty=0 WHERE product_id='SKU_MILO_1KG'")
        _assert_error(
            client.post(
                f"/api/v1/approvals/{approval_id}/decide",
                headers=_headers(OWNER),
                json={"decision": "APPROVE"},
            ),
            409,
            "STOCK_CHANGED",
        )


@pytest.mark.integration
def test_already_approved_error(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client).status_code == 200
        approved = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        _assert_error(
            client.post(
                "/api/v1/orders/DRF_T1/approve",
                headers=_headers(CLERK),
                json={"expected_version": 2},
            ),
            409,
            "ALREADY_APPROVED",
        )


@pytest.mark.integration
def test_insufficient_stock_approval_error(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client, lines=[_line(11)]).status_code == 200
        _assert_error(
            client.post(
                "/api/v1/orders/DRF_T1/approve",
                headers=_headers(CLERK),
                json={"expected_version": 2},
            ),
            400,
            "DISAMBIGUATION_UNRESOLVED",
        )


@pytest.mark.integration
def test_missing_tier_price_error(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute("DELETE FROM customer_tier_prices WHERE product_id='SKU_MILO_1KG'")
    with TestClient(create_app(seeded_db)) as client:
        _assert_error(_put(client), 422, "MISSING_TIER_PRICE")
