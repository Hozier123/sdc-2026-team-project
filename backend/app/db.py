"""Short-lived PostgreSQL connections; credentials never enter diagnostics."""

import psycopg

from app.config import Settings


class DatabaseConfigurationError(Exception):
    """A missing or unsupported database setting (safe to show to operators)."""


def connect(settings: Settings) -> psycopg.Connection:
    url = settings.database_url.get_secret_value() if settings.database_url else ""
    if not url.startswith(("postgresql://", "postgres://")):
        raise DatabaseConfigurationError("DATABASE_URL must be a PostgreSQL URL")
    return psycopg.connect(
        url,
        autocommit=True,
        connect_timeout=3,
        application_name="kiraorder-backend",
        options="-c statement_timeout=5000 -c lock_timeout=5000",
    )
