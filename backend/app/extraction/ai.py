"""Adapter for Xiong's AI-Contract-v1.3 extraction payload.

The provider returns only ``rows`` and ``ignored_spans``. This module turns that
wire format into the backend's ``RawExtraction`` and classifies the verbatim
condition phrases using the frozen H5 lexicon.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.config import REPO_ROOT
from app.extraction.base import RawExtraction, RawRow

AI_CONTRACT_VERSION = "AI-Contract-v1.3"

# AI samples use generic family names. The canonical seed uses tenant-specific
# IDs; this mapping is intentionally explicit rather than fuzzy.
DEFAULT_FAMILY_ALIASES: dict[str, str] = {
    "FAM_FLOUR": "FAM_TEPUNG",
    "FAM_RICE": "FAM_BERAS",
    "FAM_OIL": "FAM_MINYAK",
    "FAM_SUGAR": "FAM_GULA",
    "FAM_SALT": "FAM_GARAM",
    "FAM_EGG": "FAM_TELUR",
}

NEGATIVE_CONTEXTS = (
    "last order was",
    "total last time",
    "stock code",
    "hantar esok",
    "price is",
    "not asking for discount",
    "harga lama rm",
    "价格不便宜也没关系",
)
_AMOUNT = re.compile(r"rm\s*(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
_UNIT_PRICE = re.compile(
    r"rm\s*\d+(?:\.\d{1,2})?\s+(?:untuk|per|for|each)\s+1\s+"
    r"(?:ctn|carton|pack|kg|pc|bag|btl|tin|papan|box|pail)",
    re.IGNORECASE,
)


class AiPayloadError(ValueError):
    """The AI service returned a payload that cannot be safely adapted."""


class AiRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span: str = Field(min_length=1)
    qty: StrictInt | None = Field(default=None, ge=1, le=999999)
    uom: str | None = Field(default=None, min_length=1)
    fam: str = Field(min_length=1)
    pack_size: str | None = Field(default=None, min_length=1)
    conds: list[str] = Field(default_factory=list)


class AiExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[AiRow] = Field(default_factory=list)
    ignored_spans: list[str] = Field(default_factory=list)


def _offset(masked_text: str, value: str, start_at: int = 0) -> tuple[int, int]:
    start = masked_text.find(value, start_at)
    if start < 0:
        raise AiPayloadError(f"AI span is not in masked_text: {value!r}")
    return start, start + len(value)


def _ignored_spans(masked_text: str, values: Iterable[str]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    cursor = 0
    for value in values:
        start, end = _offset(masked_text, value, cursor)
        result.append(
            {
                "span": value,
                "start": start,
                "end": end,
                "reason": "NON_ORDER_TEXT",
            }
        )
        cursor = end
    return tuple(result)


@lru_cache(maxsize=1)
def _condition_lexicon() -> dict[str, Any]:
    path = REPO_ROOT / "gate0" / "contracts" / "lexicons" / "condition-triggers-v3.json"
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_negative(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    return any(pattern in normalized for pattern in NEGATIVE_CONTEXTS)


def classify_condition(text: str, masked_text: str) -> list[dict[str, Any]]:
    """Classify one verbatim condition phrase with the frozen H5 v3 triggers."""
    if not text or text not in masked_text or _is_negative(text):
        return []
    normalized = " ".join(text.casefold().split())
    lexicon = _condition_lexicon()
    kinds: list[str] = []
    trigger_ids: list[str] = []
    requested_amount: str | None = None
    for trigger in lexicon.get("triggers", []):
        pattern = trigger.get("pattern")
        if not pattern:
            continue
        if re.search(pattern, normalized, re.IGNORECASE) is None:
            continue
        kind = trigger.get("kind", "")
        if kind == "PRICE_HELPER":
            continue
        if kind == "TIME_OR_OTHER":
            kinds.append("TIME")
        elif kind in {"PRICE", "STOCK"}:
            kinds.append(kind)
        trigger_ids.append(trigger["id"])
    if "PRICE" in kinds:
        amount = _AMOUNT.search(text)
        if amount:
            requested_amount = amount.group(1)
        price_basis = "UNIT" if _UNIT_PRICE.search(text) else "UNKNOWN"
    else:
        price_basis = None
    # A bare question mark plus amount is a price query, not a standalone kind.
    if "PRICE" not in kinds and _AMOUNT.search(text) and ("?" in text or "？" in text):
        kinds.append("PRICE")
        price_basis = "UNKNOWN"
        requested_amount = _AMOUNT.search(text).group(1)
    start, end = _offset(masked_text, text)
    result: list[dict[str, Any]] = []
    for kind in dict.fromkeys(kinds):
        result.append(
            {
                "kind": kind,
                "span": text,
                "start": start,
                "end": end,
                "price_basis": price_basis if kind == "PRICE" else None,
                "requested_amount": requested_amount if kind == "PRICE" else None,
                "blocking": kind == "PRICE",
                "trigger_ids": tuple(trigger_ids),
                "lexicon_version": lexicon.get("version", "condition-triggers-v3"),
            }
        )
    return result


def to_raw_extraction(
    payload: dict[str, Any] | AiExtraction,
    masked_text: str,
    family_aliases: dict[str, str] | None = None,
) -> RawExtraction:
    """Validate an AI payload and convert it to the backend provider type."""
    try:
        if isinstance(payload, AiExtraction):
            parsed = payload
        else:
            parsed = AiExtraction.model_validate(payload)
    except Exception as exc:  # pydantic's ValidationError is intentionally narrow
        raise AiPayloadError(f"AI response failed schema validation: {exc}") from exc
    aliases = {**DEFAULT_FAMILY_ALIASES, **(family_aliases or {})}
    rows: list[RawRow] = []
    for row in parsed.rows:
        _offset(masked_text, row.span)
        fam = aliases.get(row.fam, row.fam)
        conds: list[dict[str, Any]] = []
        for cond in row.conds:
            conds.extend(classify_condition(cond, masked_text))
        rows.append(
            RawRow(
                span=row.span,
                qty=row.qty,
                uom=row.uom,
                fam=fam,
                pack_size=row.pack_size,
                conds=tuple(conds),
            )
        )
    return RawExtraction(
        rows=tuple(rows),
        ignored_spans=_ignored_spans(masked_text, parsed.ignored_spans),
    )


class AiServiceError(RuntimeError):
    """The configured AI service is unavailable or returned an invalid payload."""


class HttpAiExtractor:
    """HTTP client for Xiong's AI-Contract-v1.3 microservice endpoint."""

    def __init__(
        self,
        *,
        service_url: str,
        api_key: str | None = None,
        timeout_s: float = 8.0,
        client: httpx.Client | None = None,
        family_aliases: dict[str, str] | None = None,
    ) -> None:
        self.service_url = service_url
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.client = client or httpx.Client(timeout=timeout_s)
        self.family_aliases = family_aliases

    def extract(
        self,
        masked_text: str,
        language_hint: str | None,
        request_id: str,
    ) -> RawExtraction:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self.client.post(
                self.service_url,
                headers=headers,
                json={
                    "masked_text": masked_text,
                    "language_hint": language_hint,
                    "request_id": request_id,
                },
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise AiServiceError(f"AI service request failed: {exc}") from exc
        if response.status_code != 200:
            raise AiServiceError(
                f"AI service returned HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AiServiceError("AI service returned non-JSON") from exc
        return to_raw_extraction(payload, masked_text, self.family_aliases)
