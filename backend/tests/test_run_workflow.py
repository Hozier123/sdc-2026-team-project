"""B04 transport, business assertions, credential handling and mutation checkpoints; no DB/GPU."""

import hashlib
import json
from collections import Counter

import httpx
import pytest

from tools.run_workflow import ROOT, Driver, StopRun, main, write_json
from tools.workflow_mock import mock_client


def test_checkout_preserves_independently_signed_driver_bytes():
    driver_bytes = (ROOT / "backend/tools/run_workflow.py").read_bytes()
    assert hashlib.sha256(driver_bytes).hexdigest() == (
        "16c08c081d107582a48cd193bfbd554a4719df1ff8a8d01c32bcb41c88b9ffd5"
    )


def case(name="direct"):
    return json.loads((ROOT / "docs/ops/b04-cases" / f"{name}.json").read_text("utf-8"))


def instrument(value, rewrite=None):
    original = mock_client(value)
    calls = []

    def handle(request):
        calls.append((request.method, request.url.path, request.content))
        response = original.send(request)
        return rewrite(request, response) if rewrite else response

    return httpx.Client(transport=httpx.MockTransport(handle)), calls


def driver(tmp_path, value=None, **kwargs):
    value = value or case()
    return Driver(
        value,
        "http://127.0.0.1:8000/api/v1",
        tmp_path,
        run_id="test-run",
        mock=True,
        environment="test",
        **kwargs,
    )


def change(response, **updates):
    body = response.json()
    body.update(updates)
    return httpx.Response(response.status_code, json=body, headers=response.headers)


@pytest.mark.parametrize("name", ["direct", "owner-approve", "owner-reject", "stock-blocked"])
def test_four_routes_record_every_request_and_business_result(tmp_path, name):
    value = case(name)
    client, calls = instrument(value)
    run = driver(tmp_path, value, client=client)
    result = run.execute()
    assert result["status"] == "SIMULATED_PASS", result
    records = list(run.path.glob("request-*.json"))
    assert len(records) == len(calls)
    for path in records:
        record = json.loads(path.read_text("utf-8"))
        assert record["case_id"] == value["case_id"]
        assert record["run_id"] == "test-run"
        assert record["request_id"] and record["sent_request_id"]
        assert record["status"] == "PASS"
        assert record["elapsed_ms"] >= 0
    assert len(list(run.path.glob("response-*.txt"))) == len(calls)
    for method, path, content in calls:
        if path.endswith("/approve"):
            assert json.loads(content) == {"expected_version": 2}
        if method == "PUT":
            body = json.loads(content)
            assert body["expected_version"] == 1
            assert all(not line.get("save_to_alias_cache") for line in body["lines"])


@pytest.mark.parametrize("field,value", [("role", "OWNER"), ("tenant", {"id": "T2"})])
def test_wrong_identity_stops_before_mutations(tmp_path, field, value):
    client, calls = instrument(case(), lambda req, res: change(res, **{field: value}))
    result = driver(tmp_path, client=client).execute()
    assert result["status"] == "FAIL"
    assert all(method == "GET" for method, _, _ in calls)


def test_owner_missing_stops_after_saved_and_resumes_without_replaying_writes(
    tmp_path, monkeypatch
):
    value = case("owner-approve")
    for role in ("CLERK", "WAREHOUSE"):
        monkeypatch.setenv(value["token_env"][role], f"b04-mock-{role}")
    monkeypatch.delenv(value["token_env"]["OWNER"], raising=False)
    client, calls = instrument(value)
    run = Driver(
        value,
        "http://127.0.0.1:8000/api/v1",
        tmp_path,
        run_id="test-run",
        environment="test",
        client=client,
    )
    assert run.execute("saved")["status"] == "CHECKPOINT"
    resumed = Driver(
        value, run.base, tmp_path, run_id="test-run", resume=True, environment="test", client=client
    )
    assert resumed.execute()["status"] == "BLOCKED"
    assert not any(path.endswith("/approve") for _, path, _ in calls)
    monkeypatch.setenv(value["token_env"]["OWNER"], "b04-mock-OWNER")
    resumed = Driver(
        value, run.base, tmp_path, run_id="test-run", resume=True, environment="test", client=client
    )
    assert resumed.execute()["status"] == "API_PASS"
    counts = Counter(path for method, path, _ in calls if method != "GET")
    assert counts["/api/v1/orders/parse-draft"] == 1
    assert counts["/api/v1/orders/drafts/MOCK_DRAFT/lines"] == 1
    assert counts["/api/v1/approvals/MOCK_APPROVAL/decide"] == 1


