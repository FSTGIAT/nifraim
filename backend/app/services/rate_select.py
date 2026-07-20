"""Category-aware commission-rate selection for the EXPECTED-commission math.

Background — the bug this prevents
----------------------------------
Agreement rate tables mix two very different things:
  • monthly נפרעים rates  — gemel 0.2–0.6%/yr, insurance ~3–15%
  • one-time scope/heqef (ריסק) rates — 28–60%

The generic product matcher's last-resort fallback ("any company rate") could
return a 60% ריסק rate and the caller would apply it to gemel ACCUMULATION,
inflating expected commission 2–3×. Production also lumps insurance into broad
categories ("הראל - חיים") that never match itemized agreement rows, so the
matcher fell through to that same 60% fallback.

These helpers make selection category-aware:
  • gemel  → the company's gemel-magnitude rate (≤ GEMEL_RATE_CEILING), median.
  • insurance → product match; if it returns a scope rate (> ceiling) or nothing,
    fall back to matching the broad category KEYWORD against the company's
    itemized rows; reject anything above the insurance ceiling.

Shared by api/insights.py (monthly view) and api/production.py (dashboard +
trend) so all expected-commission numbers agree.
"""
from __future__ import annotations

from typing import Callable

from app.utils.company_norm import normalize_company

# Ceilings separating monthly נפרעים rates from one-time scope/heqef rates.
GEMEL_RATE_CEILING = 0.03      # 3%/yr — real gemel נפרעים rates are 0.2–0.6%
INSURANCE_RATE_CEILING = 0.20  # 20% — excludes 28–60% scope/ריסק rates

# Broad insurance categories used in production data (product / product_type).
_INS_CATEGORY_KEYS = ("בריאות", "חיים", "משכנתא", "סיעודי", "מנהלים", "ריסק", "תאונ")


# Product-type tokens that decide the commission basis. Checked in this order:
# the accumulation family wins over the pure-risk family so that "ביטוח מנהלים"
# and "מנהלים חיסכון טהור" — which contain the pure-risk token חיים/מנהלים but
# are savings vehicles — are not misread as pure risk.
_ACCUM_TOKENS = ("חיסכון", "מנהלים", "גמל", "השתלמות", "תגמולים", "קופ")
_PURE_RISK_TOKENS = ("בריאות", "סיעודי", "משכנתא", "חיים", "ריסק", "תאונ")


def pure_risk_insurance(product_type: str | None) -> bool:
    """True for pure-risk insurance product types (בריאות/חיים/סיעודי/משכנתא).

    These are premium-based even when the record happens to carry an
    accumulation value, and they belong on the insurance sheet under the
    insurer's INSURANCE legal entity — never the pension/gemel one.
    """
    if not product_type:
        return False
    if "פנסיה" in product_type:
        return False
    if any(tok in product_type for tok in _ACCUM_TOKENS):
        return False
    return any(tok in product_type for tok in _PURE_RISK_TOKENS)


# Accumulation-bearing products that are nevertheless issued by the insurer's
# INSURANCE entity, not its pension/gemel one. They belong on the savings sheet
# (they carry צבירה) but must keep the insurance legal name.
#
# Verified against the reference portfolio (פרודוקציה יוני משורנס.xlsx, sheet
# מוצרי חיסכון): every one of these rows carries יצרן = "הראל חברה לביטוח בע\"מ" /
# "הפניקס חברה לביטוח בע\"מ" / "מגדל חברה לביטוח בע\"מ" / "כלל חברה לביטוח בע\"מ" /
# "מנורה מבטחים ביטוח בע\"מ" — never the פנסיה וגמל entity.
_INSURER_ISSUED_SAVINGS = ("מנהלים", "פוליסת חיסכון", "חיסכון פיננסי", "מגוון")


def entity_kind(product_type: str | None, sheet: str) -> str:
    """Which LEGAL ENTITY issues this product — 'insurance' or 'savings'.

    Deliberately separate from the sheet. Sheet answers "does this row carry
    accumulation"; entity answers "which company signed it", and for the
    מנהלים / פוליסת-חיסכון family those answers differ. Coupling them (savings
    sheet ⇒ savings entity) filed ביטוח מנהלים under 'הראל פנסיה וגמל בע"מ'
    when the portfolio says 'הראל חברה לביטוח בע"מ' — the same class of
    mis-entity this day's work set out to remove, reintroduced one layer down.
    """
    if product_type and any(t in product_type for t in _INSURER_ISSUED_SAVINGS):
        return "insurance"
    return sheet


