"""Deterministic PII masking for order messages.

Only the three Gate 0 tokens may leave this module. Raw PII must never be
logged, persisted, or sent to an extraction provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

MaskKind = Literal["PHONE", "MYKAD", "EMAIL"]

TOKEN_BY_KIND: dict[MaskKind, str] = {
    "PHONE": "[REDACTED_PHONE]",
    "MYKAD": "[REDACTED_MYKAD]",
    "EMAIL": "[REDACTED_EMAIL]",
}

_PII_RE = re.compile(
    r"(?P<PHONE>(?<!\d)(?:\+?60|0)1[0-9](?:[-\s]?\d){7,8}(?!\d))"
    r"|(?P<MYKAD>(?<!\d)\d{6}[-\s]?\d{2}[-\s]?\d{4}(?!\d))"
    r"|(?P<EMAIL>[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"
)


@dataclass(frozen=True)
class MaskToken:
    kind: MaskKind
    token: str
    start: int
    end: int


@dataclass(frozen=True)
class MaskedMessage:
    masked_text: str
    tokens: tuple[MaskToken, ...]


def mask_message(message_text: str) -> MaskedMessage:
    tokens: list[MaskToken] = []

    def replace(match: re.Match[str]) -> str:
        kind = match.lastgroup
        if kind not in TOKEN_BY_KIND:
            raise AssertionError("PII regex produced an unknown group")
        token = TOKEN_BY_KIND[kind]
        tokens.append(MaskToken(kind=kind, token=token, start=match.start(), end=match.end()))
        return token

    masked = _PII_RE.sub(replace, message_text)
    return MaskedMessage(masked_text=masked, tokens=tuple(tokens))