def test_missing_warehouse_checked_before_do_creation(tmp_path, monkeypatch):
    value = case()
    monkeypatch.setenv(value["token_env"]["CLERK"], "b04-mock-CLERK")
    monkeypatch.delenv(value["token_env"]["WAREHOUSE"], raising=False)
    client, calls = instrument(value)
    run = Driver(value, "http://127.0.0.1:8000/api/v1", tmp_path, client=client, environment="test")
    assert run.execute()["status"] == "BLOCKED"
    assert not any(path.endswith("/approve") for _, path, _ in calls)


@pytest.mark.parametrize("name", ["direct", "owner-approve", "owner-reject"])
def test_resume_after_decision_does_not_repeat_decision(tmp_path, name):
    value = case(name)
    client, calls = instrument(value)
    run = driver(tmp_path, value, client=client)
    assert run.execute("decision")["status"] == "CHECKPOINT"
    before = [call for call in calls if call[0] != "GET"]
    resumed = driver(tmp_path, value, client=client, resume=True)
    assert resumed.execute()["status"] == "SIMULATED_PASS"
    assert [call for call in calls if call[0] != "GET"] == before


@pytest.mark.parametrize("failure", ["timeout", "server_error", "invalid_json"])
def test_uncertain_write_is_never_replayed(tmp_path, failure):
    def rewrite(request, response):
        if request.url.path.endswith("/approve"):
            if failure == "timeout":
                raise httpx.ReadTimeout("must not persist exception text with secrets")
            return httpx.Response(
                503 if failure == "server_error" else 200, text="upstream failure"
            )
        return response

    client, calls = instrument(case(), rewrite)
    run = driver(tmp_path, client=client)
    assert run.execute()["status"] == "INDETERMINATE"
    before = len(calls)
    with pytest.raises(StopRun, match="sealed"):
        driver(tmp_path, client=client, resume=True)
    assert len(calls) == before
    record = json.loads(next(run.path.glob("request-*-approve.json")).read_text("utf-8"))
    assert record["status"] == "INDETERMINATE"


def test_crashed_in_flight_mutation_is_sealed(tmp_path):
    client, calls = instrument(case())
    run = driver(tmp_path, client=client)
    run.state["pending_request"] = {"method": "POST", "step": "parse"}
    run.checkpoint()
    resumed = driver(tmp_path, client=client, resume=True)
    assert resumed.execute()["status"] == "INDETERMINATE"
    assert calls == []


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_identity_http_errors_preserve_body_and_block(tmp_path, status):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                status, json={"error_code": "TEST_ERROR"}, headers={"X-Request-ID": "server-id"}
            )
        )
    )
    run = driver(tmp_path, client=client)
    assert run.execute()["status"] == "BLOCKED"
    record = json.loads(next(run.path.glob("request-*.json")).read_text("utf-8"))
    assert record["request_id"] == "server-id" and record["http_status"] == status
    assert record["response_body"]["error_code"] == "TEST_ERROR"


@pytest.mark.parametrize("target", ["save_qty", "do_price", "warehouse_price", "audit_missing"])
def test_http_200_is_not_business_success(tmp_path, target):
    def rewrite(request, response):
        body = response.json()
        if target == "save_qty" and request.method == "PUT":
            body["lines"][0]["effective_qty"] = 999
        elif target == "do_price" and request.url.path == "/api/v1/delivery-orders/MOCK_DO":
            body["lines"][0]["applied_unit_price"] = "0.01"
        elif target == "warehouse_price" and "/warehouse/" in request.url.path:
            body["items"][0]["unit_price"] = "3.00"
        elif target == "audit_missing" and request.url.path.endswith("/audit-detail"):
            body["events"] = []
        return httpx.Response(response.status_code, json=body, headers=response.headers)

    client, _ = instrument(case(), rewrite)
    result = driver(tmp_path, client=client).execute()
    assert result["status"] == "FAIL", result


def test_llm_plan_rejects_fallback(tmp_path):
    value = case()
    client, calls = instrument(value)
    value["allowed_ai_modes"] = ["LLM"]
    result = driver(tmp_path, value, client=client).execute()
    assert result["status"] == "FAIL"
    assert result["actual_ai_mode"] == "FALLBACK"
    assert not any(method == "PUT" for method, _, _ in calls)


