"""Commission-rate selection for the EXPECTED-commission math — ONE selector.

Shared by api/production.py (dashboard + trend), api/insights.py (monthly view)
and services/ai_service.py, so every expected-commission number agrees.

What this module guards against
-------------------------------
Agreement rate tables mix two very different things:
  • monthly נפרעים rates  — gemel 0.2–0.6%/yr, insurance ~3–15%
  • one-time scope/heqef (ריסק) rates — 28–60%

A last-resort "any company rate" fallback could return a 60% ריסק rate and the
caller would apply it to a gemel ACCUMULATION, inflating expected commission
2–3×. That is what `GEMEL_RATE_CEILING` / `INSURANCE_RATE_CEILING` exist for.

Why there is no longer a gemel-vs-insurance branch
--------------------------------------------------
There used to be two selectors, `gemel_rate_for` and `insurance_rate_for`, and
`expected_rate` routed every gemel record to the first one. Only the third,
product-level matcher had a company fallback — so a single company-name
mismatch silently zeroed a whole company's gemel book, with no error anywhere.

Measured live 2026-07-27, this is what it cost: a user with a healthy 216-row
agreement shelf had 121 of 511 production records match NO rate at all, because
portal automation's merged file writes canonical legal names
('מנורה מבטחים פנסיה וגמל בע"מ') while the agreement shelf holds short names
('מנורה'), and `normalize_company` does not invert `canonical_company`.

So: one `select_rate` for every product. The only remaining branch is the
COMMISSION BASIS, and that is a property of the record's own data
(`accumulation_based`) rather than a category the caller must know:
  • accumulation-bearing → accum × rate ÷ 12
  • otherwise            → premium × rate
The ceilings are applied per record by that basis.

Invariant: a rate that does not match must be REPORTED, never silently
skipped. `select_rate` returns a `route` explaining every decision, and
`explain_expected_commission` turns those into a per-company coverage report.
"""
from __future__ import annotations

from typing import Callable

from app.utils.company_norm import company_residue, company_stem, normalize_company

# Magnitude guards separating monthly נפרעים rates from one-time scope/heqef
# rates. Applied per RECORD by its commission basis, not by a category.
GEMEL_RATE_CEILING = 0.03      # 3%/yr — real gemel נפרעים rates are 0.2–0.6%

# 25%: high enough to admit a legitimate SUMMED book+reward rate, low enough to
# still reject scope/היקף (28–60%) and clawback. It was 0.20, which silently
# rejected the canonical worked example in commission_rate_summing.md —
# השתלות שנה 6-15 = עמלת ספר 15% + שיעור תגמול 7.2% = 22.2% — and fell back to
# the median, answering 15% (the book component alone) for a rate the agreement
# plainly prints as 22.2%. Live data confirms the guard is still needed:
# מיטב clawback rows sit at 33% and 66%.
#
# Measured 2026-07-27: NO stored rate row sits in (0.20, 0.25], so this band
# only ever admits a book+reward SUM computed here — it cannot let a leaked
# scope rate through. Worth ₪82 of ₪108,374 today; the raise is about being
# right when an agreement does print a summed 22.2%, not about the amount.
INSURANCE_RATE_CEILING = 0.25


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


def _kind(rate_row) -> str:
    return (getattr(rate_row, "rate_kind", None) or "single").lower()


def _overlap(a: str, b: str) -> bool:
    """Substring match in either direction — agreement product names and
    production product names each tend to be a superset of the other
    ('פוליסות מסוג מגוון' vs 'מגוון')."""
    return bool(a) and bool(b) and (a in b or b in a)


# Words that appear in almost every Israeli product name and therefore carry no
# discriminating power. Matching on one of these alone is a FALSE match: live,
# a 'מנורה - חיים' life policy matched the rate row
# 'בריאות – נספחי ביטוח ואמבולטורי' on the shared word 'ביטוח' and was priced at
# 19.2% — a health rate applied to a life policy.
_GENERIC_PRODUCT_TOKENS = frozenset({
    "ביטוח", "ביטוחי", "פוליסה", "פוליסות", "פוליסת", "מסוג", "סוג",
    "חברה", "בעמ", "קרן", "קרנות", "קופה", "קופות", "תוכנית", "תכנית",
    "מוצר", "מוצרי", "עמלת", "עמלה", "שיעור", "נספחי", "נספח",
})


