"""Application factory; startup never changes the database schema."""

from fastapi import FastAPI

from app.approvals import router as approvals_router
from app.config import Settings
from app.delivery import router as delivery_router
from app.drafts import router as drafts_router
from app.errors import register_error_handlers
from app.extraction.stub import StubExtractor
from app.health import router as health_router
from app.me import router as me_router
from app.parse import router as parse_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="KiraOrder backend foundation", version="0.1.0")
    app.state.settings = settings if settings is not None else Settings()
    app.state.extraction_provider = StubExtractor()
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(parse_router)
    app.include_router(drafts_router)
    app.include_router(approvals_router)
    app.include_router(delivery_router)
    return app


app = create_app()
