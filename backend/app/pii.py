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
    raw_length: int
    # One entry per masked character, mapped to the original raw index.
    # Every character of a replacement token maps to the token's raw start.
    index_map: tuple[int, ...]

    def original_index(self, masked_index: int) -> int:
        if masked_index < 0 or masked_index > len(self.index_map):
            raise IndexError("masked index out of range")
        if masked_index == len(self.index_map):
            return self.raw_length
        return self.index_map[masked_index]


def mask_message(message_text: str) -> MaskedMessage:
    tokens: list[MaskToken] = []
    pieces: list[str] = []
    index_map: list[int] = []
    cursor = 0

    for match in _PII_RE.finditer(message_text):
        for raw_index in range(cursor, match.start()):
            pieces.append(message_text[raw_index])
            index_map.append(raw_index)

        kind = match.lastgroup
        if kind not in TOKEN_BY_KIND:
            raise AssertionError("PII regex produced an unknown group")
        token = TOKEN_BY_KIND[kind]
        pieces.append(token)
        index_map.extend([match.start()] * len(token))
        tokens.append(
            MaskToken(
                kind=kind,
                token=token,
                start=match.start(),
                end=match.end(),
            )
        )
        cursor = match.end()

    for raw_index in range(cursor, len(message_text)):
        pieces.append(message_text[raw_index])
        index_map.append(raw_index)

    return MaskedMessage(
        masked_text="".join(pieces),
        tokens=tuple(tokens),
        raw_length=len(message_text),
        index_map=tuple(index_map),
    )