def _tokens(s: str) -> set[str]:
    """Discriminating words of `s`. Leading ו is stripped ('והשתלמות' →
    'השתלמות') so a conjunction can't hide a match; tokens under 3 chars and
    generic product words are dropped as noise."""
    return {
        t for t in (tok.lstrip("ו") for tok in s.split())
        if len(t) >= 3 and t not in _GENERIC_PRODUCT_TOKENS
    }


def _token_score(a: str, b: str) -> int:
    """How strongly product text `a` matches product text `b`, as a count of
    shared discriminating words.

    Word-level matching is necessary because Israeli product names are
    multi-word and rarely nest: 'ביטוח חיים' is not a substring of
    'מנורה - חיים' nor vice versa, yet they are the same product. Without it
    those records fell past the product tier to a blanket median, which priced
    78 מנורה life policies at the 10% median of every מנורה rate instead of
    the ~1.5% the חיים rows actually say.

    Whole-string containment only sets a FLOOR of 1 — it deliberately does not
    outrank a multi-word match. Scoring containment above token overlap made
    short product names win everything: 'גמל' is contained in almost every
    gemel product text, so a bare 'גמל' rate beat the far more specific
    'קופות גמל / נפרעים' line from the actual agreement, repricing 223 מור
    records from the agreement's 0.25% to a seeded 0.30%.
    """
    if not a or not b:
        return 0
    shared = len(_tokens(a) & _tokens(b))
    if shared:
        return shared
    return 1 if (a in b or b in a) else 0


def _token_overlap(a: str, b: str) -> bool:
    """Any meaningful WORD of `a` appearing anywhere in `b`.

    Deliberately looser than `_token_score` — used for company-name residue,
    where the residue is a fragment ('גמל והשתלמות') rather than a product name
    and substring-within-word matching is wanted.
    """
    if not a or not b:
        return False
    return any(t in b for t in _tokens(a))


