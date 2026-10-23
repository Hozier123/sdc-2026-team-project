"""Template-only post-approval confirmation reply."""

from __future__ import annotations

from decimal import Decimal

from app.clarification import detect_language
from app.schemas import DeliveryOrderLine, ReplyDraft


def _line_text(line: DeliveryOrderLine) -> str:
    return f"{line.display_name} {line.quantity} {line.unit} @ RM {line.applied_unit_price}"


def build_reply(
    do_number: str,
    lines: list[DeliveryOrderLine],
    total: Decimal,
    language: str,
    warnings: list[str] | None = None,
) -> ReplyDraft:
    """Build the multilingual confirmation draft from persisted DO values."""
    selected = language if language in {"ms", "zh", "en"} else detect_language("")
    items = "; ".join(_line_text(line) for line in lines)
    total_text = f"{total:.2f}"
    if selected == "ms":
        message = f"Order {do_number} dah confirm: {items}. Jumlah RM {total_text}. Terima kasih!"
    elif selected == "zh":
        message = f"订单 {do_number} 已确认：{items}。合计 RM {total_text}。谢谢！"
    else:
        message = f"Order {do_number} confirmed: {items}. Total RM {total_text}. Thank you!"
    return ReplyDraft(
        language=selected,
        message=message,
        do_number=do_number,
        warnings=warnings or [],
    )
