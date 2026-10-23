"""Deterministic pre-segmentation and RapidFuzz offline fallback extractor for KiraOrder.

Complies strictly with Gate 0 v4 contract and Review Revision v2:
- Zero hardcoding: dynamically loads field-evidence-v2.json via multi-candidate search
- No duplicate safety lexicon: failure to load lexicon triggers FileNotFoundError (mapped to 503)
- Precision H1 pipeline:
    UnitPriceMarkerMask -> AmountMask (with thousands comma) -> CodeMask
    -> CommaDecimalGuard (strict no-space + comma_unit) -> PackSizeMask
    -> DotDecimalGuard -> Candidates -> AmbiguityCheck
- Zero impact on all 35 required H1 cases while blocking '1,5kg', '0,5 ctn', '2.5 ctn'
"""

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Sequence, Tuple

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize text using NFKC, casefold, and whitespace collapsing."""
    nfkc = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(nfkc.split())


def normalize_text_with_map(text: str) -> Tuple[str, List[int]]:
    """Normalize text using NFKC, casefold, and whitespace collapsing while tracking index map.

    Returns:
        (normalized_str, index_map)
        where index_map[norm_i] points to the original Unicode code point index in `text`.
    """
    if not text:
        return "", []

    # Step 1: NFKC + map
    nfkc_chars: List[str] = []
    nfkc_map: List[int] = []
    for orig_idx, ch in enumerate(text):
        norm_ch = unicodedata.normalize("NFKC", ch)
        for sub_ch in norm_ch:
            nfkc_chars.append(sub_ch)
            nfkc_map.append(orig_idx)

    # Step 2: casefold + map
    cf_chars: List[str] = []
    cf_map: List[int] = []
    for ch, orig_idx in zip(nfkc_chars, nfkc_map, strict=False):
        folded = ch.casefold()
        for f_ch in folded:
            cf_chars.append(f_ch)
            cf_map.append(orig_idx)

    # Step 3: whitespace collapse + strip
    norm_chars: List[str] = []
    index_map: List[int] = []
    in_ws = False

    start_i = 0
    while start_i < len(cf_chars) and cf_chars[start_i].isspace():
        start_i += 1

    end_i = len(cf_chars)
    while end_i > start_i and cf_chars[end_i - 1].isspace():
        end_i -= 1

    for i in range(start_i, end_i):
        ch = cf_chars[i]
        orig_idx = cf_map[i]
        if ch.isspace():
            if not in_ws:
                norm_chars.append(" ")
                index_map.append(orig_idx)
                in_ws = True
        else:
            norm_chars.append(ch)
            index_map.append(orig_idx)
            in_ws = False

    normalized_str = "".join(norm_chars)
    return normalized_str, index_map


def _find_lexicon_path() -> Path:
    """Locate field-evidence-v2.json in order of precedence without development machine hardcoding."""
    # 1. Explicit environment variable override
    env_path = os.getenv("KIRAORDER_FIELD_EVIDENCE_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    # 2. Candidate paths walking up from current file
    current_dir = Path(__file__).resolve().parent
    repo_candidates = [
        current_dir.parents[1],  # project root
        current_dir.parents[0],
        current_dir.parents[2] if len(current_dir.parents) > 2 else current_dir,
    ]

    relative_subpaths = [
        Path("gate0/contracts/lexicons/field-evidence-v2.json"),
        Path("Gate 0/contracts/lexicons/field-evidence-v2.json"),
        Path("最终gate/Gate 0/contracts/lexicons/field-evidence-v2.json"),
    ]

    for root in repo_candidates:
        for sub in relative_subpaths:
            cand = root / sub
            if cand.is_file():
                return cand

    raise FileNotFoundError(
        "Gate 0 field-evidence-v2.json not found. "
        "Ensure gate0/contracts/lexicons/ is copied to the container or set KIRAORDER_FIELD_EVIDENCE_PATH."
    )


def load_h1_lexicon() -> Dict[str, Any]:
    """Load and parse the Gate 0 H1 field evidence lexicon."""
    lex_path = _find_lexicon_path()
    return json.loads(lex_path.read_text(encoding="utf-8"))


# Fallback / Seed Catalog (Sinaran T1 baseline for offline fallback)
DEFAULT_SEED_CATALOG: Final[Dict[str, Sequence[str]]] = {
    "FAM_FLOUR": ("Tepung", "Flour", "Tepung Gandum", "Wheat Flour", "面粉"),
    "FAM_RICE": ("Beras", "Rice", "Beras Wangi", "Fragrant Rice", "米", "白米"),
    "FAM_OIL": ("Minyak", "Cooking Oil", "Minyak Masak", "Oil", "食用油", "油"),
    "FAM_SUGAR": ("Gula", "Sugar", "Gula Pasir", "White Sugar", "白糖", "糖"),
    "FAM_SALT": ("Garam", "Salt", "Garam Halus", "盐"),
    "FAM_EGG": ("Telur", "Egg", "Telur Ayam", "鸡蛋", "蛋"),
}

# Pre-segmentation Regexes:
# Strict rule: Only split on newlines, semicolons, and list numbers.
# NEVER split on commas or conjunctions (and, dan, 和).
# Dot in numbering list must NOT be followed by a digit (?!\d), preventing '2.5 ctn' slicing.
_COARSE_SPLIT_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\r\n;；]+", re.UNICODE)
_INLINE_NUM_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:^|\s+)(?:\d+\.(?!\d)|\d+\)|\([0-9]+\))\s+", re.UNICODE
)
_LEADING_NUM_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:\d+\.(?!\d)|\d+\)|\([0-9]+\))\s*", re.UNICODE
)

_ARABIC = re.compile(r"(?<![A-Za-z0-9_.-])([1-9][0-9]{0,5})(?![0-9])")
_GRADE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:grade|gred)\s*([a-c0-9]+)\b", re.IGNORECASE
)

# Strict no-space comma decimal guard: matches 1,5 or 0,5 without spaces (blocks 1,5kg, 0,5 ctn)
_STRICT_COMMA_DECIMAL = re.compile(r"(?<![\d.,])\d+,\d+(?![\d.,])")
# Currency amount with thousands commas: RM 1,200 or RM1,200.50
_AMOUNT_WITH_THOUSANDS = re.compile(r"(?i)\brm\s*\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?")
# Currency amount with comma decimal: RM2,50 or RM12,50 (Malaysian/Indonesian decimal notation)
_AMOUNT_WITH_COMMA_DECIMAL = re.compile(r"(?i)\brm\s*\d+,\d{1,2}(?!\d)")

_MS_TEENS = ("dua", "tiga", "empat", "lima", "enam", "tujuh", "lapan", "delapan", "sembilan")
_MS_ONES = ("satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "lapan", "delapan", "sembilan")
_EN_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_EN_ONES = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_ZH_TEENS = "一二三四五六七八九"
_ZH_TENS = "二三四五六七八九"


@dataclass(frozen=True)
class FallbackLine:
    """Deterministic extraction result for a single candidate span."""

    span: str
    family_id: str
    qty: Optional[int]
    uom: Optional[str]
    pack_size: Optional[str]
    grade: Optional[str]
    match_score: float
    is_decimal_qty: bool
    issue_reason: Optional[str] = None
    match_source: str = "RAPIDFUZZ_FALLBACK"


def split_into_candidate_spans(text: str) -> List[str]:
    """Split input text into candidate line spans using strong boundaries only."""
    if not text:
        return []

    coarse_chunks = _COARSE_SPLIT_PATTERN.split(text)
    spans: List[str] = []
    for chunk in coarse_chunks:
        sub_chunks = _INLINE_NUM_PATTERN.split(chunk)
        for sub in sub_chunks:
            cleaned = _LEADING_NUM_PATTERN.sub("", sub).strip()
            if cleaned:
                spans.append(cleaned)
    return spans


def _mask_with(pattern: Any, text: str) -> str:
    """Replace regex matches with equal-length space strings to preserve offsets."""
    if isinstance(pattern, re.Pattern):
        return pattern.sub(lambda m: " " * len(m.group(0)), text)
    return re.sub(pattern, lambda m: " " * len(m.group(0)), text, flags=re.IGNORECASE)


def _candidate_list(text: str, lexicon: Dict[str, Any]) -> List[Tuple[int, int, int]]:
    """Return (start, end, value) quantity candidates; longest match wins."""
    out: List[Tuple[int, int, int]] = []
    qrules = lexicon["quantity"]
    ms_units = qrules["ms_units"]
    en_values = qrules["en_values"]
    zh_values = qrules["zh_values"]

    # 1. Malay compound teens: "dua belas" -> 12
    for m in re.finditer(rf"\b({'|'.join(_MS_TEENS)})\s+belas\b", text):
        out.append((m.start(), m.end(), 10 + ms_units[m.group(1)]))

    # 2. Malay compound tens: "dua puluh", "tiga puluh lima" -> 35
    for m in re.finditer(
        rf"\b({'|'.join(_MS_TEENS)})\s+puluh(?:\s+({'|'.join(_MS_ONES)}))?\b", text
    ):
        value = ms_units[m.group(1)] * 10
        if m.group(2):
            value += ms_units[m.group(2)]
        out.append((m.start(), m.end(), value))

    # 3. English compound: "twenty-five", "thirty four" -> 34
    for m in re.finditer(
        rf"\b({'|'.join(_EN_TENS.keys())})(?:[-\s]({'|'.join(_EN_ONES)}))?\b", text
    ):
        value = _EN_TENS[m.group(1)]
        if m.group(2):
            value += en_values[m.group(2)]
        out.append((m.start(), m.end(), value))

    # 4. Chinese compound teens: "十一", "十五" -> 15
    for m in re.finditer(rf"十([{_ZH_TEENS}])", text):
        out.append((m.start(), m.end(), 10 + zh_values[m.group(1)]))

    # 5. Chinese compound tens: "二十", "三十五" -> 35
    for m in re.finditer(rf"([{_ZH_TENS}])十([{_ZH_TEENS}])?", text):
        value = zh_values[m.group(1)] * 10
        if m.group(2):
            value += zh_values[m.group(2)]
        out.append((m.start(), m.end(), value))

    # 6. Single words (Malay, English, Chinese)
    for word, value in ms_units.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", text):
            out.append((m.start(), m.end(), value))

    for word, value in en_values.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", text):
            out.append((m.start(), m.end(), value))

    for ch, value in zh_values.items():
        for m in re.finditer(re.escape(ch), text):
            out.append((m.start(), m.end(), value))

    # 7. Arabic digits
    for m in _ARABIC.finditer(text):
        out.append((m.start(), m.end(), int(m.group(1))))

    # Earliest occurrence first; at the same start, longest span first
    out.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    return out


def parse_quantity_h1(
    span: str,
    lexicon: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[int], Optional[str], Optional[int], Optional[int]]:
    """Deterministic quantity extraction complying strictly with H1 truth tables.

    Pipeline:
      1. Unit-price marker mask (e.g. "RM2.50 satu" -> "satu" masked)
      2. Currency amount mask (thousands comma + standard RM patterns)
      3. Code mask (e.g. "A95")
      4. Comma Decimal Guard (strict no-space comma + decimal_comma_unit_pattern) -> BEFORE pack_size
      5. Conditional pack_size spec mask (only if multiple candidates or explicit x/装)
      6. Dot Decimal Guard -> AFTER pack_size (preserves "1.5 kg x 2" -> 2)
      7. Candidate extraction & ambiguity check
    """
    if lexicon is None:
        lexicon = load_h1_lexicon()

    value = normalize_text(span)
    qrules = lexicon["quantity"]

    # 1. Unit-price markers removal (runtime relax separator to [.,] to cover "RM2,50 satu")
    raw_marker = qrules["unit_price_marker_pattern"]
    relaxed_marker = re.sub(r"\\\.\\d\{1,2\}", r"[.,]\\d{1,2}", raw_marker)
    masked = _mask_with(relaxed_marker, value)

    # 2. Currency amounts removal (thousands comma first, then comma decimal, then standard)
    masked = _mask_with(_AMOUNT_WITH_THOUSANDS, masked)
    masked = _mask_with(_AMOUNT_WITH_COMMA_DECIMAL, masked)
    masked = _mask_with(qrules["qty_exclude_pattern"], masked)

    # 3. SKU codes removal
    masked = _mask_with(qrules["code_exclude_pattern"], masked)

    # 4. Comma Decimal Guard BEFORE pack_size mask:
    # Blocks "1,5kg", "0,5 ctn" (strict no-space comma) and "1,5 kg" (decimal_comma_unit_pattern)
    # Does NOT block "12, 3" in "Air 500 g x 12, 3 pack" because of the space after comma!
    if _STRICT_COMMA_DECIMAL.search(masked) or re.search(
        qrules["decimal_comma_unit_pattern"], masked
    ):
        return None, "INVALID_QUANTITY", None, None

    # 5. Pack-size spec removal (when another candidate exists or explicit x/装)
    before = _candidate_list(masked, lexicon)
    if len({v for _, _, v in before}) > 1 or re.search(r"\d\s*x\s*\d|装", masked, re.IGNORECASE):
        for pattern in lexicon["pack_size"]["patterns"]:
            masked = _mask_with(pattern, masked)

    # 6. Dot Decimal Guard AFTER pack_size mask:
    # Preserves "1.5 kg x 2" (pack_size masked) while blocking isolated "2.5 ctn", "1.5kg"
    if re.search(qrules["decimal_guard_pattern"], masked):
        return None, "INVALID_QUANTITY", None, None

    # 7. Candidates extraction
    candidates = _candidate_list(masked, lexicon)
    if not candidates:
        return None, None, None, None

    # 8. Distinct non-overlapping check (Rule 7: Ambiguous quantity)
    distinct: List[Tuple[int, int, int]] = []
    cursor = -1
    for s, e, val in candidates:
        if s >= cursor:
            distinct.append((s, e, val))
            cursor = e

    if len({v for _, _, v in distinct}) > 1:
        return None, "AMBIGUOUS_QUANTITY", None, None

    start, end, qty = distinct[0]
    return qty, None, start, end


def _pack_match_starts_inside_decimal(value: str, start: int) -> bool:
    """Reject a pack match that begins inside a comma/dot decimal.

    The frozen H1 pack patterns use ``\\b`` before the digits. In
    ``1,5kg`` the comma is a non-word character, so ``\\b`` matches between
    the comma and ``5`` and the pattern returns a false ``5kg``.  A pack
    size may never start immediately after a decimal separator or digit.
    """
    return start > 0 and (value[start - 1] in ".," or value[start - 1].isdigit())


def parse_pack_size_h1_with_offsets(
    span: str,
    lexicon: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Extract pack size spec and normalized offsets from span.

    Returns:
        (pack_size, start, end) in normalize_text(span) coordinates.
    """
    if lexicon is None:
        lexicon = load_h1_lexicon()
    value = normalize_text(span)
    for pattern in lexicon["pack_size"]["patterns"]:
        m = re.search(pattern, value, re.IGNORECASE)
        if m:
            if _pack_match_starts_inside_decimal(value, m.start()):
                continue
            s, e = m.start(), m.end()
            matched_slice = value[s:e]
            suffix_m = re.search(r"\s*(?:装|pack|packs)$", matched_slice, flags=re.IGNORECASE)
            if suffix_m:
                e = s + suffix_m.start()
            while s < e and value[s].isspace():
                s += 1
            while e > s and value[e - 1].isspace():
                e -= 1
            pack_val = parse_pack_size_h1(span, lexicon=lexicon)
            return pack_val, s, e
    return None, None, None


