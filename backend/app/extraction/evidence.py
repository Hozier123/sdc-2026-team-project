"""Deterministic quantity evidence from the frozen H1 lexicon.

This is an evidence guard, not a SKU resolver or an extraction fallback.
Offsets are projected back to original masked Unicode code points.
"""

import json
import re
import unicodedata
from functools import lru_cache

from app.config import REPO_ROOT


@lru_cache(maxsize=1)
def lexicon():
    return json.loads(
        (REPO_ROOT / "gate0/contracts/lexicons/field-evidence-v2.json").read_text(encoding="utf-8")
    )


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def projected(value):
    chars, starts, ends = [], [], []
    for match in re.finditer(r"[^\W\d_][\u0300-\u036f]*|.", value, re.DOTALL):
        for char in unicodedata.normalize("NFKC", match.group()).casefold():
            if char.isspace():
                if chars and chars[-1] == " ":
                    ends[-1] = match.end()
                    continue
                char = " "
            chars.append(char)
            starts.append(match.start())
            ends.append(match.end())
    return "".join(chars), starts, ends


def candidates(text):
    rules = lexicon()["quantity"]
    out = []

    def add(pattern, value):
        for match in re.finditer(pattern, text):
            out.append((match.start(), match.end(), value(match)))

    ms, en, zh = rules["ms_units"], rules["en_values"], rules["zh_values"]
    ms_tens = "|".join(word for word, number in ms.items() if 2 <= number <= 9)
    ms_ones = "|".join(word for word, number in ms.items() if 1 <= number <= 9)
    add(rf"\b({ms_tens}) belas\b", lambda m: 10 + ms[m[1]])
    add(
        rf"\b({ms_tens}) puluh(?: ({ms_ones}))?\b",
        lambda m: ms[m[1]] * 10 + (ms[m[2]] if m[2] else 0),
    )
    tens = dict(
        zip(
            ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"),
            range(20, 100, 10),
            strict=True,
        )
    )
    ones = "|".join(word for word, number in en.items() if number < 10)
    add(
        rf"\b({'|'.join(tens)})(?:[- ]({ones}))?\b",
        lambda m: tens[m[1]] + (en[m[2]] if m[2] else 0),
    )
    add(r"十([一二三四五六七八九])", lambda m: 10 + zh[m[1]])
    add(
        r"([二三四五六七八九])十([一二三四五六七八九])?",
        lambda m: zh[m[1]] * 10 + (zh[m[2]] if m[2] else 0),
    )
    for mapping in (ms, en):
        for word, number in mapping.items():
            add(rf"\b{word}\b", lambda m, n=number: n)
    for word, number in zh.items():
        add(word, lambda m, n=number: n)
    add(rules["arabic_pattern"], lambda m: int(m[1]))
    return sorted(out, key=lambda candidate: (candidate[0], -(candidate[1] - candidate[0])))


def quantity_evidence(span):
    text, starts, ends = projected(span)
    rules = lexicon()["quantity"]

    def mask(pattern, value):
        return re.sub(pattern, lambda m: " " * len(m.group()), value, flags=re.IGNORECASE)

    masked = text
    for rule in ("unit_price_marker_pattern", "qty_exclude_pattern", "code_exclude_pattern"):
        masked = mask(rules[rule], masked)
    masked = mask(r"\b\d{1,4}[-/]\d{1,2}(?:[-/]\d{1,4})?\b", masked)
    if len({c[2] for c in candidates(masked)}) > 1 or re.search(r"\d\s*x\s*\d|装", masked):
        for pattern in lexicon()["pack_size"]["patterns"]:
            masked = mask(pattern, masked)
    if (
        re.search(rules["decimal_guard_pattern"], masked)
        or re.search(rules["decimal_comma_unit_pattern"], masked)
        or re.search(r"(?<!\w)[+-]\d", masked)
    ):
        return None, "INVALID_QUANTITY", None, None
    chosen, end = [], -1
    for candidate in candidates(masked):
        if candidate[0] >= end:
            chosen.append(candidate)
            end = candidate[1]
    if not chosen:
        return None, "INVALID_QUANTITY", None, None
    if len({c[2] for c in chosen}) > 1:
        return None, "AMBIGUOUS_QUANTITY", None, None
    start, end, quantity = chosen[0]
    return quantity, None, starts[start], ends[end - 1]


def exact_phrase(phrase, span):
    phrase = normalize(phrase)
    if not phrase:
        return False
    pattern = re.escape(phrase)
    if phrase[0].isascii() and phrase[0].isalnum():
        pattern = r"(?<![a-z])" + pattern
    if phrase[-1].isascii() and phrase[-1].isalnum():
        pattern += r"(?![a-z])"
    return re.search(pattern, normalize(span)) is not None


def evidenced_uom(value, span, units):
    """Return the tenant canonical unit only when the span evidences it.

    `units` is an iterable of `(canonical_unit, alias)` pairs from the tenant
    `uom_aliases` table plus the H1 lexicon. The provider may return either the
    canonical form ("btl"/"pail") or the surface alias ("botol"/"pail"); both
    are accepted only when the alias itself appears in the masked span. A
    surface alias is never inferred from the SKU or the pack size, and tenant
    aliases are only looked up from the caller's own tenant rows.
    """
    if not value:
        return None
    wanted = normalize(value)
    for canonical, alias in units:
        if normalize(canonical) != wanted and normalize(alias) != wanted:
            continue
        if exact_phrase(alias, span):
            return canonical
    return None


def pack_size_evidence(span):
    """Return (value, start, end) for a registered pack-size pattern."""
    if not span:
        return None
    text, starts, ends = projected(span)
    best = None
    for pattern in lexicon()["pack_size"]["patterns"]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if best is None or (match.end() - match.start()) > (best[2] - best[1]):
                best = (match.group(), match.start(), match.end())
    if best is None:
        return None
    start, end = best[1], best[2]
    while end > start and span[starts[end - 1] : ends[end - 1]].isspace():
        end -= 1
    value = span[starts[start] : ends[end - 1]]
    value = re.sub(r"\s*(?:装|pack|packs)\s*$", "", value, flags=re.IGNORECASE).strip()
    return value, starts[start], ends[end - 1]
