"""One product taxonomy: raw insurer wording → (category, canonical type).

QA 2026-09-09 items 9 and 11 ask for the book split into **ביטוח** vs
**פיננסים**, with a per-product breakdown inside each. Neither is possible off
the raw columns, because `product_type` is not a taxonomy — it is whatever each
portal happened to write:

    ר.ת.-מורחב בריאות ביטוחים   915   ← Harel: the REPORT's filename
    חיים                        261   ← Phoenix
    ביטוח בריאות                212   ← Migdal
    ביטוח חיים                  147   ← Menora
    ר.ת.-מורחב חיים ביטוחים      89   ← Harel again
    ר.ת.-מורחב חיים פוליסות      64   ← …and again

Those last four are all "חיים" (561 rows), split across four spellings, so a
GROUP BY product_type reports one product as four and the ביטוח/פיננסים split
cannot be drawn at all.

Two deliberate limits:

  * **Category is delegated**, never re-derived. `aggregate.classify_record` is
    the existing decision and carries two documented live incidents in its
    comments (Phoenix MU rows filed under the pension entity; 14 Harel gemel
    rows filed as insurance). A fifth independent classifier is exactly the
    problem this module exists to end.
  * **Unrecognised wording is preserved, never bucketed as "אחר".** Hachshara's
    `בסט` fund family and `פיננסים וזמן פרישה` are real products this app has
    no opinion about; collapsing them into a catch-all would hide them from the
    very breakdown the agent asked for.

A life policy that CARRIES ACCUMULATION is פיננסים, not ביטוח (user decision,
2026-09-09). Live this is 324 rows holding ₪54,536,228 — Phoenix MU and Harel
מגוון policies — so the whole פיננסים side currently reads `חיים`. That looks
wrong to anyone expecting גמל/השתלמות/פנסיה there, and it is deliberate: those
policies hold savings, and moving them to ביטוח would put ₪54.5M of balance on
a panel measured in monthly premium. Do not "fix" it.
"""

import re

# Report-name scaffolding Harel wraps around the real product. Stripped first
# so `ר.ת.-מורחב חיים פוליסות` can reach the same key as Phoenix's bare `חיים`.
_REPORT_PREFIXES = ("ר.ת.-מורחב", "ר.ת.-מורחב", "ר.ת.")
_REPORT_SUFFIXES = ("ביטוחים", "פוליסות")

# Canonical types, matched by substring on the cleaned string. ORDER MATTERS:
# the first hit wins, so a more specific type must precede the token it
# contains — `גמל להשקעה` before `גמל`, `ביטוח מנהלים` before `מנהלים`.
_CANONICAL: tuple[tuple[str, tuple[str, ...]], ...] = (
    # ── financial ────────────────────────────────────────────────────────
    ("גמל להשקעה",   ("גמל להשקעה", "גמל להשקע")),
    ("קרן השתלמות",  ("השתלמות",)),
    ("קרן פנסיה",    ("פנסיה",)),
    ("קופת גמל",     ("גמל", "תגמולים", "קופ\"ג", "קופג")),
    ("פוליסת חיסכון", ("פוליסת חיסכון", "חיסכון פיננסי", "חסכון פיננסי")),
    ("ביטוח מנהלים", ("ביטוח מנהלים", "מנהלים")),
    ("מגוון",        ("מגוון",)),
    # ── insurance ────────────────────────────────────────────────────────
    ("בריאות",       ("בריאות",)),
    ("סיעודי",       ("סיעוד",)),
    ("משכנתא",       ("משכנתא", "משכנתה")),
    ("תאונות אישיות", ("תאונ",)),
    ("אובדן כושר עבודה", ("אכ\"ע", "אובדן כושר")),
    ("ריסק",         ("ריסק", "ריזיקו")),
    ("חיים",         ("חיים",)),
)


def canonical_product_type(raw: str | None) -> str:
    """Collapse one insurer's product wording onto a shared key.

    Returns the raw (whitespace-normalised) string when nothing matches — an
    unknown product must stay visible and countable, not vanish into "אחר".

        'ר.ת.-מורחב חיים פוליסות' → 'חיים'
        'ביטוח חיים'              → 'חיים'
        'חיים'                    → 'חיים'
        'מור השתלמות'             → 'קרן השתלמות'
        'בסט'                     → 'בסט'      (unknown, preserved)
    """
    if not raw:
        return ""
    s = re.sub(r"\s+", " ", str(raw).replace("‏", "").replace("‎", "")).strip()
    if not s:
        return ""

    stripped = s
    for pref in _REPORT_PREFIXES:
        if stripped.startswith(pref):
            stripped = stripped[len(pref):].strip(" -")
            break
    for suf in _REPORT_SUFFIXES:
        if stripped.endswith(suf):
            stripped = stripped[: -len(suf)].strip()
            break
    # `ביטוח X` and `X` are the same product to the agent, but only when a
    # canonical token follows — `ביטוח מנהלים` must NOT become `מנהלים` before
    # the table below has had its say, so this runs as a match candidate only.
    candidates = [stripped, s]
    if stripped.startswith("ביטוח "):
        candidates.insert(1, stripped[len("ביטוח "):].strip())

    for canon, tokens in _CANONICAL:
        for cand in candidates:
            if any(tok in cand for tok in tokens):
                return canon
    return stripped or s


def classify_product(record: dict) -> tuple[str, str]:
    """`(category, canonical_type)` where category is 'insurance' | 'financial'.

    The category comes from `aggregate.classify_record` — the single existing
    decision, which already reconciles product wording against the row's
    amounts. Imported lazily: `aggregate` pulls in the rate helpers, and this
    module is imported by API layers that must stay cheap.
    """
    from app.services.portal_automation.aggregate import classify_record

    category = "financial" if classify_record(record) == "savings" else "insurance"
    raw = record.get("product_type") or record.get("fund_type") or record.get("product")
    return category, canonical_product_type(raw)
