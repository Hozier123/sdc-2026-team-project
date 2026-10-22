"""Deterministic extraction stub for the parse-draft skeleton."""

from __future__ import annotations

from app.extraction.base import RawExtraction


class StubExtractor:
    """Returns no rows; the skeleton creates an unresolved draft."""

    def extract(
        self,
        masked_text: str,
        language_hint: str | None,
        request_id: str,
    ) -> RawExtraction:
        return RawExtraction()
