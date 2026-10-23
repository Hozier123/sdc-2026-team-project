"""Provider selection tests; no network or database required."""

import pytest

from app.config import Settings
from app.extraction.ai import HttpAiExtractor
from app.extraction.runpod_adapter import RunPodAdapterProvider
from app.extraction.stub import StubExtractor
from app.main import _extractor


def test_default_settings_keep_stub_provider():
    settings = Settings(_env_file=None)
    assert isinstance(_extractor(settings), StubExtractor)


def test_http_provider_remains_default_when_service_url_is_set():
    settings = Settings(_env_file=None, ai_service_url="https://ai.example.test/extract")
    assert isinstance(_extractor(settings), HttpAiExtractor)


def test_runpod_adapter_requires_explicit_flag_and_credentials():
    settings = Settings(
        _env_file=None,
        ai_provider="runpod_adapter",
        runpod_api_key="test-key",
        runpod_endpoint_id="test-endpoint",
        llm_timeout_s=4.1,
    )
    provider = _extractor(settings)
    assert isinstance(provider, RunPodAdapterProvider)
    assert provider.adapter.extractor.api_key == "test-key"
    assert provider.adapter.extractor.endpoint_id == "test-endpoint"
    assert provider.adapter.extractor.timeout_s == 4.1


def test_runpod_adapter_missing_credentials_fails_fast():
    settings = Settings(_env_file=None, ai_provider="runpod_adapter", runpod_endpoint_id="x")
    with pytest.raises(ValueError, match="RUNPOD_API_KEY"):
        _extractor(settings)


def test_explicit_stub_ignores_ai_service_url():
    settings = Settings(
        _env_file=None,
        ai_provider="stub",
        ai_service_url="https://ai.example.test/extract",
    )
    assert isinstance(_extractor(settings), StubExtractor)
