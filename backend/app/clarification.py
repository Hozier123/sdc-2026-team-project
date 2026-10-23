"""Template-only clarification and confirmation messages for Gate 0.

All business values come from the persisted draft/DO and catalog. The model is
never asked to write customer-facing text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.schemas import ClarificationDraft, Issue, WorkingLine

_MS_WORDS = {
    "nak",
    "boleh",
    "ambil",
    "bagi",
    "lagi",
    "kalau",
    "tolong",
    "hantar",
    "esok",
    "sikit",
    "dan",
    "tak",
    "ada",
}
_EN_WORDS = {"please", "can", "want", "need", "and", "the", "if"}
_HAN = re.compile(r"[\u3400-\u9fff]")

_OPEN = {
    "ms": "Sila sahkan pesanan ini:",
    "en": "Please confirm this order:",
    "zh": "请确认这张订单：",
}
_CLOSE = {"ms": "Terima kasih!", "en": "Thank you!", "zh": "谢谢！"}
_TOO_MANY = {
    "ms": "Ada lebih daripada 5 perkara. Sila hubungi pelanggan secara terus.",
    "en": "There are more than 5 questions. Please call the customer directly.",
    "zh": "问题超过 5 个，请直接电话联系客户。",
}


def _hint(value: str | None) -> str | None:
    normalized = (value or "").replace("_", "-").casefold()
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("ms"):
        return "ms"
    if normalized.startswith("en"):
        return "en"
    return None


def detect_language(text: str | None) -> str:
    """Frozen Gate 0 rule: Han/2, Malay words, English words; ties use Malay."""
    value = text or ""
    han = len(_HAN.findall(value)) / 2
    words = re.findall(r"[a-z]+", value.casefold())
    ms = sum(1 for word in words if word in _MS_WORDS)
    en = sum(1 for word in words if word in _EN_WORDS)
    if han == 0 and ms == 0 and en == 0:
        return "en"
    if han >= ms and han >= en:
        return "zh"
    return "ms" if ms >= en else "en"


def _language(language_hint: str | None, text: str) -> str:
    return _hint(language_hint) or detect_language(text)


def _key(issue: Issue) -> str:
    if issue.code == "CUSTOMER_CONDITION":
        kind = issue.condition_kind or "OTHER"
        return kind if kind in {"PRICE", "STOCK", "OTHER"} else "GENERIC"
    if issue.code in {
        "MISSING_UOM",
        "INSUFFICIENT_STOCK",
        "LOW_CONFIDENCE_MATCH",
        "MULTIPLE_PACK_SIZES",
        "MULTIPLE_GRADES",
        "SAME_DAY_ORDER",
        "UNUSUAL_QTY",
    }:
        return issue.code
    return "GENERIC"


def _line_for(issue: Issue, lines: dict[str, WorkingLine]) -> WorkingLine | None:
    if issue.line_id and issue.line_id in lines:
        return lines[issue.line_id]
    for target in (*issue.target_line_ids, *issue.candidate_line_ids):
        if target in lines:
            return lines[target]
    if len(lines) == 1:
        return next(iter(lines.values()))
    return None


def _item(line: WorkingLine | None, issue: Issue) -> str:
    if line is not None:
        return line.description or line.sku_id or issue.span or "item"
    return issue.span or "item"


def _options(line: WorkingLine | None, field: str) -> list[str]:
    if line is None:
        return []
    options: list[str] = []
    for candidate in line.candidate_skus:
        value = getattr(candidate, field)
        if not value:
            continue
        label = str(value)
        if candidate.tier_unit_price:
            label += f" (RM {candidate.tier_unit_price}/{candidate.base_unit})"
        if label not in options:
            options.append(label)
    return options


def _price(line: WorkingLine | None) -> str | None:
    if line is None or not line.tier_unit_price:
        return None
    return f"RM {line.tier_unit_price}/{line.uom or 'UNIT'}"


def _generic(issue: Issue, line: WorkingLine | None, language: str) -> str:
    item = _item(line, issue)
    span = issue.span or item
    if language == "ms":
        return f'Boleh sahkan "{span}" untuk {item}?'
    if language == "zh":
        return f"想确认一下：“{span}”？"
    return f'Could you confirm "{span}" for {item}?'


def _question(issue: Issue, line: WorkingLine | None, language: str) -> str:
    key = _key(issue)
    item = _item(line, issue)
    if key in {"MULTIPLE_PACK_SIZES", "MULTIPLE_GRADES", "MISSING_UOM"}:
        if line is not None and line.candidate_skus:
            field = "grade" if key == "MULTIPLE_GRADES" else "pack_size"
            if key == "MISSING_UOM":
                field = "base_unit"
            options = _options(line, field)
            if options:
                joined = " / ".join(options)
                if language == "ms":
                    return f"{item} nak {joined}?"
                if language == "zh":
                    return f"{item} 要 {joined}？"
                return f"{item}: {joined}?"
        if key == "MULTIPLE_PACK_SIZES" and line and line.pack_size:
            return (
                f"Sila sahkan saiz pembungkusan {item}: {line.pack_size}?"
                if language == "ms"
                else (
                    f"请确认 {item} 的包装规格：{line.pack_size}？"
                    if language == "zh"
                    else f"Please confirm the pack size for {item}: {line.pack_size}?"
                )
            )
        if key == "MULTIPLE_GRADES" and line and line.grade:
            return (
                f"Sila sahkan gred {item}: {line.grade}?"
                if language == "ms"
                else (
                    f"请确认 {item} 的等级：{line.grade}？"
                    if language == "zh"
                    else f"Please confirm the grade for {item}: {line.grade}?"
                )
            )
        if key == "MULTIPLE_PACK_SIZES":
            return {
                "ms": f"Sila pilih saiz pembungkusan yang betul untuk {item}.",
                "zh": f"请选择 {item} 的正确包装规格。",
                "en": f"Please choose the correct pack size for {item}.",
            }[language]
        if key == "MULTIPLE_GRADES":
            return {
                "ms": f"Sila pilih gred yang betul untuk {item}.",
                "zh": f"请选择 {item} 的正确等级。",
                "en": f"Please choose the correct grade for {item}.",
            }[language]
        return {
            "ms": f"Sila sahkan unit untuk {item}.",
            "zh": f"请确认 {item} 的单位。",
            "en": f"Please confirm the unit for {item}.",
        }[language]
    if key == "INSUFFICIENT_STOCK":
        available = line.available_qty if line and line.available_qty is not None else None
        if available is None:
            available = issue.data_used.get("available_qty")
        if available is None:
            return {
                "ms": "Sila sahkan ketersediaan stok atau pilih alternatif.",
                "zh": "请确认库存情况，或选择替代商品。",
                "en": "Please confirm stock availability or choose an alternative.",
            }[language]
        unit = (line.uom if line and line.uom else None) or "unit"
        if language == "ms":
            return f"Stok {item} tinggal {available} {unit}. Nak ambil {available} {unit}?"
        if language == "zh":
            return f"{item} 现在只有 {available} {unit}，先拿 {available} {unit} 可以吗？"
        return f"We only have {available} {unit} of {item}. Is {available} {unit} OK?"
    if key == "PRICE":
        price = _price(line)
        if price and line and line.effective_qty and line.uom:
            if language == "ms":
                return f"Harga {item} {price}. Masih nak ambil {line.effective_qty} {line.uom}?"
            if language == "zh":
                return f"{item} 价格是 {price}，还是要 {line.effective_qty} {line.uom} 吗？"
            return f"{item} is {price}. Still want {line.effective_qty} {line.uom}?"
        span = issue.span or item
        if language == "ms":
            return f'Sila sahkan harga yang diminta untuk "{span}".'
        if language == "zh":
            return f"请确认“{span}”的价格。"
        return f'Please confirm the requested price for "{span}".'
    if key == "SAME_DAY_ORDER":
        return {
            "ms": (
                "Sila sahkan sama ada ini pesanan tambahan kepada pesanan yang sudah ada hari ini."
            ),
            "zh": "请确认这是否是今天已有订单的追加订单。",
            "en": (
                "Please confirm whether this is an additional order "
                "on top of an existing order today."
            ),
        }[language]
    if key == "LOW_CONFIDENCE_MATCH":
        span = issue.span or item
        if language == "ms":
            return f'"{span}" tu barang yang mana?'
        if language == "zh":
            return f"“{span}”是指哪一个产品？"
        return f'Which item do you mean by "{span}"?'
    if key == "UNUSUAL_QTY":
        qty = line.effective_qty if line else issue.data_used.get("effective_qty")
        if language == "ms":
            return f"Sila sahkan kuantiti {qty} untuk {item}."
        if language == "zh":
            return f"请确认 {item} 的数量 {qty}。"
        return f"Please confirm the quantity {qty} for {item}."
    return _generic(issue, line, language)


def build_clarification(
    issues: Iterable[Issue],
    conditions: Iterable[Issue] = (),
    language_hint: str | None = None,
    *,
    lines: Iterable[WorkingLine] = (),
    masked_text: str = "",
) -> tuple[ClarificationDraft | None, str | None]:
    """Return a three-language, data-filled clarification, or (None, None)."""
    unresolved = [
        issue
        for issue in [*issues, *conditions]
        if not issue.resolved and issue.condition_kind != "STOCK"
    ]
    if not unresolved:
        return None, None
    line_map = {line.line_id: line for line in lines}
    language = _language(language_hint, masked_text)
    issue_ids: list[str] = []
    questions: list[str] = []
    for issue in unresolved:
        if issue.issue_id in issue_ids:
            continue
        issue_ids.append(issue.issue_id)
        line = _line_for(issue, line_map)
        question = _question(issue, line, language)
        if question not in questions:
            questions.append(question)
    if len(questions) > 5:
        questions = questions[:5] + [_TOO_MANY[language]]
    message = " ".join([_OPEN[language], *questions, _CLOSE[language]])
    if len(message) > 2000:
        message = message[:1997].rstrip() + "..."
    return (
        ClarificationDraft(
            language=language,
            message=message,
            unresolved_issue_ids=issue_ids,
        ),
        language,
    )
