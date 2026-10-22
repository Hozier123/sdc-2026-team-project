"""Application factory; startup never changes the database schema."""

from fastapi import FastAPI

from app.config import Settings
from app.health import router


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="KiraOrder backend foundation", version="0.1.0")
    app.state.settings = settings if settings is not None else Settings()
    app.include_router(router)
    return app


app = create_app()
