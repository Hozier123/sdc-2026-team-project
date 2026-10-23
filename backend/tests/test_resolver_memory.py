"""B22 catalog resolver and B23 customer-memory integration tests."""

import json

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.config import REPO_ROOT
from app.db import connect
from app.main import create_app
from app.migrations import migrate
from app.seed import load_seed

pytestmark = pytest.mark.integration

SEED_DIR = REPO_ROOT / "data" / "seed"
MANIFEST = json.loads((SEED_DIR / "SEED_MANIFEST.json").read_text(encoding="utf-8"))
TOKEN = "resolver-memory-clerk"


@pytest.fixture
def t1_db(db_settings):
    migrate(db_settings)
    meta = MANIFEST["tenants"]["T1"]
    load_seed(
        db_settings,
        tenant="T1",
        seed_path=SEED_DIR / "T1_seed.sql",
        seed_version=meta["seed_version"],
        expect_sha256=meta["sql_sha256"],
        expect_products=meta["products"],
        expect_inventory=meta["inventory_sum"],
    )
    with connect(db_settings) as conn:
        conn.execute(
            "UPDATE users SET demo_token_hash=%s WHERE user_id='USR_T1_CLERK'",
            (hash_token(TOKEN),),
        )
    return db_settings


def _headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def _provider(row: dict):
    from app.extraction.ai import to_raw_extraction

    class Provider:
        def extract(self, masked_text, language_hint, request_id):
            return to_raw_extraction({"rows": [row], "ignored_spans": []}, masked_text)

    return Provider()


def _parse(settings, provider, customer_id: str, text: str):
    app = create_app(settings)
    app.state.extraction_provider = provider
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": customer_id, "message_text": text},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_resolver_selects_unique_pack_and_prices(t1_db):
    draft = _parse(
        t1_db,
        _provider(
            {
                "span": "Milo 1kg 2 bag",
                "qty": 2,
                "uom": "bag",
                "fam": "FAM_MILO",
                "pack_size": "1kg",
            }
        ),
        "CUS_ALI",
        "Milo 1kg 2 bag",
    )
    assert draft["ai_mode"] == "LLM"
    assert draft["status"] == "READY_FOR_APPROVAL"
    line = draft["lines"][0]
    assert line["sku_id"] == "SKU_MILO_1KG"
    assert line["candidate_skus"] == []
    assert line["match_source"] == "LLM_EXTRACTED"
    assert line["tier_unit_price"] is not None
    assert line["subtotal_rm"] is not None
    assert draft["totals"]["is_complete"] is True


def test_resolver_returns_pack_candidates_instead_of_guessing(t1_db):
    draft = _parse(
        t1_db,
        _provider(
            {
                "span": "Milo 2 bag",
                "qty": 2,
                "uom": "bag",
                "fam": "FAM_MILO",
            }
        ),
        "CUS_ALI",
        "Milo 2 bag",
    )
    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    line = draft["lines"][0]
    assert line["sku_id"] is None
    assert {candidate["sku_id"] for candidate in line["candidate_skus"]} == {
        "SKU_MILO_1KG",
        "SKU_MILO_2KG",
    }
    assert "MULTIPLE_PACK_SIZES" in draft["blocking_issues"]
    assert "NO_CANDIDATE" not in draft["blocking_issues"]


def test_resolver_returns_grade_candidates(t1_db):
    draft = _parse(
        t1_db,
        _provider(
            {
                "span": "Telur 1 papan",
                "qty": 1,
                "uom": "papan",
                "fam": "FAM_TELUR",
            }
        ),
        "CUS_ALI",
        "Telur 1 papan",
    )
    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    line = draft["lines"][0]
    assert line["sku_id"] is None
    assert len(line["candidate_skus"]) == 3
    assert "MULTIPLE_GRADES" in draft["blocking_issues"]


def test_resolver_uses_grade_evidence_to_select_one_sku(t1_db):
    draft = _parse(
        t1_db,
        _provider(
            {
                "span": "Telur A 1 papan",
                "qty": 1,
                "uom": "papan",
                "fam": "FAM_TELUR",
            }
        ),
        "CUS_ALI",
        "Telur A 1 papan",
    )
    assert draft["status"] == "READY_FOR_APPROVAL"
    assert draft["lines"][0]["sku_id"] == "SKU_TELUR_A_PAPAN"
    assert draft["lines"][0]["grade"] == "A"


def test_customer_alias_memory_bypasses_provider(t1_db):
    class MustNotBeCalled:
        def extract(self, masked_text, language_hint, request_id):
            raise AssertionError("customer memory should bypass the provider")

    app = create_app(t1_db)
    app.state.extraction_provider = MustNotBeCalled()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_RASA", "message_text": "老规矩辣椒酱 2 btl"},
        )
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["ai_mode"] == "ALIAS_ONLY"
    assert draft["status"] == "READY_FOR_APPROVAL"
    line = draft["lines"][0]
    assert line["sku_id"] == "SKU_CILI_1KG"
    assert line["match_source"] == "SUGGESTED_DEFAULT"
    assert line["saved_alias"]["alias_id"] == "ALS_CACHE_RASA_001"
    assert line["candidate_skus"] == []
    assert "COPY_CLARIFICATION" not in draft["allowed_actions"]


def test_save_then_second_parse_reuses_customer_alias(t1_db):
    first = _parse(
        t1_db,
        _provider(
            {
                "span": "CILI 2 btl",
                "qty": 2,
                "uom": "btl",
                "fam": "FAM_CILI",
            }
        ),
        "CUS_RASA",
        "CILI 2 btl",
    )
    assert first["status"] == "READY_FOR_APPROVAL"
    line = first["lines"][0]
    with TestClient(create_app(t1_db)) as client:
        saved = client.put(
            f"/api/v1/orders/drafts/{first['draft_id']}/lines",
            headers=_headers(),
            json={
                "expected_version": 1,
                "lines": [
                    {
                        "line_id": line["line_id"],
                        "sku_id": line["sku_id"],
                        "confirmed_qty": 2,
                        "uom": "btl",
                        "match_source": "MANUAL_SELECTED",
                        "save_to_alias_cache": True,
                        "alias_scope": "CUSTOMER",
                    }
                ],
            },
        )
    assert saved.status_code == 200, saved.text
    saved_alias = saved.json()["lines"][0]["saved_alias"]
    assert saved_alias["product_id"] == "SKU_CILI_1KG"

    class MustNotBeCalled:
        def extract(self, masked_text, language_hint, request_id):
            raise AssertionError("saved alias should bypass the provider on the second parse")

    app = create_app(t1_db)
    app.state.extraction_provider = MustNotBeCalled()
    with TestClient(app) as client:
        second = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_RASA", "message_text": "CILI 2 btl"},
        )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["ai_mode"] == "ALIAS_ONLY"
    assert body["lines"][0]["sku_id"] == "SKU_CILI_1KG"
    assert body["lines"][0]["saved_alias"]["alias_id"] == saved_alias["alias_id"]
