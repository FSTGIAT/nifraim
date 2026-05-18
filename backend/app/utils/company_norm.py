"""Company-name normalization shared across the comparison + AI layers.

The QA bug "אבלין פיפרברג שייכת רק לנפרעים" came from the fuzzy substring
match in `_matches_commission_company` (`"הראל" in "הראל חברה לביטוח בע״מ"`
works, but `"הראל גמל" in "הראל לביטוח"` does not). When the match silently
fails, the customer drops out of one bucket and lands in the wrong one.

This module gives ONE deterministic normalizer used by both the backend
classifier and the frontend switcher detector — so they always agree on
"is this the same company?".
"""
import re
import unicodedata


# Israeli insurance-company name suffixes we strip before comparison.
_SUFFIX_TOKENS = (
    "בע\"מ", "בע''מ", "בע״מ", "בעמ", 'בע"מ',
    "חברה לביטוח", "חברה ל ביטוח",
    "ביטוח", "פנסיה", "גמל והשתלמות", "גמל", "השתלמות",
    "ופנסיה", "וגמל", "חיים ובריאות", "חיים",
    "ל ביטוח", "ביטוחים", "פנסיה וגמל",
)

# Aliases — different surface forms that must collapse to the same key.
# Order matters: longer keys are checked first so "הפניקס אקסלנס" matches
# before just "אקסלנס". We do NOT strip the leading "ה" globally — for
# Israeli companies (הראל, הפניקס, הכשרה) it's part of the proper noun.
_ALIASES = [
    ("הפניקס אקסלנס", "הפניקס"),
    ("פניקס אקסלנס", "הפניקס"),
    ("הפניקס", "הפניקס"),
    ("פניקס", "הפניקס"),
]


def normalize_company(name: str | None) -> str:
    """Return a canonical comparable key for an insurance/saving company.

    Examples (after normalization, all collapse together):
        "הראל"                              → "הראל"
        "הראל חברה לביטוח בע״מ"             → "הראל"
        "הראל גמל"                          → "הראל"
        "אלטשולר שחם גמל ופנסיה בע\"מ"      → "אלטשולר שחם"
        "הפניקס אקסלנס פנסיה וגמל בע\"מ"    → "הפניקס"
    """
    if not name:
        return ""
    s = str(name).strip()
    if not s:
        return ""
    # Unicode normalize so visually identical chars (Hebrew final/non-final
    # nun, etc.) compare equal — but keep Hebrew, just NFKC.
    s = unicodedata.normalize("NFKC", s)
    # Drop curly quotes / vertical-bar separators
    s = re.sub(r'[\'"`׳״|]', "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Apply alias map BEFORE suffix stripping (alias keys assume raw names).
    # Longer keys are checked first — see _ALIASES ordering note.
    for k, v in _ALIASES:
        if s.startswith(k) or s == k:
            return v
    # Repeatedly strip recognised trailing suffixes until none match. This
    # collapses "הראל חברה לביטוח בע״מ" → "הראל" in one pass.
    lower = s
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIX_TOKENS:
            if lower.endswith(" " + suf):
                lower = lower[: -(len(suf) + 1)].rstrip()
                changed = True
                break
            if lower == suf:
                lower = ""
                changed = True
                break
    return lower.strip()


def same_company(a: str | None, b: str | None) -> bool:
    """True when two company names normalise to the same canonical key.
    Empty strings never match."""
    na, nb = normalize_company(a), normalize_company(b)
    return bool(na) and na == nb
