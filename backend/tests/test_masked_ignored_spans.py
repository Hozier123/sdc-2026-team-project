"""Regression tests for preserving masked PII tokens in ignored_spans."""

from __future__ import annotations

from app.ai.adapter import _merge_masked_ignored_spans


def test_masked_token_is_added_when_model_omits_it():
    text = "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]"
    assert _merge_masked_ignored_spans(text, []) == ["[REDACTED_PHONE]"]


def test_masked_token_is_not_duplicated():
    text = "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]"
    assert _merge_masked_ignored_spans(text, ["[REDACTED_PHONE]"]) == ["[REDACTED_PHONE]"]


def test_model_ignored_spans_are_kept_and_masked_tokens_appended():
    text = "hantar esok [REDACTED_PHONE]"
    assert _merge_masked_ignored_spans(text, ["hantar esok"]) == [
        "hantar esok",
        "[REDACTED_PHONE]",
    ]
