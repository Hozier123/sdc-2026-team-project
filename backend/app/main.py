"""Application factory; startup never changes the database schema."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.approvals import router as approvals_router
from app.config import Settings
from app.delivery import router as delivery_router
from app.drafts import router as drafts_router
from app.errors import REQUEST_ID_HEADER, register_error_handlers
from app.extraction.ai import HttpAiExtractor
from app.extraction.stub import StubExtractor
from app.health import router as health_router
from app.me import router as me_router
from app.parse import router as parse_router


def _extractor(settings: Settings):
    if settings.ai_service_url:
        return HttpAiExtractor(
            service_url=settings.ai_service_url,
            api_key=(
                settings.ai_api_key.get_secret_value() if settings.ai_api_key is not None else None
            ),
            timeout_s=settings.ai_timeout_s,
        )
    return StubExtractor()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="KiraOrder backend foundation", version="0.1.0")
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
    app.state.extraction_provider = _extractor(app.state.settings)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(parse_router)
    app.include_router(drafts_router)
    app.include_router(approvals_router)
    app.include_router(delivery_router)
    return app


app = create_app()
