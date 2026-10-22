"""Provider boundary between parse-draft and any extraction implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RawRow:
    span: str
    qty: int | None = None
    uom: str | None = None
    fam: str | None = None
    pack_size: str | None = None
    conds: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class RawExtraction:
    rows: tuple[RawRow, ...] = ()
    ignored_spans: tuple[dict[str, Any], ...] = ()


class ExtractionProvider(Protocol):
    def extract(
        self,
        masked_text: str,
        language_hint: str | None,
        request_id: str,
    ) -> RawExtraction: ...


def validate_raw_extraction(raw: RawExtraction, masked_text: str) -> RawExtraction:
    """Reject provider output that cannot be safely handed to the Adapter."""
    if not isinstance(raw, RawExtraction):
        raise TypeError("extractor must return RawExtraction")
    for row in raw.rows:
        if not isinstance(row, RawRow):
            raise TypeError("rows must contain RawRow")
        if not isinstance(row.span, str) or not row.span or row.span not in masked_text:
            raise ValueError("row span is not in masked_text")
        if isinstance(row.qty, bool) or (
            row.qty is not None and (not isinstance(row.qty, int) or row.qty < 1)
        ):
            raise ValueError("row qty must be a positive integer or null")
    return raw