def parse_pack_size_h1(span: str, lexicon: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Extract pack size spec from span (e.g. '500g', '5kg', '12 x 1L')."""
    if lexicon is None:
        lexicon = load_h1_lexicon()
    value = " ".join(span.split())
    for pattern in lexicon["pack_size"]["patterns"]:
        m = re.search(pattern, value, re.IGNORECASE)
        if m:
            if _pack_match_starts_inside_decimal(value, m.start()):
                continue
            text = m.group(0).strip()
            return re.sub(r"\s*(?:装|pack|packs)$", "", text, flags=re.IGNORECASE)
    return None


def parse_uom_h1_with_offsets(
    span: str,
    lexicon: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Extract canonical UOM and normalized offsets from span.

    Returns:
        (canonical_uom, start, end) in normalize_text(span) coordinates.
    """
    if lexicon is None:
        lexicon = load_h1_lexicon()
    value = normalize_text(span)
    aliases = lexicon["uom_aliases"]

    for canonical, values in aliases.items():
        for alias in values:
            a = normalize_text(alias)
            if a.isascii():
                m = re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", value)
                if m:
                    return canonical, m.start(), m.end()
            elif a in value:
                m = re.search(re.escape(a), value)
                if m:
                    return canonical, m.start(), m.end()

    for alias, canonical in lexicon.get("tenant_uom_extensions", {}).items():
        a = normalize_text(alias)
        if a.isascii():
            m = re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", value)
            if m:
                return canonical, m.start(), m.end()
        elif a in value:
            m = re.search(re.escape(a), value)
            if m:
                return canonical, m.start(), m.end()

    return None, None, None


def parse_uom_h1(span: str, lexicon: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Extract canonical UOM from span (ctn, pack, kg, pc, bag + tenant extensions)."""
    canonical, _, _ = parse_uom_h1_with_offsets(span, lexicon=lexicon)
    return canonical


def parse_grade_h1(span: str) -> Optional[str]:
    """Extract product grade (e.g. 'Grade A' -> 'A')."""
    grade_match = _GRADE_PATTERN.search(span)
    if grade_match:
        return grade_match.group(1).upper()
    return None


def _match_family_rapidfuzz(
    text: str,
    catalog: Dict[str, Sequence[str]],
    threshold: float = 65.0,
) -> Tuple[str, float]:
    """Match family ID using RapidFuzz token_set_ratio against catalog aliases."""
    normalized_input = normalize_text(text)
    best_fam = "UNKNOWN"
    best_score = 0.0

    for fam_id, phrases in catalog.items():
        for phrase in phrases:
            norm_phrase = normalize_text(phrase)
            score = fuzz.token_set_ratio(normalized_input, norm_phrase)
            if score > best_score:
                best_score = score
                if score >= threshold:
                    best_fam = fam_id

    return best_fam, float(best_score)


def extract_fallback_line(
    span: str,
    catalog: Optional[Dict[str, Sequence[str]]] = None,
    threshold: float = 65.0,
    lexicon: Optional[Dict[str, Any]] = None,
) -> FallbackLine:
    """Extract product line fields deterministically from a single candidate span."""
    if catalog is None:
        catalog = DEFAULT_SEED_CATALOG
    if lexicon is None:
        lexicon = load_h1_lexicon()

    # 1. Spec & Grade
    pack_size = parse_pack_size_h1(span, lexicon=lexicon)
    grade = parse_grade_h1(span)

    # 2. UOM
    uom = parse_uom_h1(span, lexicon=lexicon)

    # 3. Quantity with H1 length-preserving pipeline
    qty, reason, _, _ = parse_quantity_h1(span, lexicon=lexicon)
    is_decimal = reason == "INVALID_QUANTITY"

    # 4. RapidFuzz match
    family_id, score = _match_family_rapidfuzz(span, catalog, threshold=threshold)

    issue_reason: Optional[str] = None
    if reason:
        issue_reason = reason
    elif qty is None:
        issue_reason = "FIELD_NOT_EVIDENCED"
    elif family_id == "UNKNOWN":
        issue_reason = "FAMILY_NOT_EVIDENCED"

    return FallbackLine(
        span=span,
        family_id=family_id,
        qty=qty,
        uom=uom,
        pack_size=pack_size,
        grade=grade,
        match_score=score,
        is_decimal_qty=is_decimal,
        issue_reason=issue_reason,
        match_source="RAPIDFUZZ_FALLBACK",
    )


def extract_fallback_order(
    masked_message: str,
    catalog: Optional[Dict[str, Sequence[str]]] = None,
    lexicon: Optional[Dict[str, Any]] = None,
) -> List[FallbackLine]:
    """Execute complete deterministic offline fallback extraction for a whole message."""
    spans = split_into_candidate_spans(masked_message)
    lines: List[FallbackLine] = []
    for span in spans:
        line = extract_fallback_line(span, catalog=catalog, lexicon=lexicon)
        lines.append(line)
    return lines
