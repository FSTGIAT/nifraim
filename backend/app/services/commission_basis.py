"""Which column is the agent's commission EXCLUDING VAT — decided by measurement.

The נפרעים pipeline carries two commission columns per row, `commission_paid`
and `commission_before_fee`, and their meaning is NOT consistent across
insurers (QA 2026-09-09, item 6). Measured on live data:

    מור      18,394.45 / 18,394.45   identical — summing both would double
    מנורה         0.00 /  7,758.32   only one populated
    הכשרה    40,160.53 / 47,223.69   both populated, both real

and the parsers disagree about which name means what: Harel savings maps
`עמלה לפני מע"מ`→`commission_paid`, the exact opposite of Hachshara.

So a blanket COALESCE is wrong in three different directions. But the agent
needs ONE number, and the decision (2026-09-09) is **commission excluding VAT**
— VAT is remitted to מע"מ and is not agent income.

Rather than hardcode a per-insurer table that silently rots as portals change
their exports, this derives the answer from the rows themselves: if one column
is consistently ~1.17–1.18× the other across a company's rows, that IS a VAT
pair (Israeli VAT was 17% through 2024 and 18% from 2025), and the smaller
column is the ex-VAT figure. Hachshara measures at exactly 1.18 on every row.

When the ratio is not a VAT relationship the columns mean genuinely different
things, and this refuses to guess: it falls back to the canonical priority in
`comparison_service._get_commission` and reports `verified=False`, so a caller
can show the number while flagging that its VAT basis is unconfirmed.
"""

from statistics import median

# Israeli VAT: 17% to 2024-12-31, 18% from 2025-01-01. The window is deliberately
# tight — a ratio of 1.3 is not a rounding error, it is a different quantity.
_VAT_MIN, _VAT_MAX = 1.15, 1.205
# Below this the two columns are the same number (Mor copies one into the other).
_SAME_MAX = 1.02
# One or two rows can agree by coincidence; a basis decision should not.
_MIN_SAMPLES = 3


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def detect_vat_basis(records) -> dict:
    """Inspect one company's נפרעים rows → how to read its commission columns.

    Returns `{"field", "verified", "ratio", "samples", "reason"}` where `field`
    is the record key holding the EX-VAT commission.
    """
    ratios = []
    for r in records:
        paid = _f(r.get("commission_paid"))
        before = _f(r.get("commission_before_fee"))
        if paid > 0 and before > 0:
            ratios.append(paid / before)

    if len(ratios) < _MIN_SAMPLES:
        return {"field": "commission_paid", "verified": False, "ratio": None,
                "samples": len(ratios),
                "reason": "לא נמצאו מספיק שורות עם שתי העמודות מלאות"}

    ratio = median(ratios)
    if ratio <= _SAME_MAX:
        return {"field": "commission_paid", "verified": True, "ratio": ratio,
                "samples": len(ratios),
                "reason": "שתי העמודות זהות — אותו סכום"}
    if _VAT_MIN <= ratio <= _VAT_MAX:
        # paid = before × (1 + VAT) → `commission_before_fee` is the ex-VAT one.
        return {"field": "commission_before_fee", "verified": True, "ratio": ratio,
                "samples": len(ratios),
                "reason": f"יחס {ratio:.2f} = מע\"מ; העמודה ללא מע\"מ נבחרה"}
    inv = 1 / ratio
    if _VAT_MIN <= inv <= _VAT_MAX:
        # The parser mapped them the other way round (Harel savings does).
        return {"field": "commission_paid", "verified": True, "ratio": ratio,
                "samples": len(ratios),
                "reason": f"יחס הפוך {inv:.2f} = מע\"מ; העמודה ללא מע\"מ נבחרה"}
    return {"field": "commission_paid", "verified": False, "ratio": ratio,
            "samples": len(ratios),
            "reason": f"היחס {ratio:.2f} אינו מע\"מ — משמעות העמודות שונה"}


def ex_vat_commission(record, basis: dict) -> float:
    """One row's agent commission on the basis `detect_vat_basis` chose.

    Falls back to the other column when the chosen one is empty for this row —
    insurers leave either side blank per row (Menora populates only one), and
    dropping such a row would understate the company's total.
    """
    primary = _f(record.get(basis["field"]))
    if primary:
        return primary
    other = ("commission_before_fee" if basis["field"] == "commission_paid"
             else "commission_paid")
    return _f(record.get(other)) or _f(record.get("actual_amount"))
