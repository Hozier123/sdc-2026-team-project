"""Small deterministic Gate 0 oracles used to execute H1/H5 truth tables.

These are contract-test reference implementations, not production business code.
"""

import json
import re
import unicodedata
from pathlib import Path


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


# ---------------------------------------------------------------------------
# H1: quantity / UOM
# ---------------------------------------------------------------------------

_DECIMAL = re.compile(r"(?<![\d.,])\d+\s*[.,]\s*\d+(?![\d.,])")
_AMOUNT = re.compile(r"(?i)\brm\s*\d+(?:\.\d{1,2})?")
_CODE = re.compile(r"(?i)\b[A-Za-z]{1,6}\d{1,8}\b")
_ARABIC = re.compile(r"(?<![A-Za-z0-9_.-])([1-9][0-9]{0,5})(?![0-9])")

_MS_UNITS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "lapan": 8, "delapan": 8, "sembilan": 9,
    "sepuluh": 10, "sebelas": 11,
}
_MS_TEENS = ("dua", "tiga", "empat", "lima", "enam", "tujuh", "lapan", "delapan", "sembilan")
_MS_ONES = ("satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "lapan", "delapan", "sembilan")
_EN_VALUES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
_EN_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_EN_ONES = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_ZH_VALUES = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
_ZH_TEENS = "一二三四五六七八九"
_ZH_TENS = "二三四五六七八九"


def _candidate_list(text):
    """Return (start, end, value) quantity candidates; longest match wins."""
    out = []

    for m in re.finditer(rf"\b({'|'.join(_MS_TEENS)})\s+belas\b", text):
        out.append((m.start(), m.end(), 10 + _MS_UNITS[m.group(1)]))

    for m in re.finditer(
        rf"\b({'|'.join(_MS_TEENS)})\s+puluh(?:\s+({'|'.join(_MS_ONES)}))?\b",
        text,
    ):
        value = _MS_UNITS[m.group(1)] * 10
        if m.group(2):
            value += _MS_UNITS[m.group(2)]
        out.append((m.start(), m.end(), value))

    for m in re.finditer(
        rf"\b({'|'.join(_EN_TENS)})(?:[-\s]({'|'.join(_EN_ONES)}))?\b",
        text,
    ):
        value = _EN_TENS[m.group(1)]
        if m.group(2):
            value += _EN_VALUES[m.group(2)]
        out.append((m.start(), m.end(), value))

    for m in re.finditer(rf"十([{_ZH_TEENS}])", text):
        out.append((m.start(), m.end(), 10 + _ZH_VALUES[m.group(1)]))

    for m in re.finditer(rf"([{_ZH_TENS}])十([{_ZH_TEENS}])?", text):
        value = _ZH_VALUES[m.group(1)] * 10
        if m.group(2):
            value += _ZH_VALUES[m.group(2)]
        out.append((m.start(), m.end(), value))

    for word, value in _MS_UNITS.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", text):
            out.append((m.start(), m.end(), value))

    for word, value in _EN_VALUES.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", text):
            out.append((m.start(), m.end(), value))

    for ch, value in _ZH_VALUES.items():
        for m in re.finditer(re.escape(ch), text):
            out.append((m.start(), m.end(), value))

    for m in _ARABIC.finditer(text):
        out.append((m.start(), m.end(), int(m.group(1))))

    # earliest occurrence first; at the same start, longest span first.
    out.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    return out


_H1_LEXICON = Path(__file__).parents[2] / "contracts" / "lexicons" / "field-evidence-v2.json"


def _mask_with(pattern, text):
    return re.sub(pattern, lambda m: " " * len(m.group(0)), text, flags=re.IGNORECASE)


def parse_quantity(span):
    """Return (qty, reason, start, end) in normalized-span coordinates.

    The Adapter maps these offsets back to masked_text code points.
    """
    value = normalize(span)
    lexicon = json.loads(_H1_LEXICON.read_text(encoding="utf-8"))
    qrules = lexicon["quantity"]

    # Unit-price markers are removed before amount removal so "RM2.50 satu"
    # cannot leave the marker as a false qty candidate.
    masked = _mask_with(qrules["unit_price_marker_pattern"], value)
    masked = _mask_with(rules := qrules["qty_exclude_pattern"], masked)
    masked = _mask_with(qrules["code_exclude_pattern"], masked)

    # Pack-size numbers are spec, not order quantity. Only exclude them when
    # another qty candidate exists (or the span is an explicit x/装 spec),
    # so "10kg bawang" remains qty=10 while "Tipe 5kg x 2" becomes 2.
    before = _candidate_list(masked)
    if len({v for _, _, v in before}) > 1 or re.search(r"\d\s*x\s*\d|装", masked, re.IGNORECASE):
        for pattern in lexicon["pack_size"]["patterns"]:
            masked = _mask_with(pattern, masked)

    if re.search(qrules["decimal_guard_pattern"], masked) or re.search(
        qrules["decimal_comma_unit_pattern"], masked
    ):
        return None, "INVALID_QUANTITY", None, None

    candidates = _candidate_list(masked)
    if not candidates:
        return None, None, None, None

    # Rule 7: two distinct non-overlapping qty values are not a guess.
    distinct = []
    cursor = -1
    for s, e, val in candidates:
        if s >= cursor:
            distinct.append((s, e, val))
            cursor = e
    if len({v for _, _, v in distinct}) > 1:
        return None, "AMBIGUOUS_QUANTITY", None, None
    start, end, qty = distinct[0]
    return qty, None, start, end


def parse_pack_size(span):
    value = " ".join(span.split())
    lexicon = json.loads(_H1_LEXICON.read_text(encoding="utf-8"))
    for pattern in lexicon["pack_size"]["patterns"]:
        m = re.search(pattern, value, re.IGNORECASE)
        if m:
            text = m.group(0).strip()
            return re.sub(r"\s*(?:装|pack|packs)$", "", text, flags=re.IGNORECASE)
    return None


def _parse_uom(span):
    value = normalize(span)
    lexicon = json.loads(_H1_LEXICON.read_text(encoding="utf-8"))
    aliases = lexicon["uom_aliases"]
    for canonical, values in aliases.items():
        for alias in values:
            a = normalize(alias)
            if a.isascii():
                if re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", value):
                    return canonical
            elif a in value:
                return canonical
    # Tenant-level extensions are still explicit aliases, not a private oracle table.
    for alias, canonical in lexicon.get("tenant_uom_extensions", {}).items():
        a = normalize(alias)
        if a.isascii():
            if re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", value):
                return canonical
        elif a in value:
            return canonical
    return None


def evaluate_h1_case(case):
    if "spans" in case:
        ordered = sorted(case["spans"])
        overlap = any(current[0] < previous[1] for previous, current in zip(ordered, ordered[1:]))
        return {
            "issue": "LOW_CONFIDENCE_MATCH" if overlap else None,
            "reason_code": "OVERLAPPING_SPAN" if overlap else None,
        }

    span = normalize(case["span"])
    qty, invalid_reason, qty_start, qty_end = parse_quantity(span)
    uom = _parse_uom(span)
    pack_size = parse_pack_size(case["span"])
    result = {"qty": qty, "uom": uom, "pack_size": pack_size}
    if qty_start is not None:
        result.update(qty_start=qty_start, qty_end=qty_end)
    if invalid_reason:
        result.update(issue="LOW_CONFIDENCE_MATCH", reason_code=invalid_reason)

    model_qty = case.get("model_qty")
    if isinstance(model_qty, str) and model_qty.isascii() and model_qty.isdigit():
        coerced = int(model_qty)
        result["diagnostic"] = "MODEL_TYPE_COERCED"
        if qty is not None and coerced == qty:
            result["model_value_accepted"] = True
        else:
            result["model_value_accepted"] = False
            result.update(issue="LOW_CONFIDENCE_MATCH", reason_code="FIELD_NOT_EVIDENCED")
    elif model_qty is not None and model_qty != qty:
        result["model_value_accepted"] = False
        if isinstance(model_qty, int):
            result.update(issue="LOW_CONFIDENCE_MATCH", reason_code="FIELD_NOT_EVIDENCED")

    model_family = case.get("model_family")
    if model_family is not None and normalize(model_family) not in span:
        result.update(
            family="UNKNOWN",
            issue="LOW_CONFIDENCE_MATCH",
            reason_code="FAMILY_NOT_EVIDENCED",
        )
    return result


# ---------------------------------------------------------------------------
# H5: condition triggers
# ---------------------------------------------------------------------------

_H5_LEXICON = Path(__file__).parents[2] / "contracts" / "lexicons" / "condition-triggers-v3.json"
_AMOUNT_VALUE = re.compile(r"\brm\s*\d+(?:\.\d{1,2})?\b", re.IGNORECASE)
_ALLOCATION = re.compile(
    r"\brm\s*\d+(?:\.\d{1,2})?\s+for\s+[1-9]\d*\s+(?:ctn|cartons?|packs?|bags?|pcs?)\b",
    re.IGNORECASE,
)
_UNIT_PRICE = re.compile(
    r"\brm\s*\d+(?:\.\d{1,2})?\s+(?:untuk\s+1|per)\s+(?:ctn|cartons?|packs?|bags?|pcs?|kg)\b",
    re.IGNORECASE,
)


def _h5_lexicon():
    return json.loads(_H5_LEXICON.read_text(encoding="utf-8"))


def _context_ok(value, trigger, lexicon):
    if not trigger.get("requires_context"):
        return True
    negatives = [normalize(n) for n in lexicon.get("negative_contexts", []) if "<" not in n]
    if any(token in value for token in negatives):
        return False
    markers = [normalize(m) for m in lexicon.get("context_markers", [])]
    return any(token in value for token in markers)


def detect_condition_kinds(text):
    value = normalize(text)
    lexicon = _h5_lexicon()
    kinds = []

    for trigger in lexicon["triggers"]:
        if trigger["kind"] == "STOCK" and re.search(trigger["pattern"], value, re.IGNORECASE):
            kinds.append("STOCK")
            break

    explicit_price = False
    for trigger in lexicon["triggers"]:
        if trigger["kind"] != "PRICE":
            continue
        if trigger.get("requires_context") and not _context_ok(value, trigger, lexicon):
            continue
        if re.search(trigger["pattern"], value, re.IGNORECASE):
            explicit_price = True
            break

    amount = bool(_AMOUNT_VALUE.search(value))
    amount_with_context = amount and any(
        token in value for token in ("kalau", "if ", "?", "？")
    )
    allocation = bool(_ALLOCATION.search(value))

    if explicit_price or amount_with_context or allocation:
        kinds.append("PRICE")

    for trigger in lexicon["triggers"]:
        if trigger["kind"] == "TIME_OR_OTHER" and re.search(trigger["pattern"], value, re.IGNORECASE):
            kinds.append("OTHER")
            break

    return kinds


def evaluate_condition(text):
    kinds = detect_condition_kinds(text)
    value = normalize(text)
    return {
        "kinds": kinds,
        "price_basis": ("UNIT" if _UNIT_PRICE.search(value) else "UNKNOWN") if "PRICE" in kinds else None,
        "blocking": "PRICE" in kinds,
    }
