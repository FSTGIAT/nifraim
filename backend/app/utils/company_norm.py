"""Company-name normalization shared across the comparison + AI layers.

The QA bug "אבלין פיפרברג שייכת רק לנפרעים" came from the fuzzy substring
match in `_matches_commission_company` (`"הראל" in "הראל חברה לביטוח בע״מ"`
works, but `"הראל גמל" in "הראל לביטוח"` does not). When the match silently
fails, the customer drops out of one bucket and lands in the wrong one.

This module gives ONE deterministic normalizer used by both the backend
classifier and the frontend switcher detector — so they always agree on
"is this the same company?".
"""
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


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


# ── Canonical LEGAL entity names ──────────────────────────────────────────
#
# `normalize_company` returns a comparable *collapse key* ("הפניקס", "הראל");
# for the merged production file we instead need the full LEGAL entity name
# the maslaka clearinghouse uses — and it distinguishes an insurer's savings
# entity from its insurance entity (הפניקס אקסלנס פנסיה וגמל בע"מ vs הפניקס
# חברה לביטוח בע"מ). So `canonical_company(name, kind)` maps a raw portal name
# to the right legal entity for the record's kind.
#
# Every value below is copied VERBATIM from the reference file
# `פרודוקציה אפריל.xlsx` (`יצרן` column) — not invented. Matching is by name
# stem so raw short-names (הפניקס, הפניקס גמל), variants (הראל גמל, הראל מגוון)
# and already-legal names all resolve; already-legal inputs are idempotent.
#
# (stems, savings-entity, insurance-entity). insurance is None for single-
# entity insurers (gemel/pension or insurance-only) → same name for both kinds.
#
# stems[0] is the PRIMARY short key returned by `company_stem`. The longer
# multi-word forms are the BRAND as the insurer writes it ("אלטשולר שחם",
# "מיטב דש", "מנורה מבטחים") and exist so `company_residue` doesn't mistake
# brand continuation for a product name — without "אלטשולר שחם" as a stem,
# 'אלטשולר שחם גמל ופנסיה בע"מ' yields the residue 'שחם גמל ופנסיה בעמ'.
# Matching is longest-stem-first (see `_stem_index`).
_LEGAL_ENTITIES: list[tuple[tuple[str, ...], str, str | None]] = [
    (("הפניקס", "פניקס", "הפניקס אקסלנס", "פניקס אקסלנס"),
                          'הפניקס אקסלנס פנסיה וגמל בע"מ', 'הפניקס חברה לביטוח בע"מ'),
    (("הראל",),           'הראל פנסיה וגמל בע"מ',          'הראל חברה לביטוח בע"מ'),
    (("מנורה", "מנורה מבטחים"),
                          'מנורה מבטחים פנסיה וגמל בע"מ',  'מנורה מבטחים ביטוח בע"מ'),
    (("מגדל", "מגדל מקפת"),
                          'מגדל מקפת קרנות פנסיה וקופות גמל בע"מ', 'מגדל חברה לביטוח בע"מ'),
    (("כלל",),            'כלל פנסיה וגמל בע"מ',           'כלל חברה לביטוח בע"מ'),
    (("אלטשולר", "אלטשולר שחם"), 'אלטשולר שחם גמל ופנסיה בע"מ',   None),
    (("מיטב", "מיטב דש"), 'מיטב גמל ופנסיה בע"מ',          None),
    (("מור",),            'מור גמל ופנסיה בע"מ',           None),
    (("ילין", "ילין לפידות"), 'ילין לפידות ניהול קופות גמל בע"מ', None),
    (("הכשרה",),          'הכשרה חברה לביטוח בע"מ',        None),
    (("אנליסט",),         'אנליסט קופות גמל בע"מ',         None),
]

# Every (stem, primary-key) pair, longest stem first, so "מיטב דש ניהול תיקים"
# resolves against "מיטב דש" rather than the shorter "מיטב".
_stem_index: list[tuple[str, str]] = sorted(
    ((stem, stems[0]) for stems, _sav, _ins in _LEGAL_ENTITIES for stem in stems),
    key=lambda pair: -len(pair[0]),
)


def _clean(name: str | None) -> str:
    """Quote/whitespace cleanup shared by the stem helpers and
    `canonical_company` — deliberately WITHOUT alias mapping or suffix
    stripping, both of which destroy the product residue."""
    if not name:
        return ""
    s = re.sub(r'[\'"`׳״|]', "", str(name)).strip()
    return re.sub(r"\s+", " ", s)


def _match_stem(name: str | None) -> tuple[str, str] | None:
    """(matched_stem, primary_key) for the longest brand stem that `name`
    starts with, or None when the insurer isn't in `_LEGAL_ENTITIES`."""
    s = _clean(name)
    if not s:
        return None
    for stem, primary in _stem_index:
        if s.startswith(stem):
            return stem, primary
    return None


def known_company_stem(name: str | None) -> str:
    """Brand key, but ONLY for insurers actually in `_LEGAL_ENTITIES` — '' for
    anything else.

    Unlike `company_stem`, this does NOT fall back to `normalize_company`, so
    it can be used to ASK "is this string a company at all?". Guessing a
    company out of free text needs that question answered: a product named
    'פרודוקציה - חיים' otherwise yields the company 'פרודוקציה'.
    """
    hit = _match_stem(name)
    return hit[1] if hit else ""