def savings_product_type(product_type: str | None) -> bool:
    """True for product types that are savings/pension vehicles by NAME —
    גמל / השתלמות / תגמולים / חיסכון / מנהלים / קרן פנסיה.

    Deliberately independent of any amount: a גמל row whose accumulation column
    came through empty is still a גמל row. Use for SHEET/ENTITY routing only,
    never for the commission basis — `accumulation_based` correctly needs a
    positive accumulation there, since a zero-accumulation gemel row must
    contribute 0 expected commission rather than a rate against nothing.
    """
    if not product_type:
        return False
    if "פנסיה" in product_type:
        return True
    return any(tok in product_type for tok in _ACCUM_TOKENS)


def accumulation_based(product_type: str | None, accum: float) -> bool:
    """Whether a production record's EXPECTED commission is accumulation-based
    (accum × rate / 12) vs premium-based (premium × rate).

    Accumulation-based: gemel, השתלמות, גמל להשקעה, פוליסת חיסכון, מנהלים-חיסכון.
    NOT accumulation-based:
      • pension (קרן פנסיה) — נפרעים commission is on the monthly deposit, not
        the accumulated balance; production carries no pension premium, so it
        correctly contributes 0 rather than an inflated accum × rate.
      • pure-risk insurance (בריאות/חיים/סיעודי/משכנתא) — premium-based.

    The pure-risk exclusion is load-bearing and was missing for a long time:
    only `פנסיה` was excluded, so ANY insurance row carrying an accumulation
    value (Phoenix's MU life book stores one and deliberately leaves premium
    None) was billed as gemel — `accum × rate / 12` against a gemel rate — and,
    via `aggregate.classify_record`, was filed on the savings sheet under the
    insurer's PENSION legal entity. Live 2026-07-14: all 259 Phoenix MU rows
    landed under 'הפניקס אקסלנס פנסיה וגמל בע"מ' although 49% of those clients
    are הפניקס חברה לביטוח בריאות/סיעודי/חיים policies in the real portfolio.
    """
    if accum <= 0:
        return False
    if product_type and "פנסיה" in product_type:
        return False
    if pure_risk_insurance(product_type):
        return False
    return True