def _effective_rate(rows) -> float:
    """The rate a set of same-product rows really means.

    total → book+reward → book → reward → single → first. Summing book+reward
    is the Israeli agreement convention (עמלת ספר + שיעור תגמול), but ONLY when
    both are literally present — see commission_rate_summing.md.
    """
    if not rows:
        return 0.0
    totals = [r for r in rows if _kind(r) == "total"]
    if totals:
        return float(totals[0].rate)
    book = next((r for r in rows if _kind(r) == "book"), None)
    reward = next((r for r in rows if _kind(r) == "reward"), None)
    if book and reward:
        return float(book.rate) + float(reward.rate)
    if book:
        return float(book.rate)
    if reward:
        return float(reward.rate)
    # Several plain rows for the same product — in practice the same product at
    # different policy-year bands (`rate_scope`), which nothing matches on yet.
    # Take the median rather than the first: `rows[0]` made the answer depend on
    # DB order, so one מנורה product returned 19.2% or 9.2% run to run.
    singles = [r for r in rows if _kind(r) == "single"] or list(rows)
    vals = sorted(float(r.rate) for r in singles if r.rate is not None)
    return vals[len(vals) // 2] if vals else 0.0


def company_candidates(user_rates, company: str) -> tuple[list, str]:
    """The rate rows belonging to `company`, plus HOW they were found.

    Two tiers, and the second one is the fix for the automation merge:
      1. `normalize_company` equality — preserves every match that already worked.
      2. `company_stem` equality — catches the merged production file's canonical
         legal names ('מנורה מבטחים פנסיה וגמל בע"מ') against the agreement
         shelf's short names ('מנורה'), which tier 1 silently misses.

    The old raw-substring fallback is gone: measured against live data it never
    fired for canonical names ('מגדל קשת' vs 'מגדל חברה לביטוח בע"מ' fails in
    both directions), so it produced false confidence and no matches.

    The candidate SET is the stem set, deliberately — the tiers are not
    exclusive. Returning only the exact matches when any exist would hide the
    company's own sibling rows from the selector: for production
    'הראל פנסיה וגמל בע"מ', `normalize_company` keeps 'הראל מגוון' as
    'הראל מגוון', so an exact-only set silently drops the very row that prices
    מגוון policies. `tier` therefore reports whether an exact-normalised row
    was present, and precedence (product → residue → default → median) picks
    the winner within the set.
    """
    if not company or not user_rates:
        return [], "none"
    stem = company_stem(company)
    if not stem:
        return [], "none"
    rows = [
        r for r in user_rates
        if r.company_name and company_stem(r.company_name) == stem
    ]
    if not rows:
        return [], "none"
    canon = normalize_company(company)
    tier = "exact" if any(
        normalize_company(r.company_name) == canon for r in rows
    ) else "stem"
    return rows, tier


def is_seeded(rate_row) -> bool:
    """True for a rate that did NOT come from the agent's own agreement.

    `source_document_id` is NULL for rows created by `POST /commission-rates/seed`
    (the hardcoded `DEFAULT_COMMISSION_RATES` table) and for legacy rows. Those
    values belong to whoever the defaults were authored from — they are a
    starting point, not this agent's contract, and an expected-commission figure
    resting on them should say so rather than read as fact.
    """
    return getattr(rate_row, "source_document_id", None) is None


def select_rate(user_rates, company: str, product: str | None,
                product_type: str | None, is_accum: bool,
                ceiling: float | None = None) -> tuple[float, str]:
    """THE rate for one production record — one selector for every product.

    There is deliberately no gemel-vs-insurance branch here any more. The old
    split (`gemel_rate_for` / `insurance_rate_for`) existed to stop the matcher
    applying a one-time 28–60% ריסק rate to a gemel accumulation; that job is
    done by the magnitude `ceiling`, which is a property of the RECORD's basis
    (accumulation vs premium), not a category the caller has to know. Collapsing
    them also removed the real bug: only the product matcher had a company
    fallback, so a single name mismatch zeroed a whole company's gemel book.

    Returns (rate, route) where route explains the decision — 'exact:product',
    'stem:default', 'none', … — so a zero is always attributable.
    """
    candidates, tier = company_candidates(user_rates, company)
    if not candidates:
        return 0.0, "none"
    if ceiling is None:
        ceiling = GEMEL_RATE_CEILING if is_accum else INSURANCE_RATE_CEILING
    text = f"{product or ''} {product_type or ''}".strip().lower()

    # A premium-based record must not be priced with a gemel-magnitude rate.
    # The shelf's company-wide defaults are overwhelmingly savings rates
    # (0.30–0.50%), so without a FLOOR every unmatched ביטוח חיים / בריאות /
    # סיעודי record silently inherits one: measured live, 998 insurance records
    # were priced at 0.45% where the agreement says 19.2% — a ~40× error that
    # produced a plausible-looking, entirely wrong number.
    #
    # The floor guards only the FALLBACK tiers. An explicit product match is
    # semantic evidence and is trusted at any magnitude — if an agreement
    # literally prints a 0.5% rate against 'ביטוח חיים', that is the rate.
    floor = 0.0 if is_accum else GEMEL_RATE_CEILING

    def _ok(rate: float) -> bool:
        return 0 < rate <= ceiling

    def _ok_fallback(rate: float) -> bool:
        return floor < rate <= ceiling

    # 1. Rows that name a product. Keep only the BEST-scoring group so a
    #    weak one-word overlap can't dilute an exact product match, then
    #    longest product name first so the most specific agreement line wins
    #    instead of whichever row the DB happened to return.
    if text:
        scored = [
            (_token_score(r.product.lower(), text), r)
            for r in candidates if r.product
        ]
        best = max((s for s, _ in scored), default=0)
        if best > 0:
            matches = [r for s, r in scored if s == best]
            # Narrow to ONE product — the most specific line that tied. Only
            # then combine, because `_effective_rate` sums book+reward and
            # medians year-bands, both of which are only meaningful within a
            # single product. Letting it span two different products turned
            # 'קופות גמל / נפרעים' (0.25%, from the agreement) and a bare 'גמל'
            # (0.30%, seeded) into their 0.30% median for 223 מור records.
            longest = max(matches, key=lambda r: len(r.product or ""))
            target = (longest.product or "").lower()
            matches = [r for r in matches if (r.product or "").lower() == target]
            rate = _effective_rate(matches)
            if _ok(rate):
                return rate, f"{tier}:product"

    # 2. Company-default rows (product IS NULL).
    defaults = [r for r in candidates if not r.product]
    if defaults:
        # Legacy shape: the PRODUCT was smuggled into the company column
        # ('הראל מגוון', 'מגדל קשת', 'פניקס גמל והשתלמות'). Only consult the
        # residue when there is more than one default row to tell apart —
        # otherwise the single default is simply the company's rate. Strictly
        # gated on `product IS NULL`, so once the migration moves the residue
        # into the real product column this branch becomes an inert no-op.
        if len(defaults) > 1 and text:
            scored = [
                (company_residue(r.company_name).lower(), r) for r in defaults
            ]
            res_matches = [r for res, r in scored if _token_overlap(res, text)]
            if res_matches:
                res_matches.sort(key=lambda r: -len(company_residue(r.company_name)))
                rate = _effective_rate(res_matches)
                if _ok_fallback(rate):
                    return rate, f"{tier}:residue"
        if len(defaults) > 1:
            # Several company-wide rates and nothing to tell them apart. Take
            # the MEDIAN, not defaults[0] — picking the first made the answer
            # depend on DB row order, so the same portfolio could be priced at
            # 0.34% or 0.45% between two runs with nothing changed.
            vals = sorted(
                float(r.rate) for r in defaults
                if r.rate is not None and _ok_fallback(float(r.rate))
            )
            rate = vals[len(vals) // 2] if vals else 0.0
        else:
            rate = _effective_rate(defaults)
        if _ok_fallback(rate):
            return rate, f"{tier}:default"

    # 3. Magnitude-guarded last resort: the median of this company's in-range
    #    rates. This is what the old per-category helpers did, kept as a guard
    #    rather than as a separate code path.
    vals = sorted(
        float(r.rate) for r in candidates
        if r.rate is not None and _ok_fallback(float(r.rate))
    )
    if vals:
        return vals[len(vals) // 2], f"{tier}:median"
    return 0.0, f"{tier}:no_sane_rate"


def expected_rate(user_rates, pick_rate: Callable | None, company: str,
                  product: str | None, product_type: str | None,
                  is_gemel: bool) -> float:
    """The rate to use for one production record's EXPECTED commission.
    Returns 0 when no sane rate exists — the caller skips the record.

    `pick_rate` is accepted for signature compatibility with the existing call
    sites in api/production.py and api/insights.py and is no longer consulted:
    `select_rate` now does the product matching, book+reward summing and
    company fallback itself.
    """
    rate, _route = select_rate(user_rates, company, product, product_type, is_gemel)
    return rate


def make_pick_rate(user_rates) -> Callable[[str, str | None], float]:
    """Canonical product-rate matcher. Returns a closure `pick(company, product)`.

    Deliberately UNCAPPED (`ceiling=inf`) — this is the raw "what does the
    agreement say for this product" lookup, and its callers pass the result
    into `expected_rate`, which applies the basis-appropriate ceiling. Capping
    here as well would silently drop legitimate scope/היקף rates from any
    future caller that wants them.
    """
    def pick(company_name: str, product_name: str | None = None) -> float:
        rate, _route = select_rate(
            user_rates, company_name, product_name, None,
            is_accum=False, ceiling=float("inf"),
        )
        return rate

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
    total, by_company, _coverage = explain_expected_commission(rows, user_rates)
    return total, by_company


# Why a record contributed nothing. Ordered worst-to-least actionable for the UI.
NO_COMPANY = "no_company"    # no agreement row for this company at all
NO_RATE = "no_rate"          # company has rates, but none for this kind of product
NO_BASE = "no_base"          # matched a rate, but the file carries no premium/accumulation
OK_ACCUM = "accum"
OK_PREMIUM = "premium"

# These are shown to the agent verbatim, so they have to say what to DO.
# "no matching agreement" is too coarse: having no מנורה agreement at all and
# having a מנורה GEMEL rate but no insurance rate need different actions.
_REASON_LABELS_HE = {
    NO_COMPANY: "אין הסכם לחברה הזו",
    NO_RATE: "יש הסכם, אך אין שיעור עמלה לסוג המוצר הזה",
    NO_BASE: "אין פרמיה או צבירה בקובץ",
}


def explain_expected_commission(rows, user_rates) -> tuple[float, list[dict], list[dict]]:
    """`compute_expected_commission` plus a per-company COVERAGE report.

    The coverage report exists because every failure in this module is a
    `continue`: a company whose name doesn't match, or whose records carry no
    premium, contributes ₪0 and vanishes from the dashboard with no error. The
    agent then sees a small number and has no way to learn why. Live 2026-07-27
    that was 77% of one user's portfolio.

    Returns (total, by_company, coverage) where each coverage entry is:
        {"company", "records", "contributing", "no_rate", "no_base",
         "matched_via", "expected", "reason", "reason_label"}
    `matched_via` is the winning route ('exact:product', 'stem:default', …) or
    'none'; `reason` is set only when the company contributed nothing.
    """
    by_company: dict[str, dict] = {}
    total = 0.0
    # Which companies the agent has a REAL (document-backed) agreement for.
    # Anything else is priced off the seeded defaults.
    documented_stems = {
        company_stem(x.company_name) for x in user_rates
        if x.company_name and not is_seeded(x)
    }
    documented_stems.discard("")

    for r in rows:
        company = r.receiving_company
        if not company:
            continue
        accum_f = float(r.accumulation or 0)
        premium_f = float(r.total_premium or 0)
        is_accum = accumulation_based(r.product_type, accum_f)
        rate, route = select_rate(
            user_rates, company, r.product, r.product_type, is_accum
        )

        bucket = by_company.setdefault(company, {
            "total": 0.0, "clients": set(), "records": 0, "contributing": 0,
            "no_rate": 0, "no_base": 0, "no_company": 0,
            "approximate": 0, "seeded": 0, "routes": {},
        })
        bucket["records"] += 1

        if rate <= 0:
            # route 'none' = the company isn't in the shelf at all;
            # '<tier>:no_sane_rate' = it is, but has no rate of the right
            # magnitude for this product's basis (e.g. gemel rates only, and
            # this is an insurance premium).
            if route == "none":
                bucket["no_company"] += 1
            else:
                bucket["no_rate"] += 1
            continue

        exp = accum_f * rate / 12.0 if is_accum else (premium_f * rate if premium_f > 0 else 0.0)
        if exp <= 0:
            bucket["no_base"] += 1
            continue

        bucket["routes"][route] = bucket["routes"].get(route, 0) + 1
        bucket["contributing"] += 1
        # A ':product' or ':residue' route priced this record off a rate line
        # that actually names the product. ':default' and ':median' are
        # estimates from the company's other rates — real numbers, but the
        # agent should be able to tell them apart from a firm one.
        if route.endswith((":default", ":median")):
            bucket["approximate"] += 1
        if company_stem(company) not in documented_stems:
            bucket["seeded"] += 1
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

    coverage = []
    for co, d in by_company.items():
        reason = None
        if d["contributing"] == 0:
            # Whichever failure dominates is the one worth showing the agent.
            reason = max(
                (NO_COMPANY, d["no_company"]), (NO_RATE, d["no_rate"]), (NO_BASE, d["no_base"]),
                key=lambda pair: pair[1],
            )[0]
        coverage.append({
            "company": co,
            "records": d["records"],
            "contributing": d["contributing"],
            "no_company": d["no_company"],
            "no_rate": d["no_rate"],
            "no_base": d["no_base"],
            "approximate": d["approximate"],
            "seeded": d["seeded"],
            "matched_via": max(d["routes"], key=d["routes"].get) if d["routes"] else "none",
            "expected": round(d["total"], 2),
            "reason": reason,
            "reason_label": _REASON_LABELS_HE.get(reason) if reason else None,
        })
    # Biggest uncovered books first — that's the agent's actionable list.
    coverage.sort(key=lambda c: (c["contributing"] > 0, -c["records"]))

    return round(total, 2), by_company_list, coverage
