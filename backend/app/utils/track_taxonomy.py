"""Investment-track (אפיק / מסלול השקעה) names → one shared vocabulary.

The clearinghouse "מסלולי השקעה" sheet names every track the way its fund
house does: 142 distinct strings in one agent's book for ~12 real tracks —
'הפניקס גמל מחקה מדד S&P500', 'אלפא מור תגמולים - עוקב מדד S&P 500',
'1830 אלטשולר שחם חיסכון פלוס עוקב מדד S&P 500', 'עוקב מדד 005 P&S' … A chart
"לפי אפיק" needs the TRACK, not the brand's spelling of it.

Some houses send visual-order (reversed) digits: 'לבני 05 ומטה' is 50,
'005 P&S' is S&P 500. Those are folded back before matching.

Order matters: 'עוקב מדדי מניות' is an index tracker, not an equity track;
'אשראי ואג"ח עם מניות' is a bond track. Unknown names fall to "אחר" rather than
being guessed.
"""
from __future__ import annotations

import re

SP500 = "עוקב מדד S&P 500"
INDEX = "עוקב מדדים"
EQUITY = "מניות"
AGE_50 = "לבני 50 ומטה"
AGE_50_60 = "לבני 50 עד 60"
AGE_60 = "לבני 60 ומעלה"
AGE_OTHER = "תלוי גיל"
BONDS = 'אשראי ואג"ח'
CASH = "כספי (שקלי)"
MIXED = "משולב סחיר"
GENERAL = "כללי"
PROFIT = "משתתף ברווחים"
NONE = "ללא מסלול"
OTHER = "אחר"

# Reversed digit runs some exports carry (visual Hebrew order).
_REVERSED = {"05": "50", "06": "60", "005": "500"}


def _unreverse(s: str) -> str:
    return re.sub(r"(?<!\d)(005|05|06)(?!\d)", lambda m: _REVERSED[m.group(1)], s)


def canonical_track(name: str | None) -> str:
    s = _unreverse(str(name or "").strip())
    if not s or s in ("0", "nan", "None"):
        return NONE
    low = s.lower().replace('"', "").replace("״", "")

    if "s&p" in low or "p&s" in low or re.search(r"\bsp\s*500\b", low) or \
            ("500" in low and "עוקב" in low):
        return SP500
    if "עוקב מדד" in low or "מחקה מדד" in low or "עוקב מדדים" in low:
        return INDEX
    if "אשראי" in low or "אגח" in low or "אג ח" in low:
        return BONDS
    if "כספי" in low or "שקלי" in low:
        return CASH
    if "משולב סחיר" in low:
        return MIXED
    if "מניות" in low:
        return EQUITY
    # Age-dependent tracks (תלוי גיל). "50 עד 60" before the single bounds.
    if re.search(r"50\s*(עד|-|–)\s*60|60\s*(-|–)\s*50", low):
        return AGE_50_60
    if re.search(r"50\s*ומטה|עד גיל 50|גילאי 50 ומטה", low) or \
            ("לבני" in low and "50" in low and "ומטה" in low):  # word-reversed exports
        return AGE_50
    if re.search(r"60\s*ומעלה|מעל גיל 60|גילאי 60", low):
        return AGE_60
    if "מותאם" in low or "תלוי גיל" in low:
        return AGE_OTHER
    if "כללי" in low:
        return GENERAL
    # Old profit-sharing insurance funds (קרן י / קרן ט / קרן השקעה ו').
    if re.search(r"קרן\s*(י|ט|השקעה)", low) or "משתתף ברווחים" in low:
        return PROFIT
    return OTHER
