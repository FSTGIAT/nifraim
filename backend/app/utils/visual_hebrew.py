"""Recover logical Hebrew from CP862 visual-order fields.

Several Israeli insurers still ship DOS-era fixed-width exports whose Hebrew is
stored *visually* — the writer reversed each field so a left-to-right terminal
would paint it correctly. Reading them back means undoing that.

Shared by `hachshara_prod` (SP/SB/RM records), `phoenix_mu` (the Phoenix
terminal MU book) and available to `menora_legacy`. It lived privately inside
`hachshara_prod` while the other two open-coded a naive `[::-1]`, which is the
bug this module exists to stop repeating.
"""
from __future__ import annotations

import re

# A run of digits and the punctuation that binds them (dates, policy numbers,
# amounts). These were written in reading order INSIDE an otherwise reversed
# field, so they have to be flipped back before the whole-string reverse.
_LTR_RUN = re.compile(r"[0-9][0-9./\-:,]*")


def reverse_visual_hebrew(s: str) -> str:
    """Visual-order CP862 field → logical Hebrew.

    The legacy writer reversed the whole string for DOS display, then put each
    numeric run back in reading order. So the inverse is: re-reverse the numeric
    runs, then reverse the whole string.

        visual  '02/16 טרפ טסב'  ->  logical  'בסט פרט 02/16'

    A naive whole-field ``[::-1]`` is fine for a pure-Hebrew name field but
    renders that date as '61/20' — which is exactly how a real הכשרה product
    name got corrupted. Always use this, even when today's field happens to
    hold no digits.
    """
    s = (s or "").strip()
    if not s:
        return ""
    protected = _LTR_RUN.sub(lambda m: m.group(0)[::-1], s)
    return protected[::-1].strip()
