"""Application factory; startup never changes the database schema."""

from fastapi import FastAPI

from app.config import Settings
from app.errors import register_error_handlers
from app.health import router as health_router
from app.me import router as me_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="KiraOrder backend foundation", version="0.1.0")
    app.state.settings = settings if settings is not None else Settings()
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(me_router)
    return app


app = create_app()
