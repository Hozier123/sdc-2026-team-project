"""Generate the Gate 0 ClarificationDraft from unresolved issues/conditions."""

from __future__ import annotations

from collections.abc import Iterable

from app.schemas import ClarificationDraft, Issue

_TEMPLATES: dict[str, dict[str, str]] = {
    "PRICE": {
        "ms": "Sila sahkan harga yang diminta sebelum pesanan diproses.",
        "en": "Please confirm the requested price before the order is processed.",
        "zh": "请先确认客户提出的价格，再处理订单。",
    },
    "STOCK": {
        "ms": "Sila sahkan ketersediaan stok atau pilih alternatif.",
        "en": "Please confirm stock availability or choose an alternative.",
        "zh": "请确认库存情况，或选择替代商品。",
    },
    "MISSING_UOM": {
        "ms": "Sila sahkan unit untuk item ini sebelum pesanan diproses.",
        "en": "Please confirm the unit for this item before processing.",
        "zh": "请先确认该商品的单位，再处理订单。",
    },
    "INSUFFICIENT_STOCK": {
        "ms": "Stok tidak mencukupi. Sila kurangkan kuantiti atau pilih alternatif.",
        "en": "Stock is insufficient. Please reduce the quantity or choose an alternative.",
        "zh": "库存不足，请减少数量或选择替代商品。",
    },
    "LOW_CONFIDENCE_MATCH": {
        "ms": "Sila sahkan produk dan kuantiti sebelum pesanan diproses.",
        "en": "Please confirm the product and quantity before processing.",
        "zh": "请先确认商品和数量，再处理订单。",
    },
    "MULTIPLE_PACK_SIZES": {
        "ms": "Sila pilih saiz pembungkusan yang betul.",
        "en": "Please choose the correct pack size.",
        "zh": "请选择正确的包装规格。",
    },
    "MULTIPLE_GRADES": {
        "ms": "Sila pilih gred produk yang betul.",
        "en": "Please choose the correct product grade.",
        "zh": "请选择正确的商品等级。",
    },
    "SAME_DAY_ORDER": {
        "ms": "Sila sahkan sama ada pesanan boleh dihantar pada hari yang sama.",
        "en": "Please confirm whether same-day delivery is possible.",
        "zh": "请确认是否可以当日送达。",
    },
    "UNUSUAL_QTY": {
        "ms": "Sila sahkan kuantiti luar biasa ini sebelum pesanan diproses.",
        "en": "Please confirm this unusual quantity before processing.",
        "zh": "请先确认这个异常数量，再处理订单。",
    },
    "GENERIC": {
        "ms": "Sila sahkan perkara yang belum diselesaikan sebelum pesanan diproses.",
        "en": "Please confirm the unresolved item before processing the order.",
        "zh": "请先确认未解决事项，再处理订单。",
    },
}


def _language(value: str | None) -> str:
    normalized = (value or "en").replace("_", "-").casefold()
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("ms"):
        return "ms"
    return "en"


def _key(issue: Issue) -> str:
    if issue.code == "CUSTOMER_CONDITION":
        kind = issue.condition_kind or "OTHER"
        return kind if kind in {"PRICE", "STOCK"} else "GENERIC"
    if issue.code in _TEMPLATES:
        return issue.code
    return "GENERIC"


def build_clarification(
    issues: Iterable[Issue],
    conditions: Iterable[Issue] = (),
    language_hint: str | None = None,
) -> tuple[ClarificationDraft | None, str | None]:
    """Return a clarification for unresolved issues, or (None, None)."""
    unresolved = [issue for issue in [*issues, *conditions] if not issue.resolved]
    if not unresolved:
        return None, None
    language = _language(language_hint)
    messages: list[str] = []
    issue_ids: list[str] = []
    for issue in unresolved:
        if issue.issue_id in issue_ids:
            continue
        issue_ids.append(issue.issue_id)
        message = _TEMPLATES[_key(issue)][language]
        if message not in messages:
            messages.append(message)
    return (
        ClarificationDraft(
            language=language,
            message=" ".join(messages),
            unresolved_issue_ids=issue_ids,
        ),
        language,
    )
