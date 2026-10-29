"""Application factory; startup never changes the database schema."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.adapter import OrderAiAdapter
from app.ai.extractor import RunPodExtractor
from app.ai_runtime import AiRuntimeConfig, resolve_ai_runtime
from app.ai_status import AiOrchestrator
from app.approvals import router as approvals_router
from app.config import Settings
from app.delivery import router as delivery_router
from app.drafts import router as drafts_router
from app.errors import REQUEST_ID_HEADER, register_error_handlers
from app.extraction.ai import HttpAiExtractor
from app.extraction.runpod_adapter import RunPodAdapterProvider
from app.extraction.stub import StubExtractor
from app.health import router as health_router
from app.me import router as me_router
from app.parse import router as parse_router
from app.read_models import router as read_models_router


def _extractor(settings: Settings, *, runtime: AiRuntimeConfig | None = None):
    runtime = runtime or resolve_ai_runtime(settings)
    api_key = runtime.api_key.get_secret_value() if runtime.api_key is not None else None
    if runtime.provider == "runpod_adapter":
        runpod_extractor = RunPodExtractor(
            api_key=api_key,
            endpoint_id=runtime.endpoint_id,
            base_url=runtime.inference_url,
            timeout_s=runtime.inference_timeout_s,
            model_name=runtime.model_name,
        )
        return RunPodAdapterProvider(adapter=OrderAiAdapter(extractor=runpod_extractor))
    if runtime.provider == "http":
        return HttpAiExtractor(
            service_url=runtime.inference_url,
            api_key=api_key,
            timeout_s=runtime.inference_timeout_s,
        )
    return StubExtractor()


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            for owned in (owned_provider, owned_orchestrator):
                close = getattr(owned, "close", None)
                if close:
                    close()

    app = FastAPI(title="KiraOrder backend foundation", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings if settings is not None else Settings()
    origins = [
        origin.strip()
        for origin in app.state.settings.cors_allow_origins.split(",")
        if origin.strip()
    ]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    runtime = resolve_ai_runtime(app.state.settings)
    owned_provider = _extractor(app.state.settings, runtime=runtime)
    app.state.extraction_provider = owned_provider
    owned_orchestrator = AiOrchestrator(app.state.settings, runtime=runtime)
    app.state.ai_orchestrator = owned_orchestrator
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(parse_router)
    app.include_router(drafts_router)
    app.include_router(approvals_router)
    app.include_router(delivery_router)
    app.include_router(read_models_router)
    return app


app = create_app()
