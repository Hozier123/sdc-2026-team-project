"""Provider boundary between parse-draft and any extraction implementation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Protocol


@dataclass(frozen=True)
class RawRow:
    span: str
    qty: int | None = None
    uom: str | None = None
    fam: str | None = None
    pack_size: str | None = None
    conds: tuple[dict[str, Any], ...] = ()
    source: str = "LLM_EXTRACTED"
    invalid_reason: str | None = None
    memory: bool = False
    alias: dict[str, Any] | None = None


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


def validate_raw_extraction(
    raw: RawExtraction, masked_text: str, *, strict: bool = True
) -> RawExtraction:
    """Validate provider output; non-strict mode isolates bad rows."""
    if not isinstance(raw, RawExtraction):
        raise TypeError("extractor must return RawExtraction")
    validated: list[RawRow] = []
    changed = False
    for row in raw.rows:
        if not isinstance(row, RawRow):
            if strict:
                raise TypeError("rows must contain RawRow")
            changed = True
            continue
        if not isinstance(row.span, str) or not row.span or row.span not in masked_text:
            if strict:
                raise ValueError("row span is not in masked_text")
            changed = True
            validated.append(
                replace(
                    row,
                    span=row.span if isinstance(row.span, str) else "",
                    invalid_reason="SOURCE_EVIDENCE_INVALID",
                )
            )
            continue
        if isinstance(row.qty, bool) or (
            row.qty is not None and (not isinstance(row.qty, int) or row.qty < 1)
        ):
            if strict:
                raise ValueError("row qty must be a positive integer or null")
            changed = True
            validated.append(replace(row, invalid_reason="INVALID_QUANTITY"))
            continue
        validated.append(row)
    return replace(raw, rows=tuple(validated)) if changed else raw
