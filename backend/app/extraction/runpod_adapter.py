"""In-process RunPod adapter provider.

The AI handoff module is a Pre-Resolver adapter, not an HTTP extraction
endpoint. This provider converts ``OrderAiAdapter.adapt`` output into the
backend's ``RawExtraction`` boundary without inventing SKU, price, stock or
approval fields.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any, Sequence

from app.ai.adapter import AdapterOutput, OrderAiAdapter
from app.extraction.base import RawExtraction, RawRow


def _condition_dict(condition) -> dict[str, Any]:
    return {
        "kind": condition.kind,
        "span": condition.span,
        "start": condition.span_start,
        "end": condition.span_end,
        "condition_scope": condition.condition_scope,
        "price_basis": condition.price_basis,
        "requested_amount": condition.requested_amount,
    }


def _ignored_span_dict(masked_text: str, value: str, cursor: int) -> tuple[dict[str, Any], int]:
    start = masked_text.find(value, cursor)
    if start < 0:
        # Keep the adapter's evidence visible, but never invent a position.
        return {
            "text": value,
            "start": -1,
            "end": -1,
            "normalizer_version": "field-evidence-v2",
        }, cursor
    end = start + len(value)
    return {
        "text": value,
        "start": start,
        "end": end,
        "normalizer_version": "field-evidence-v2",
    }, end


def adapter_output_to_raw(output: AdapterOutput, masked_text: str) -> RawExtraction:
    """Pure conversion used by the provider and by mock tests."""
    conditions = tuple(_condition_dict(condition) for condition in output.conditions)
    ignored: list[dict[str, Any]] = []
    cursor = 0
    for value in output.ignored_spans:
        item, cursor = _ignored_span_dict(masked_text, value, cursor)
        ignored.append(item)

    rows: list[RawRow] = []
    for line in output.lines:
        line_conditions = tuple(
            condition for condition in conditions if condition["span"] in line.span
        )
        evidence = tuple(asdict(item) for item in line.field_evidence)
        rows.append(
            RawRow(
                span=line.span,
                qty=line.qty,
                uom=line.uom,
                fam=line.family_id,
                pack_size=line.pack_size,
                conds=line_conditions,
                source=line.match_source,
                field_evidence=evidence,
            )
        )
    return RawExtraction(
        rows=tuple(rows),
        ignored_spans=tuple(ignored),
        ai_mode=output.ai_mode,
        conditions=conditions,
    )


class RunPodAdapterProvider:
    """Synchronous backend boundary around the async AI adapter."""

    def __init__(self, adapter: OrderAiAdapter | None = None) -> None:
        self.adapter = adapter or OrderAiAdapter()

    async def extract_async(
        self,
        masked_text: str,
        catalog: dict[str, Sequence[str]] | None,
        *,
        language_hint: str | None = None,
        request_id: str | None = None,
    ) -> RawExtraction:
        if catalog is None:
            raise ValueError("tenant catalog must be explicitly provided")
        output = await self.adapter.adapt(masked_text, catalog)
        return adapter_output_to_raw(output, masked_text)

    def extract(
        self,
        masked_text: str,
        language_hint: str | None,
        request_id: str,
        catalog: dict[str, Sequence[str]] | None = None,
    ) -> RawExtraction:
        """Adapter-compatible sync entry point.

        ``catalog`` is mandatory at runtime; it is passed separately because
        the existing provider protocol does not carry tenant context.
        """
        if catalog is None:
            raise ValueError("tenant catalog must be explicitly provided")
        return asyncio.run(
            self.extract_async(
                masked_text,
                catalog,
                language_hint=language_hint,
                request_id=request_id,
            )
        )