def test_tokens_and_bearer_echo_are_redacted_from_all_outputs(tmp_path):
    def rewrite(request, response):
        return change(response, debug=f"b04-mock-CLERK {request.headers['Authorization']}")

    client, _ = instrument(case(), rewrite)
    run = driver(tmp_path, client=client)
    assert run.execute()["status"] == "FAIL"  # extra warehouse fields correctly rejected
    for path in run.path.iterdir():
        text = path.read_text("utf-8")
        assert "b04-mock-CLERK" not in text
        assert "b04-mock-WAREHOUSE" not in text


def test_case_change_or_url_change_cannot_resume(tmp_path):
    value = case()
    run = driver(tmp_path, value, client=mock_client(value))
    assert run.execute("saved")["status"] == "CHECKPOINT"
    value["parse"]["message_text"] = "different input"
    with pytest.raises(StopRun, match="binding changed"):
        driver(tmp_path, value, resume=True)


def test_plan_needs_no_sessions_and_creates_no_evidence(tmp_path, capsys):
    result = main(
        ["--case", str(ROOT / "docs/ops/b04-cases/direct.json"), "--plan", "--out", str(tmp_path)]
    )
    assert result == 0 and "PLAN_ONLY" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_raw_non_json_error_is_saved(tmp_path):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(502, text="<html>gateway failure</html>")
        )
    )
    run = driver(tmp_path, client=client)
    assert run.execute()["status"] == "FAIL"
    assert (
        next(run.path.glob("response-*.txt")).read_text("utf-8") == "<html>gateway failure</html>"
    )


def test_stale_checkpoint_binding_protects_driver_revision(tmp_path):
    run = driver(tmp_path, client=mock_client(case()))
    run.state["binding"]["driver_sha256"] = "old-driver"
    write_json(run.path / "checkpoint.json", run.state)
    with pytest.raises(StopRun, match="binding changed"):
        driver(tmp_path, resume=True)


def test_frozen_direct_do_fixture_is_accepted_without_mutating_baseline(tmp_path):
    """The immutable Gate 0 DO is an independent, fixed contract response."""
    fixture = json.loads((ROOT / "gate0/contracts/fixtures/approve_200.json").read_text("utf-8"))
    delivery = fixture["body"]
    value = case()
    value["parse"]["customer_id"] = "CUS_002"
    value["expected"]["lines"] = [
        {"sku_id": "SKU_OIL_1L", "quantity": 3, "unit": "ctn", "applied_unit_price": "120.00"}
    ]
    run = driver(tmp_path, value, client=mock_client(value))
    run.state["identities"]["CLERK"] = "USR_CLERK_01"
    run.verify_do(delivery, {"draft_id": "DRF_003", "version": 2})
    delivery["draft_version"] = 1
    with pytest.raises(StopRun, match="wrong draft/version"):
        run.verify_do(delivery, {"draft_id": "DRF_003", "version": 2})


def test_raw_utf8_body_hash_matches_evidence_bytes(tmp_path):
    raw = '{\n  "error_code": "TEST", "message": "合成失败"\n}\n'.encode()
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                401,
                content=raw,
                headers={"X-Request-ID": "raw-body", "Content-Type": "application/json"},
            )
        )
    )
    run = driver(tmp_path, client=client)
    assert run.execute()["status"] == "BLOCKED"
    assert next(run.path.glob("response-*.txt")).read_bytes() == raw


def test_resume_preserves_original_role_user_identity(tmp_path):
    value = case()
    run = driver(tmp_path, client=mock_client(value))
    assert run.execute("saved")["status"] == "CHECKPOINT"

    def different_user(request, response):
        return (
            change(response, user_id="DIFFERENT_USER")
            if request.url.path.endswith("/me")
            else response
        )

    client, calls = instrument(value, different_user)
    resumed = driver(tmp_path, resume=True, client=client)
    assert resumed.execute()["status"] == "FAIL"
    assert all(method == "GET" for method, _, _ in calls)


def test_failed_http_approval_does_not_accept_unexpected_202(tmp_path):
    def wrong_branch(request, response):
        if request.url.path.endswith("/approve"):
            return httpx.Response(202, json={"approval_id": "UNEXPECTED"}, headers=response.headers)
        return response

    client, _ = instrument(case(), wrong_branch)
    assert driver(tmp_path, client=client).execute()["status"] == "FAIL"


def test_incomplete_parse_does_not_invent_sku(tmp_path):
    def missing_sku(request, response):
        if request.url.path.endswith("/parse-draft"):
            body = response.json()
            body["lines"][0]["sku_id"] = None
            return httpx.Response(200, json=body, headers=response.headers)
        return response

    client, calls = instrument(case(), missing_sku)
    result = driver(tmp_path, client=client).execute()
    assert result["status"] == "BLOCKED"
    assert not any(method == "PUT" for method, _, _ in calls)