def company_stem(name: str | None) -> str:
    """The BRAND key for a company name, ignoring legal-entity and product
    wording: 'הראל', 'מנורה', 'מגדל', …

    This is the fallback tier for rate matching. `normalize_company` is a
    collapse key built from a suffix list, and it does NOT invert
    `canonical_company` — the merged automation file writes
    'מנורה מבטחים פנסיה וגמל בע"מ' (→ 'מנורה מבטחים') while the agreement shelf
    holds 'מנורה' (→ 'מנורה'), so canonical equality silently misses and the
    whole company contributes ₪0. Matching on the stem instead makes
    'הראל פנסיה וגמל בע"מ', 'הראל גמל' and 'הראל מגוון' all resolve to 'הראל'.

    Falls back to `normalize_company` for insurers not in `_LEGAL_ENTITIES`,
    so an unmapped company still gets a stable (if coarser) key.
    """
    hit = _match_stem(name)
    return hit[1] if hit else normalize_company(name)


def company_residue(name: str | None) -> str:
    """Whatever follows the brand stem — the PRODUCT information that legacy
    rate rows smuggled into the company column.

        'הראל מגוון'          → 'מגוון'
        'מגדל קשת'            → 'קשת'
        'מור ניהול תיקים'     → 'ניהול תיקים'
        'פניקס גמל והשתלמות'  → 'גמל והשתלמות'
        'מיטב דש'             → ''            (brand only, no product)

    Two rules here are load-bearing and were both established by measurement:

    1. The residue is taken from the RAW name, never from
       `normalize_company(name)`. `normalize_company` applies `_ALIASES`
       FIRST, so 'פניקס גמל והשתלמות' and 'פניקס פוליסות' both collapse to
       'הפניקס' and the residue — the only thing telling their 0.45% and
       0.34% rates apart — is destroyed.
    2. The residue is NOT suffix-stripped. 'פניקס גמל והשתלמות' is
       distinguished precisely by 'גמל והשתלמות', which is itself in
       `_SUFFIX_TOKENS`; stripping it would re-lose the pair.

    Returns '' when the insurer isn't in `_LEGAL_ENTITIES` (no stem to
    subtract) or when the name is exactly the brand.
    """
    hit = _match_stem(name)
    if not hit:
        return ""
    stem, _primary = hit
    return _clean(name)[len(stem):].strip()


# Corporate-FORM wording — says what kind of legal entity this is, never what
# it sells. Distinct from `_SUFFIX_TOKENS`, which also holds business-line words
# (גמל, השתלמות, פנסיה, ביטוח) that legitimately name a product line.
_CORPORATE_TOKENS = (
    'בע"מ', "בע''מ", "בע״מ", "בעמ", "חברה לביטוח", "חברה ל ביטוח",
    "ל ביטוח", "חברה",
)


def product_residue(name: str | None) -> str:
    """The residue ONLY when it genuinely names a product — else ''.

    Stricter than `company_residue`, and used by the one-off migration that
    rewrites legacy rows: moving a residue into the `product` column is
    destructive, so it must not fire on wording that is merely the legal
    entity. `'הראל חברה לביטוח בע"מ'` has the residue 'חברה לביטוח בעמ', and
    writing that as a product turned a legitimate company-DEFAULT row into a
    product-specific row for a product that doesn't exist.

        'הראל מגוון'            → 'מגוון'          (a product — move it)
        'הראל נסיעות וגמל בע"מ' → 'נסיעות וגמל'    (a product — corporate wording trimmed)
        'הראל חברה לביטוח בע"מ' → ''               (just the entity — leave alone)
        'הראל פנסיה וגמל בע"מ'  → ''               (business lines only, not a product)
        'פניקס גמל והשתלמות'    → ''               (see below)

    The last case is deliberate. 'גמל והשתלמות' IS the distinguishing detail
    for that row, but every word in it is a business-line suffix, so this
    function can't tell it apart from an entity descriptor. The migration
    therefore leaves it — and `select_rate`'s runtime residue rule, which does
    NOT suffix-strip, still separates פניקס-גמל from פניקס-פוליסות. Being
    conservative here costs nothing because that fallback exists.
    """
    residue = company_residue(name)
    if not residue:
        return ""
    s = residue
    for tok in _CORPORATE_TOKENS:
        s = s.replace(tok, " ")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""
    # Every remaining word is a generic business-line suffix → not a product.
    if all(
        any(w == suf or w in suf for suf in _SUFFIX_TOKENS)
        for w in s.split()
    ):
        return ""
    return s


def canonical_company(name: str | None, kind: str = "insurance") -> str:
    """Map a raw portal company name → the full LEGAL entity name used by the
    reference production file, picking the savings- or insurance-entity by
    `kind` ("savings" | "insurance").

    Unmapped names are returned unchanged (never blanked) and logged once, so
    a new insurer degrades gracefully instead of vanishing from the merge.
    Idempotent: passing an already-legal name returns it unchanged.
    """
    if not name:
        return ""
    s = re.sub(r'[\'"`׳״|]', "", str(name)).strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return ""
    for stems, savings, insurance in _LEGAL_ENTITIES:
        if any(s.startswith(stem) for stem in stems):
            if kind == "insurance" and insurance:
                return insurance
            return savings
    logger.warning("canonical_company: unmapped insurer name %r (kind=%s)", name, kind)
    return str(name).strip()