def gemel_rate_for(user_rates, company: str) -> float:
    """Company-level gemel נפרעים rate (median of sub-ceiling rates).

    Gemel agreements carry one small rate per company; selecting directly from
    the company's sub-ceiling rates avoids the product matcher returning a 60%
    ריסק rate for an unmatched gemel product."""
    canon = normalize_company(company)
    if not canon:
        return 0.0
    vals = sorted(
        float(r.rate) for r in user_rates
        if r.company_name and normalize_company(r.company_name) == canon
        and r.rate is not None and 0 < float(r.rate) <= GEMEL_RATE_CEILING
    )
    return vals[len(vals) // 2] if vals else 0.0


def insurance_rate_for(user_rates, company: str, product: str | None,
                       product_type: str | None) -> float:
    """Broad-category insurance rate: match the category keyword against the
    company's itemized rate rows, median of sub-ceiling rates. Used when the
    direct product match fails or returns a scope rate."""
    canon = normalize_company(company)
    if not canon:
        return 0.0
    text = f"{product or ''} {product_type or ''}"
    keys = [k for k in _INS_CATEGORY_KEYS if k in text]
    if not keys:
        return 0.0
    vals = sorted(
        float(r.rate) for r in user_rates
        if r.company_name and normalize_company(r.company_name) == canon
        and r.product and r.rate is not None
        and 0 < float(r.rate) <= INSURANCE_RATE_CEILING
        and any(k in r.product for k in keys)
    )
    return vals[len(vals) // 2] if vals else 0.0


def expected_rate(user_rates, pick_rate: Callable, company: str,
                  product: str | None, product_type: str | None,
                  is_gemel: bool) -> float:
    """The rate to use for one production record's EXPECTED commission.

    `pick_rate` is the endpoint's existing product matcher (kept so book+reward
    summing and product specificity still apply for insurance). Returns 0 when
    no sane rate exists — the caller skips the record."""
    if is_gemel:
        return gemel_rate_for(user_rates, company)
    rate = pick_rate(company, product) or pick_rate(company, product_type)
    if rate <= 0 or rate > INSURANCE_RATE_CEILING:
        rate = insurance_rate_for(user_rates, company, product, product_type)
    if rate <= 0 or rate > INSURANCE_RATE_CEILING:
        return 0.0
    return rate


def make_pick_rate(user_rates) -> Callable[[str, str | None], float]:
    """Canonical product-rate matcher — the SINGLE source of truth for
    `pick_rate`, previously copy-pasted inline in api/production.py (×2) and
    api/insights.py. Returns a closure `pick(company, product) -> float`.

    Priority (after canonical company match, with substring fallback):
      1. Product overlap (either direction). If a `total` row exists, use it;
         else sum book + reward when both present (Phoenix/Harel agreements —
         see commission_rate_summing.md); else single/first.
      2. Company-level default (product IS NULL).
      3. Any company rate (last resort).
    Returns 0.0 when nothing matches.
    """
    def pick(company_name: str, product_name: str | None = None) -> float:
        if not company_name or not user_rates:
            return 0.0
        target_canon = normalize_company(company_name)
        candidates = []
        if target_canon:
            candidates = [
                r for r in user_rates
                if r.company_name and normalize_company(r.company_name) == target_canon
            ]
        if not candidates:
            target_lc = company_name.strip().lstrip("ה").lower()
            candidates = [
                r for r in user_rates
                if r.company_name and (
                    target_lc in r.company_name.lstrip("ה").lower()
                    or r.company_name.lstrip("ה").lower() in target_lc
                )
            ]
        if not candidates:
            return 0.0

        prod_lc = (product_name or "").strip().lower()
        if prod_lc:
            product_matches = [
                r for r in candidates
                if r.product and (
                    prod_lc in r.product.lower() or r.product.lower() in prod_lc
                )
            ]
            if product_matches:
                totals = [r for r in product_matches
                          if (getattr(r, "rate_kind", None) or "").lower() == "total"]
                if totals:
                    return float(totals[0].rate)
                book = next((r for r in product_matches
                             if (getattr(r, "rate_kind", None) or "").lower() == "book"), None)
                reward = next((r for r in product_matches
                               if (getattr(r, "rate_kind", None) or "").lower() == "reward"), None)
                if book and reward:
                    return float(book.rate) + float(reward.rate)
                if book:
                    return float(book.rate)
                if reward:
                    return float(reward.rate)
                singles = [r for r in product_matches
                           if (getattr(r, "rate_kind", None) or "single").lower() == "single"]
                if singles:
                    return float(singles[0].rate)
                return float(product_matches[0].rate)

        defaults = [r for r in candidates if not r.product]
        if defaults:
            prio = [r for r in defaults
                    if (getattr(r, "rate_kind", None) or "single") in ("total", "single")]
            chosen = prio[0] if prio else defaults[0]
            return float(chosen.rate)

        prio = [r for r in candidates
                if (getattr(r, "rate_kind", None) or "single") in ("total", "single")]
        chosen = prio[0] if prio else candidates[0]
        return float(chosen.rate)

    return pick


def compute_expected_commission(rows, user_rates) -> tuple[float, list[dict]]:
    """Total EXPECTED monthly commission over a set of production records, plus
    a per-company breakdown. The canonical implementation of the production
    dashboard's "עמלות צפויות לפי ההסכמים" number (number B in
    commission_calculation_model.md) — shared by the dashboard and the AI chat
    so the two ALWAYS report the same figure.

    Per record:
      • accumulation-based (gemel/השתלמות/חיסכון/מנהלים): accum × rate ÷ 12
      • premium-based (risk insurance): premium × rate
    Records with no sane rate (rate ≤ 0) or zero base are skipped.

    `rows` is any iterable whose items expose attributes: id_number,
    receiving_company, product_type, product, total_premium, accumulation
    (both ORM ClientRecord objects and column-select Row objects qualify).

    Returns (total, by_company) where by_company is sorted desc by total:
        [{"company": str, "total": float, "clients_count": int}, ...]
    """
    pick_rate = make_pick_rate(user_rates)
    by_company: dict[str, dict] = {}
    total = 0.0
    for r in rows:
        company = r.receiving_company
        if not company:
            continue
        accum_f = float(r.accumulation or 0)
        premium_f = float(r.total_premium or 0)
        is_accum = accumulation_based(r.product_type, accum_f)
        rate = expected_rate(user_rates, pick_rate, company, r.product, r.product_type, is_accum)
        if rate <= 0:
            continue
        if is_accum:
            exp = accum_f * rate / 12.0
        else:
            if premium_f <= 0:
                continue
            exp = premium_f * rate
        if exp <= 0:
            continue
        bucket = by_company.setdefault(company, {"total": 0.0, "clients": set()})
        bucket["total"] += exp
        bucket["clients"].add(r.id_number)
        total += exp

    by_company_list = sorted(
        [
            {"company": co, "total": round(d["total"], 2), "clients_count": len(d["clients"])}
            for co, d in by_company.items()
            if d["total"] > 0
        ],
        key=lambda x: -x["total"],
    )
    return round(total, 2), by_company_list
