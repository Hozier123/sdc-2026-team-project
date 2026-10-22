"""Persistence for the parse-draft skeleton."""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect


def persist_parse_draft(
    settings: Settings,
    *,
    user: CurrentUser,
    customer: dict[str, Any],
    draft: dict[str, Any],
    message_id: str,
    masked_text: str,
    language: str | None,
) -> None:
    """Insert masked input, draft, and immutable v1 snapshot atomically."""
    with connect(settings) as conn:
        conn.execute("BEGIN")
        try:
            conn.execute(
                "INSERT INTO inbound_messages "
                "(tenant_id, message_id, customer_id, source, masked_text, language) "
                "VALUES (%s, %s, %s, 'PASTE', %s, %s)",
                (
                    user.tenant_id,
                    message_id,
                    customer["customer_id"],
                    masked_text,
                    language,
                ),
            )
            conn.execute(
                "INSERT INTO orders "
                "(tenant_id, draft_id, customer_id, message_id, status, version, "
                " ai_mode, working_lines, issues, clarification, escalation_preview) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)",
                (
                    user.tenant_id,
                    draft["draft_id"],
                    customer["customer_id"],
                    message_id,
                    draft["status"],
                    draft["version"],
                    draft["ai_mode"],
                    Jsonb(draft["lines"]),
                    Jsonb(draft["issues"]),
                    Jsonb(draft["escalation_preview"]),
                ),
            )
            conn.execute(
                "INSERT INTO draft_versions "
                "(tenant_id, draft_id, version, snapshot, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    user.tenant_id,
                    draft["draft_id"],
                    draft["version"],
                    Jsonb(draft),
                    user.user_id,
                ),
            )
            conn.execute("COMMIT")
        except BaseException:
            with suppress(psycopg.Error):
                conn.execute("ROLLBACK")
            raise
