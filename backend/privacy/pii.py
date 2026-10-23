"""PII (Personally Identifiable Information) masking engine for KiraOrder.

Complies strictly with Gate 0 contract:
- Lexicon: pii-mask-tokens-v1.json
- Standard tokens: [REDACTED_PHONE], [REDACTED_MYKAD], [REDACTED_EMAIL]
- Lifetime: REQUEST_SCOPE_ONLY (applied before persistence, logging, and AI calls)
"""

from dataclasses import dataclass
import re
from typing import Final, Tuple

# Gate 0 Canonical Mask Tokens
TOKEN_PHONE: Final[str] = "[REDACTED_PHONE]"
TOKEN_MYKAD: Final[str] = "[REDACTED_MYKAD]"
TOKEN_EMAIL: Final[str] = "[REDACTED_EMAIL]"

MASK_TOKENS: Final[Tuple[str, ...]] = (TOKEN_PHONE, TOKEN_MYKAD, TOKEN_EMAIL)

# Regex Patterns
# 1. Email Pattern: standard RFC 5322 compliant snippet
_EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])",
    re.IGNORECASE,
)

# 2. Malaysian MyKad Pattern: 12 digits (YYMMDD-PB-###G or YYMMDD PB ###G or YYMMDD######)
# Must not be preceded or followed by digits or word chars
_MYKAD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)\d{6}[ -]?\d{2}[ -]?\d{4}(?!\d)"
)

# 3. Malaysian Phone Numbers:
# Covers:
# - +60 1x-xxx xxxx, +601xxxxxxxx
# - 601x-xxx xxxx, 601xxxxxxxx
# - 01x-xxx xxxx, 01xxxxxxxxx (mobile 10-11 digits)
# - Landlines: 03-xxxx xxxx, 0[4-9]-xxx xxxx, +60 3-xxxx xxxx
_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<!\w)(?:"
    r"(?:\+?60[ -]?1[0-9][ -]?\d{3,4}[ -]?\d{4})|"       # +601x mobile
    r"(?:01[0-9][ -]?\d{3,4}[ -]?\d{4})|"                # 01x local mobile
    r"(?:\+?60[ -]?[3-9][ -]?\d{3,4}[ -]?\d{4})|"        # +60 landline
    r"(?:0[3-9][ -]?\d{3,4}[ -]?\d{4})"                  # 0x local landline
    r")(?!\w)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PiiMaskResult:
    """Immutable result of PII masking on a raw message."""

    masked_text: str
    phone_count: int
    mykad_count: int
    email_count: int
    total_redacted: int

    @property
    def has_pii(self) -> bool:
        """Return True if any PII entity was masked."""
        return self.total_redacted > 0


def mask_pii(text: str) -> PiiMaskResult:
    """Mask sensitive PII in raw text using canonical Gate 0 tokens.

    Order of masking:
    1. Email addresses (to avoid digits inside emails triggering phone/MyKad)
    2. MyKad identity numbers (12 digits, to avoid partial phone matching)
    3. Malaysian Phone numbers

    Args:
        text: Raw input text from customer or channel.

    Returns:
        PiiMaskResult containing the masked text and counts of redacted tokens.
    """
    if not text:
        return PiiMaskResult(
            masked_text="",
            phone_count=0,
            mykad_count=0,
            email_count=0,
            total_redacted=0,
        )

    # 1. Mask Email
    masked_text, email_count = _EMAIL_PATTERN.subn(TOKEN_EMAIL, text)

    # 2. Mask MyKad
    masked_text, mykad_count = _MYKAD_PATTERN.subn(TOKEN_MYKAD, masked_text)

    # 3. Mask Phone
    masked_text, phone_count = _PHONE_PATTERN.subn(TOKEN_PHONE, masked_text)

    total_redacted = email_count + mykad_count + phone_count

    return PiiMaskResult(
        masked_text=masked_text,
        phone_count=phone_count,
        mykad_count=mykad_count,
        email_count=email_count,
        total_redacted=total_redacted,
    )
