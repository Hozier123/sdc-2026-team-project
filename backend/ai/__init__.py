"""AI package for KiraOrder."""

from backend.ai.fallback import (
    FallbackLine,
    extract_fallback_line,
    extract_fallback_order,
    split_into_candidate_spans,
)

__all__ = [
    "FallbackLine",
    "extract_fallback_line",
    "extract_fallback_order",
    "split_into_candidate_spans",
]
