"""Resolve one provider configuration for extraction, probes and warmup."""

from dataclasses import dataclass
from typing import Literal

from pydantic import SecretStr

from app.config import Settings


@dataclass(frozen=True)
class AiRuntimeConfig:
    provider: Literal["stub", "http", "runpod_adapter"]
    inference_url: str | None = None
    health_url: str | None = None
    models_url: str | None = None
    wake_url: str | None = None
    api_key: SecretStr | None = None
    endpoint_id: str | None = None
    model_name: str | None = None
    inference_timeout_s: float = 4.1
    probe_timeout_s: float = 2.5
    warmup_timeout_s: float = 180.0


def resolve_ai_runtime(settings: Settings) -> AiRuntimeConfig:
    provider = settings.ai_provider
    if provider == "auto":
        provider = "http" if settings.ai_service_url else "stub"
    if provider == "stub":
        return AiRuntimeConfig(provider="stub")
    common = {
        "probe_timeout_s": min(settings.ai_timeout_s, 2.5),
        "warmup_timeout_s": settings.ai_warmup_timeout_s,
    }
    if provider == "runpod_adapter":
        if (
            settings.runpod_api_key is None
            or not settings.runpod_api_key.get_secret_value().strip()
            or not settings.runpod_endpoint_id
        ):
            raise ValueError(
                "AI_PROVIDER=runpod_adapter requires RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID"
            )
        origin = f"https://{settings.runpod_endpoint_id}.api.runpod.ai"
        return AiRuntimeConfig(
            provider="runpod_adapter",
            inference_url=f"{origin}/v1/chat/completions",
            health_url=f"{origin}/health",
            models_url=f"{origin}/v1/models",
            api_key=settings.runpod_api_key,
            endpoint_id=settings.runpod_endpoint_id,
            model_name=settings.runpod_model_name,
            inference_timeout_s=settings.llm_timeout_s,
            **common,
        )
    if not settings.ai_service_url:
        raise ValueError("AI_PROVIDER=http requires AI_SERVICE_URL")
    return AiRuntimeConfig(
        provider="http",
        inference_url=settings.ai_service_url,
        health_url=settings.ai_health_url,
        wake_url=settings.ai_wake_url,
        api_key=settings.ai_api_key,
        inference_timeout_s=settings.ai_timeout_s,
        **common,
    )
