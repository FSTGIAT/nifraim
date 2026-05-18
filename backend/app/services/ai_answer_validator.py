"""Post-answer numeric validator — checks that currency amounts in the AI's
reply actually appear in the source data we gave it.

Why: The QA bugs ("סך העמלות לתקופה: ₪37,352", "עלייה של ₪1,114,575")
were the AI making up specific-looking numbers because it lost track of
which company had real data vs. which it was guessing about. The view_context
upgrade in this PR makes facts explicit, but the validator is the seatbelt:
on every answer, extract every currency-looking number and cross-check
against the same context the AI was shown. Mismatches become a yellow
warning chip on the message — the user sees the AI's answer AND a list of
numbers we couldn't verify.

Advisory-only by default. Set AI_STRICT_VALIDATION=true env var to switch
to re-prompt mode (out of scope for v1).
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


# Matches: ₪1,234 · ₪ 1,234 · 1,234₪ · 1,234 NIS · ₪1,234.56
# Captures the numeric portion. Skips bare numbers (year-like, percentages).
_RE_CURRENCY = re.compile(
    r"(?:"
    r"₪\s*([\d,]+(?:\.\d+)?)"
    r"|"
    r"([\d,]+(?:\.\d+)?)\s*(?:₪|NIS|ש[״\"]?ח)"
    r")"
)

# Tolerance — answers are often rounded; ₪37,352 vs ₪37,350 should pass.
TOLERANCE = 5.0


@dataclass
class ValidationResult:
    warnings: list[str]
    flagged_values: list[float]

    def has_warnings(self) -> bool:
        return bool(self.warnings)


def _extract_currency_amounts(text: str) -> list[float]:
    """Return all currency amounts found in the AI's answer."""
    out: list[float] = []
    if not text:
        return out
    for m in _RE_CURRENCY.finditer(text):
        raw = m.group(1) or m.group(2)
        if not raw:
            continue
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        # Drop trivial / non-financial numbers (counts, percentages)
        if val < 100:
            continue
        out.append(val)
    return out


def _extract_numbers_from_context(text: str) -> list[float]:
    """Pull every currency-like number out of the source context we showed
    the AI — these are the "valid" answers."""
    out: list[float] = []
    if not text:
        return out
    for m in _RE_CURRENCY.finditer(text):
        raw = m.group(1) or m.group(2)
        if not raw:
            continue
        try:
            out.append(float(raw.replace(",", "")))
        except ValueError:
            pass
    # Also pick up plain numbers that show up after structural labels —
    # "Δפרמיה +1,234" / "צבירה 1,234,567" — even without an explicit ₪.
    for m in re.finditer(r"(?:פרמיה|צבירה|עמלה|פקדון)[^\d-]{0,12}([+-]?[\d,]+(?:\.\d+)?)", text):
        raw = m.group(1)
        try:
            val = abs(float(raw.replace(",", "").lstrip("+")))
            if val >= 100:
                out.append(val)
        except ValueError:
            pass
    return out


def validate_answer(answer_text: str, source_context: str) -> ValidationResult:
    """Compare every currency value in `answer_text` against `source_context`
    (the view_context + any other strings shown to the AI). Returns a
    ValidationResult with warnings for unverifiable amounts.

    `source_context` should be the concatenation of view_context plus any
    other facts blocks the AI was shown — passing the system prompt itself
    is unhelpful because it doesn't contain the user's numbers.
    """
    answer_amounts = _extract_currency_amounts(answer_text or "")
    if not answer_amounts:
        return ValidationResult(warnings=[], flagged_values=[])

    source_amounts = _extract_numbers_from_context(source_context or "")
    if not source_amounts:
        # No source numbers to validate against → cannot make a judgment.
        return ValidationResult(warnings=[], flagged_values=[])

    flagged: list[float] = []
    seen: set[float] = set()  # dedupe — same value mentioned twice = same warning
    for val in answer_amounts:
        if val in seen:
            continue
        seen.add(val)
        if not any(abs(val - sv) <= TOLERANCE for sv in source_amounts):
            flagged.append(val)

    warnings: list[str] = []
    for v in flagged:
        warnings.append(
            f"₪{int(v):,} לא נמצא במקור הנתונים — ייתכן שזה מספר משוער או שגוי"
        )
    if flagged:
        logger.warning(
            "ai_answer_validator.flagged count=%d values=%s",
            len(flagged), [f"{v:.0f}" for v in flagged],
        )
    return ValidationResult(warnings=warnings, flagged_values=flagged)
