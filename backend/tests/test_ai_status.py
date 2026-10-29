"""B01 provider, readiness, concurrency and error tests; no GPU or DB needed."""

import json
import threading
from contextlib import contextmanager

import httpx
import pytest

from app.ai_runtime import resolve_ai_runtime
from app.ai_status import AiOrchestrator
from app.config import Settings
from app.errors import RateLimitedError
from app.main import _extractor, create_app

MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"
KEY = "b01-private-mock-key"
ORIGIN = "https://b01-endpoint.api.runpod.ai"
RESULT = {
    "rows": [{"span": "Milo 1 ctn", "fam": "FAM_MILO", "qty": 1, "uom": "ctn", "conds": []}],
    "ignored_spans": [],
}


def settings(**kwargs):
    return Settings(
        _env_file=None,
        **{
            "ai_provider": "runpod_adapter",
            "runpod_api_key": KEY,
            "runpod_endpoint_id": "b01-endpoint",
            "ai_service_url": "https://unused.invalid/extract",
            "ai_health_url": "https://unused.invalid/health",
            "ai_wake_url": "https://unused.invalid/wake",
            "ai_api_key": "unused-key",
            **kwargs,
        },
    )


class Upstream:
    def __init__(self):
        self.calls = []
        self.failure_path = None
        self.failure = None
        self.model = MODEL
        self.content = RESULT

    def __call__(self, request):
        self.calls.append(request)
        assert str(request.url).startswith(ORIGIN)
        assert request.headers["Authorization"] == f"Bearer {KEY}"
        if request.url.path == self.failure_path:
            if self.failure == "timeout":
                raise httpx.ReadTimeout(KEY, request=request)
            if self.failure == "connect":
                raise httpx.ConnectError(KEY, request=request)
            return httpx.Response(self.failure, text=KEY)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": self.model}]})
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == MODEL
        assert payload["messages"][-1]["content"] == "Milo 1 ctn"
        assert payload["response_format"] == {"type": "json_object"}
        assert "wake" not in payload
        return httpx.Response(
            200,
            json={"model": MODEL, "choices": [{"message": {"content": json.dumps(self.content)}}]},
        )


@contextmanager
def orchestrator(upstream=None, **kwargs):
    upstream = upstream or Upstream()
    with httpx.Client(transport=httpx.MockTransport(upstream)) as client:
        ai = AiOrchestrator(settings(**kwargs), client=client)
        try:
            yield ai, upstream
        finally:
            ai.close()


def finish(ai):
    assert ai._warmup is not None
    ai._warmup.result(timeout=3)


def test_app_shares_resolved_provider_config():
    app = create_app(settings())
    runtime = app.state.ai_orchestrator.runtime
    extractor = app.state.extraction_provider.adapter.extractor
    try:
        assert runtime.provider == "runpod_adapter"
        assert extractor.api_url == runtime.inference_url == ORIGIN + "/v1/chat/completions"
        assert extractor.api_key == runtime.api_key.get_secret_value() == KEY
        assert extractor.model_name == runtime.model_name == MODEL
        assert extractor.timeout_s == runtime.inference_timeout_s == 4.1
        assert runtime.health_url == ORIGIN + "/health"
        assert runtime.models_url == ORIGIN + "/v1/models"
        assert runtime.wake_url is None
        assert KEY not in repr(runtime)
    finally:
        app.state.ai_orchestrator.close()


def test_explicit_stub_ignores_all_upstream_config():
    with orchestrator(ai_provider="stub") as (ai, upstream):
        assert ai.status().state == "OFFLINE"
        assert ai.wake("user").accepted is False
        assert upstream.calls == []


@pytest.mark.parametrize("provider", ["auto", "http"])
def test_http_config_uses_only_http_credentials(provider):
    runtime = resolve_ai_runtime(settings(ai_provider=provider))
    assert runtime.provider == "http"
    assert runtime.api_key.get_secret_value() == "unused-key"
    assert runtime.models_url is None
    assert runtime.inference_url == "https://unused.invalid/extract"
    assert runtime.wake_url == "https://unused.invalid/wake"


def test_explicit_http_missing_service_fails_fast():
    with pytest.raises(ValueError, match="AI_SERVICE_URL"):
        _extractor(settings(ai_provider="http", ai_service_url=None))


def test_blank_runpod_key_fails_fast():
    with pytest.raises(ValueError, match="RUNPOD_API_KEY"):
        _extractor(settings(runpod_api_key="  "))


def test_health_and_exact_model_alone_do_not_claim_ready():
    with orchestrator() as (ai, upstream):
        status = ai.status()
        assert status.state == "DEGRADED"
        assert "LLM" not in status.available_modes
        assert status.fallback_available
        assert all(request.method == "GET" for request in upstream.calls)


def test_wake_uses_valid_synthetic_inference_and_separate_timeout():
    with orchestrator() as (ai, upstream):
        result = ai.wake("user")
        assert result.accepted and result.state == "WARMING"
        finish(ai)
        assert ai.status().state == "READY"
        assert ai.status().available_modes == ["LLM", "FALLBACK", "ALIAS_ONLY"]
        post = [request for request in upstream.calls if request.method == "POST"]
        assert len(post) == 1
        assert 4.1 < post[0].extensions["timeout"]["read"] <= 180
        assert KEY not in result.model_dump_json() + ai.status().model_dump_json()


