from app.clarification import build_clarification
from app.schemas import (
    Issue,
    IssueResolution,
    SaveLinesRequest,
    WorkingLine,
)


def _issue(code: str, *, kind: str | None = None, resolved: bool = False) -> Issue:
    return Issue(
        issue_id=f"ISS_{code}_{kind or 'X'}",
        code=code,
        condition_kind=kind,
        blocking=code != "STOCK",
        resolved=resolved,
    )


def test_price_condition_builds_clear_question():
    clarification, language = build_clarification(
        [_issue("CUSTOMER_CONDITION", kind="PRICE")],
        language_hint="ms",
    )
    assert clarification is not None
    assert language == "ms"
    assert clarification.language == "ms"
    assert clarification.unresolved_issue_ids == ["ISS_CUSTOMER_CONDITION_PRICE"]
    assert "harga" in clarification.message
    assert "confirmed" not in clarification.message.lower()


def test_missing_uom_and_insufficient_stock_have_templates():
    uom, _ = build_clarification([_issue("MISSING_UOM")], language_hint="en")
    stock, _ = build_clarification([_issue("INSUFFICIENT_STOCK")], language_hint="zh")
    assert uom is not None and "unit" in uom.message
    assert stock is not None and "库存" in stock.message


def test_no_unresolved_issue_returns_no_clarification():
    clarification, language = build_clarification([], language_hint="ms")
    assert clarification is None
    assert language is None


def test_resolved_issue_returns_no_clarification():
    clarification, language = build_clarification(
        [_issue("MISSING_UOM", resolved=True)], language_hint="en"
    )
    assert clarification is None
    assert language is None


def test_language_matches_message():
    for hint, expected in (("ms", "ms"), ("en-US", "en"), ("zh-Hans", "zh")):
        clarification, lang = build_clarification(
            [_issue("LOW_CONFIDENCE_MATCH")], language_hint=hint
        )
        assert clarification is not None
        assert lang == expected
        assert clarification.language == expected
    assert (
        "Sila"
        in build_clarification([_issue("LOW_CONFIDENCE_MATCH")], language_hint="ms")[0].message
    )
    assert (
        "Please"
        in build_clarification([_issue("LOW_CONFIDENCE_MATCH")], language_hint="en")[0].message
    )
    assert (
        "请" in build_clarification([_issue("LOW_CONFIDENCE_MATCH")], language_hint="zh")[0].message
    )


def test_multiple_issues_are_deduplicated_and_ids_are_stable():
    clarification, _ = build_clarification(
        [
            _issue("MISSING_UOM"),
            _issue("MISSING_UOM"),
            _issue("CUSTOMER_CONDITION", kind="PRICE"),
        ],
        language_hint="en",
    )
    assert clarification is not None
    assert len(clarification.unresolved_issue_ids) == 2
    assert clarification.message.count("Please confirm the unit") == 1


def test_condition_resolution_marks_condition_resolved_and_clears_clarification():
    from app.drafts import _validate_resolutions

    condition = _issue("CUSTOMER_CONDITION", kind="OTHER")
    line = WorkingLine(
        line_id="LNE_1",
        family_id="FAM_MILO",
        requested_qty=1,
        confirmed_qty=1,
        effective_qty=1,
        match_source="MANUAL_SELECTED",
    )
    body = SaveLinesRequest(
        expected_version=1,
        lines=[],
        resolutions=[
            IssueResolution(
                issue_id=condition.issue_id,
                choice="CONFIRMED_WITH_CUSTOMER",
                target_line_ids=["LNE_1"],
            )
        ],
    )
    conditions = [condition]
    _validate_resolutions(
        body,
        [{"issue_id": condition.issue_id}],
        [line],
        [],
        conditions,
    )
    assert conditions[0].resolved is True
    assert conditions[0].resolution == "CONFIRMED_WITH_CUSTOMER"
    clarification, language = build_clarification([], conditions, language_hint="en")
    assert clarification is None
    assert language is None
