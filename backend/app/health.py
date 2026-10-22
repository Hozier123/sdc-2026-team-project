"""Operational probes; these are outside the frozen business API contract."""

from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.config import Settings
from app.db import DatabaseConfigurationError, connect
from app.migrations import HASH_LIST_SHA256, SQL_SHA256, VERSION

router = APIRouter(tags=["operations"])


class HealthStatus(BaseModel):
    status: Literal["ok", "ready", "not_ready"]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def database_ready(settings: Settings) -> bool:
    try:
        with connect(settings) as conn:
            conn.execute("SELECT 1")
            row = conn.execute(
                "SELECT sql_sha256, baseline_hash_sha256 "
                "FROM kiraorder_meta.schema_migrations WHERE version=%s",
                (VERSION,),
            ).fetchone()
            return row == (SQL_SHA256, HASH_LIST_SHA256)
    except (DatabaseConfigurationError, psycopg.Error):
        return False


@router.get("/healthz", response_model=HealthStatus)
def healthz() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/readyz", response_model=HealthStatus, responses={503: {"model": HealthStatus}})
def readyz(
    response: Response, settings: Annotated[Settings, Depends(get_settings)]
) -> HealthStatus:
    if database_ready(settings):
        return HealthStatus(status="ready")
    response.status_code = 503
    return HealthStatus(status="not_ready")
