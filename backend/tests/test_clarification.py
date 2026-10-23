from decimal import Decimal

from app.clarification import build_clarification, detect_language
from app.replies import build_reply
from app.schemas import (
    DeliveryOrderLine,
    Issue,
    IssueResolution,
    SaveLinesRequest,
    SkuCandidate,
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


def _candidate_line() -> WorkingLine:
    return WorkingLine(
        line_id="LNE_1",
        family_id="FAM_MILO",
        description="Milo",
        requested_qty=2,
        effective_qty=2,
        uom="bag",
        match_source="MANUAL_SELECTED",
        candidate_skus=[
            SkuCandidate(
                sku_id="SKU_MILO_1KG",
                family_id="FAM_MILO",
                display_name="Milo 1kg",
                pack_size="1kg",
                base_unit="bag",
                tier_unit_price="18.00",
                available_qty=30,
            ),
            SkuCandidate(
                sku_id="SKU_MILO_2KG",
                family_id="FAM_MILO",
                display_name="Milo 2kg",
                pack_size="2kg",
                base_unit="bag",
                tier_unit_price="34.00",
                available_qty=20,
            ),
        ],
    )


def test_language_detection_uses_text_not_only_hint():
    assert detect_language("Boss nak ambil 2 ctn") == "ms"
    assert detect_language("Please confirm 2 ctn") == "en"
    assert detect_language("老板，要两箱") == "zh"
    assert detect_language("nak please") == "ms"
    assert detect_language("Milo 2 ctn") == "en"


def test_clarification_includes_item_and_candidate_pack_prices():
    line = _candidate_line()
    issue = _issue("MULTIPLE_PACK_SIZES")
    issue.line_id = "LNE_1"
    clarification, language = build_clarification(
        [issue],
        lines=[line],
        masked_text="Milo 2 bag",
    )
    assert clarification is not None
    assert language == "en"
    assert "Milo" in clarification.message
    assert "1kg" in clarification.message
    assert "2kg" in clarification.message
    assert "RM 18.00" in clarification.message
    assert "RM 34.00" in clarification.message


def test_clarification_includes_available_stock_and_item():
    line = _candidate_line().model_copy(update={"available_qty": 2, "sku_id": "SKU_MILO_1KG"})
    issue = _issue("INSUFFICIENT_STOCK")
    issue.line_id = "LNE_1"
    clarification, _ = build_clarification(
        [issue],
        lines=[line],
        language_hint="en",
    )
    assert clarification is not None
    assert "Milo" in clarification.message
    assert "2 bag" in clarification.message
    assert "only have 2 bag" in clarification.message


def test_same_day_wording_is_not_delivery_promise():
    clarification, _ = build_clarification(
        [_issue("SAME_DAY_ORDER")],
        language_hint="en",
    )
    assert clarification is not None
    assert "existing order today" in clarification.message
    assert "delivery" not in clarification.message.lower()


def test_more_than_five_questions_adds_callback_instruction():
    issues = [
        Issue(
            issue_id=f"ISS_{i}",
            code="LOW_CONFIDENCE_MATCH",
            span=f"item-{i}",
            blocking=True,
            resolved=False,
        )
        for i in range(6)
    ]
    clarification, _ = build_clarification(issues, language_hint="en")
    assert clarification is not None
    assert "call the customer directly" in clarification.message
    assert len(clarification.unresolved_issue_ids) == 6


def test_confirmation_reply_contains_lines_total_and_language():
    lines = [
        DeliveryOrderLine(
            line_id="LNE_1",
            sku_id="SKU_MILO_1KG",
            display_name="Milo 1kg",
            quantity=2,
            unit="bag",
            tier_unit_price="18.00",
            applied_unit_price="18.00",
            subtotal_rm="36.00",
        )
    ]
    for language, marker, total_marker in (
        ("ms", "dah confirm", "Jumlah RM 36.00"),
        ("zh", "已确认", "合计 RM 36.00"),
        ("en", "confirmed", "Total RM 36.00"),
    ):
        reply = build_reply("DO_TEST", lines, Decimal("36.00"), language)
        assert reply.language == language
        assert "DO_TEST" in reply.message
        assert "Milo 1kg" in reply.message
        assert "2 bag" in reply.message
        assert marker in reply.message
        assert total_marker in reply.message