@pytest.mark.parametrize("path", ["/health", "/v1/models", "/v1/chat/completions"])
@pytest.mark.parametrize("failure", [401, 403, 429, 500, "timeout", "connect"])
def test_upstream_errors_never_claim_ready_or_expose_secrets(path, failure):
    upstream = Upstream()
    upstream.failure_path, upstream.failure = path, failure
    with orchestrator(upstream) as (ai, _):
        assert ai.wake("user").accepted
        finish(ai)
        status = ai.status()
        assert status.state != "READY"
        assert "LLM" not in status.available_modes
        assert status.fallback_available
        assert KEY not in status.model_dump_json()


@pytest.mark.parametrize("content", [{}, {"rows": []}, {"rows": [RESULT["rows"][0], {}]}])
def test_invalid_or_empty_inference_is_not_ready(content):
    upstream = Upstream()
    upstream.content = content
    with orchestrator(upstream) as (ai, _):
        ai.wake("user")
        finish(ai)
        assert ai.status().state == "DEGRADED"
        assert "invalid inference" in ai.status().message


@pytest.mark.parametrize("pack_size, expected", [("", "READY"), ("1kg", "DEGRADED")])
def test_runpod_probe_accepts_absent_pack_but_rejects_invented_pack(pack_size, expected):
    upstream = Upstream()
    upstream.content = {
        "rows": [{**RESULT["rows"][0], "pack_size": pack_size}],
        "ignored_spans": [],
    }
    with orchestrator(upstream) as (ai, _):
        ai.wake("user")
        finish(ai)
        assert ai.status().state == expected


def test_wrong_model_prevents_inference():
    upstream = Upstream()
    upstream.model = "wrong-model"
    with orchestrator(upstream) as (ai, _):
        ai.wake("user")
        finish(ai)
        assert ai.status().state == "DEGRADED"
        assert all(request.method == "GET" for request in upstream.calls)


def test_disconnect_recovery_requires_fresh_inference():
    with orchestrator() as (ai, upstream):
        ai.wake("user")
        finish(ai)
        assert ai.status().state == "READY"
        upstream.failure_path, upstream.failure = "/health", "connect"
        assert ai.status().state == "OFFLINE"
        upstream.failure_path = None
        assert ai.status().state == "DEGRADED"
        ai.observe_inference("LLM")
        assert ai.status().state == "READY"
        ai.observe_inference("FALLBACK")
        assert ai.status().state == "DEGRADED"


def test_old_inference_evidence_expires():
    with orchestrator(ai_readiness_ttl_s=1) as (ai, _):
        ai.observe_inference("LLM")
        assert ai.status().state == "READY"
        ai._last_inference_at -= 2
        assert ai.status().state == "DEGRADED"
        assert "expired" in ai.status().message


def test_wake_is_nonblocking_single_flight_and_rate_limited_per_user():
    entered, release = threading.Event(), threading.Event()
    upstream = Upstream()

    def handler(request):
        if request.method == "POST":
            entered.set()
            assert release.wait(3)
        return upstream(request)

    with orchestrator(handler) as (ai, _):
        try:
            assert ai.wake("clerk").state == "WARMING"
            assert entered.wait(2)
            assert ai.status().state == "WARMING"
            assert ai.wake("owner").accepted
            with pytest.raises(RateLimitedError):
                ai.wake("clerk")
            with pytest.raises(RateLimitedError):
                ai.wake("owner")
            # This newer real failure must not be overwritten by the older job.
            ai.observe_inference("FALLBACK")
        finally:
            release.set()
        finish(ai)
        assert ai.status().state == "DEGRADED"
        assert sum(request.method == "POST" for request in upstream.calls) == 1


@pytest.mark.parametrize("with_wake_url", [False, True])
def test_legacy_http_requires_valid_inference_and_only_explicit_wake(with_wake_url):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer unused-key"
        if request.url.path in {"/health", "/wake"}:
            return httpx.Response(200, json={"status": "ok"})
        assert request.method == "POST"
        assert json.loads(request.content)["masked_text"] == "Milo 1 ctn"
        return httpx.Response(200, json=RESULT)

    with orchestrator(
        handler,
        ai_provider="http",
        ai_wake_url="https://unused.invalid/wake" if with_wake_url else None,
    ) as (ai, _):
        assert ai.status().state == "DEGRADED"
        ai.wake("user")
        finish(ai)
        assert ai.status().state == "READY"
        assert sum(request.url.path == "/wake" for request in calls) == int(with_wake_url)


def test_alias_only_never_proves_inference():
    with orchestrator() as (ai, _):
        ai.observe_inference("ALIAS_ONLY")
        assert ai.status().state == "DEGRADED"


def test_legacy_wake_hook_runs_before_health_probe():
    awake = False

    def handler(request):
        nonlocal awake
        if request.url.path == "/wake":
            awake = True
            return httpx.Response(200)
        if request.url.path == "/health":
            return httpx.Response(200 if awake else 503)
        return httpx.Response(200, json=RESULT)

    with orchestrator(handler, ai_provider="http") as (ai, _):
        assert ai.status().state == "DEGRADED"
        ai.wake("user")
        finish(ai)
        assert awake
        assert ai.status().state == "READY"
