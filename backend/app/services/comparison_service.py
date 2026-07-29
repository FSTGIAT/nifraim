from collections import defaultdict

from app.utils.company_norm import company_stem, known_company_stem

# ---------------------------------------------------------------------------
# Product category classification
# ---------------------------------------------------------------------------
# Category 1: גמל והשתלמות  (Gemel & Education Fund)
# Category 2: ביטוח          (Insurance: life, health, savings, long-term care)
# Pension:    ALWAYS EXCLUDED from comparison
# ---------------------------------------------------------------------------

_CATEGORY_GEMEL = "gemel_hishtalmut"
_CATEGORY_INSURANCE = "insurance"
_CATEGORY_PENSION = "pension"

# The `category` column on commission_comparisons / debts is now a passive
# LABEL — nothing branches on it. New rows are written under this single value
# because a comparison is no longer produced per category; historical rows keep
# their גמל/ביטוח labels and are still readable, since the read paths select the
# newest row per user instead of filtering by category.
MERGED_CATEGORY = "merged"

_CATEGORY_LABELS = {
    _CATEGORY_GEMEL: "גמל והשתלמות",
    _CATEGORY_INSURANCE: "ביטוח",
    _CATEGORY_PENSION: "פנסיה",
}

# Map production product_type values → category
_PRODUCT_TYPE_TO_CATEGORY = {
    "קופת גמל לתגמולים ופיצויים": _CATEGORY_GEMEL,
    "קופת גמל להשקעה": _CATEGORY_GEMEL,
    "קרן השתלמות": _CATEGORY_GEMEL,
    "ביטוח חיים": _CATEGORY_INSURANCE,
    "ביטוח חיים משכנתא": _CATEGORY_INSURANCE,
    "ביטוח בריאות": _CATEGORY_INSURANCE,
    "פוליסת חיסכון פיננסי": _CATEGORY_INSURANCE,
    "מנהלים חיסכון טהור": _CATEGORY_INSURANCE,
    "ביטוח מנהלים": _CATEGORY_INSURANCE,
    "ביטוח סיעודי": _CATEGORY_INSURANCE,
    "קרן פנסיה חדשה מקיפה": _CATEGORY_PENSION,
    "קרן פנסיה חדשה כללית": _CATEGORY_PENSION,
}

# Keywords in commission product names → category
_GEMEL_KEYWORDS = ["גמל", "השתלמות", "תגמולים", "חיסכון פלוס"]
_INSURANCE_KEYWORDS = ["חיים", "בריאות", "סיעוד", "חסכון פרט", "פיננסי", "משכנתא"]


def _classify_product_type(product_type: str | None) -> str | None:
    """Classify a production product_type into a comparison category."""
    if not product_type:
        return None
    return _PRODUCT_TYPE_TO_CATEGORY.get(product_type)


def _is_mixed_category(commission_records: list[dict]) -> bool:
    """True when the commission set contains BOTH גמל and ביטוח products.

    The merged נפרעים file always does. Used to suppress the category label
    rather than let the majority vote name one half of a two-category file.
    """
    gemel = insurance = False
    for r in commission_records:
        product = (r.get("fund_type") or r.get("product") or "").lower()
        if not product:
            continue
        if any(kw in product for kw in _GEMEL_KEYWORDS):
            gemel = True
        if any(kw in product for kw in _INSURANCE_KEYWORDS):
            insurance = True
        if gemel and insurance:
            return True
    return False


def _detect_commission_category(commission_records: list[dict]) -> str | None:
    """Detect the category of a commission file from its product names.

    Scans product/fund_type fields for keywords to determine if the file
    covers גמל/השתלמות or ביטוח products.
    """
    gemel_count = 0
    insurance_count = 0

    for r in commission_records:
        product = (r.get("fund_type") or r.get("product") or "").lower()
        if not product:
            continue
        if any(kw in product for kw in _GEMEL_KEYWORDS):
            gemel_count += 1
        if any(kw in product for kw in _INSURANCE_KEYWORDS):
            insurance_count += 1

    if gemel_count > 0 and insurance_count == 0:
        return _CATEGORY_GEMEL
    if insurance_count > 0 and gemel_count == 0:
        return _CATEGORY_INSURANCE
    if gemel_count > 0 and insurance_count > 0:
        # Mixed file — use majority
        return _CATEGORY_GEMEL if gemel_count >= insurance_count else _CATEGORY_INSURANCE
    return None


# Insurer names that may appear at the START of a product string, used ONLY
# when the record carries no company of its own. Longer names first so the
# match is greedy. Sub-brands map to the parent insurer they belong to —
# 'מבטחים' is Menora's pension brand, not a company, and reporting it as one
# split Menora into two rows on every per-company view.
_PRODUCT_COMPANY_PREFIXES = [
    ("אלטשולר שחם", "אלטשולר"), ("מנורה מבטחים", "מנורה"), ("ילין לפידות", "ילין"),
    ("מיטב דש", "מיטב"), ("ביטוח ישיר", "ביטוח ישיר"), ("אי.בי.אי", "אי.בי.אי"),
    ("אינטרגמל", "מור"), ("מבטחים", "מנורה"),
    ("אקסלנס", "אקסלנס"), ("הפניקס", "הפניקס"), ("פניקס", "הפניקס"),
    ("מנורה", "מנורה"), ("הכשרה", "הכשרה"), ("הראל", "הראל"), ("כלל", "כלל"),
    ("מגדל", "מגדל"), ("פסגות", "פסגות"), ("איילון", "איילון"),
    ("אנליסט", "אנליסט"), ("מור", "מור"), ("מגה", "מגה"), ("ישיר", "ישיר"),
    ("מיטב", "מיטב"),
]


def _extract_short_company(product_name: str | None, receiving_company: str | None) -> str:
    """The company a record belongs to, as a short display/grouping name.

    `receiving_company` WINS. It is the record's own company column — the
    authoritative field — and it was previously the last resort, behind two
    guesses parsed out of the product string. Both guesses invented companies:

      • "split on ' - '" turned the product 'פרודוקציה - חיים' into the company
        'פרודוקציה' for 285 live records whose receiving_company plainly said
        'מנורה מבטחים ביטוח בע"מ';
      • prefix matching turned the product 'מבטחים יותר' into 'מבטחים' for 68
        records whose receiving_company said 'מנורה'.

    Both then rendered as separate insurers on every per-company view, and the
    unpaid customers behind them were attributed to a company that isn't real.

    Product parsing is kept only for records with NO company column, and now
    has to name a RECOGNISED insurer to be believed.
    """
    if receiving_company and receiving_company.strip():
        # Shorten to the brand so the merged file's legal names group with the
        # commission side's short ones ('מנורה מבטחים ביטוח בע"מ' → 'מנורה').
        return company_stem(receiving_company) or receiving_company.strip()

    if product_name:
        head = product_name.split(" - ")[0].strip()
        known = known_company_stem(head)
        if known:
            return known
        for prefix, parent in _PRODUCT_COMPANY_PREFIXES:
            if product_name.startswith(prefix):
                return parent

    return ""


def _normalize_id(id_number: str | None) -> str:
    """Normalize Israeli ID number for matching.

    Production files often strip leading zeros (e.g. '10725604'),
    while commission files keep them (e.g. '010725604').
    Normalize by stripping leading zeros so both map to the same key.
    """
    if not id_number:
        return ""
    return str(id_number).lstrip("0") or "0"


def _extract_policy_core(policy: str | None) -> str | None:
    """Extract the core account number from a compound policy number.

    Production format: 'X-YYY-ZZZZZZ-N' where ZZZZZZ is the actual account.
    Commission format: just 'ZZZZZZ'.
    Returns the 3rd segment if dash-separated, otherwise the original value.
    """
    if not policy:
        return None
    s = str(policy).strip()
    parts = s.split("-")
    if len(parts) == 4:
        return parts[2]
    return s


def _first_set(*values):
    """Return the first value that is not None (preserves 0 and 0.0)."""
    for v in values:
        if v is not None:
            return v
    return None


def _get_commission(record: dict):
    """Get the commission amount from a record, handling different company formats.

    Priority: commission_paid → commission_before_fee → actual_amount
    - commission_paid: Phoenix, Menora, Altshuler, Hachshara (with VAT) — the
      net amount that actually hit the agent's account.
    - commission_before_fee: Mor (pre-fee), Hachshara (ex-VAT), Harel
      (gross — fee deducted afterwards). Used when paid is missing.
    - actual_amount: Excellence agent_tracking (actual transfer).

    NEVER falls back to commission_expected. That column held nonsense in
    Menora ("פרמיה לעמלה" was misclassified as commission, sum=₪163,447) and
    is a computed estimate elsewhere — never an actual paid figure. Callers
    that explicitly want expected/estimated commission must read the
    column directly.
    """
    return _first_set(
        record.get("commission_paid"),
        record.get("commission_before_fee"),
        record.get("actual_amount"),
    )


def agent_net_commission(record: dict) -> float:
    """The amount that actually hit the agent's bank account this period.
    Always a float (0 when no data). Used by every aggregator that reports
    'paid commission' to the user."""
    v = _get_commission(record)
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _get_balance(record: dict):
    """Get the balance/accumulation from a record, handling different company formats."""
    return _first_set(record.get("month_end_balance"), record.get("balance"))


def _is_paying_company(company_name: str | None, paying_list: list[str]) -> bool:
    """Check if company matches any paying company (partial match)."""
    if not company_name or not paying_list:
        return False
    company_lower = company_name.lower()
    return any(
        pc.lower() in company_lower or company_lower in pc.lower()
        for pc in paying_list
    )


def compute_comparison(production_records: list[dict], commission_records: list[dict],
                        paying_company_names: list[str] | None = None,
                        category_override: str | None = None) -> dict:
    """
    Compare production file records against commission report records.
    Match customers by id_number, then match products by fund_policy_number.

    Production is scoped by COMPANY COVERAGE, not by גמל/ביטוח category:
    - a production record is only judged paid/unpaid if its company appears in
      the commission set being compared;
    - companies with no נפרעים coverage are reported separately as
      `uncovered_companies`, never as unpaid;
    - פנסיה products are ALWAYS excluded (נפרעים is paid on the monthly
      deposit, not on the accumulated balance).

    Why the category filter is gone
    -------------------------------
    It existed for one case: when the agent uploaded a גמל-only נפרעים file,
    every insurance client would otherwise be reported `only_production`, i.e.
    falsely unpaid. Portal automation now delivers ONE merged נפרעים file
    covering all companies and both categories, so the filter has no such job —
    it only cut the picture in half, forcing the agent to toggle a category to
    see the rest, and `api/comparison.py` had to majority-vote a mixed merged
    file into a single category, mislabelling the minority half.

    Company coverage is the more precise guard and works for both shapes: a
    single-company upload only judges that company; the merged file judges
    everything it covers. `category_override` and the detected category are
    still accepted and returned as passive LABELS so stored rows keep meaning.
    """
    # Kept for the response label only — this no longer filters anything.
    #
    # A MIXED set gets NO label. `_detect_commission_category` resolves mixed
    # files by majority vote, which is meaningless for a merged נפרעים file
    # covering both categories — and the label is not merely decorative
    # downstream: the frontend summary branches on it to decide whether
    # zero-accumulation customers count as unpaid, and the dashboard picks its
    # hint text from it. Labelling a both-categories comparison "גמל והשתלמות"
    # is the same majority-vote defect this change removed from the API,
    # one layer up. Empty label → every consumer degrades to neutral.
    if category_override and category_override in (_CATEGORY_GEMEL, _CATEGORY_INSURANCE):
        commission_category = category_override
    else:
        commission_category = _detect_commission_category(commission_records)
        if commission_category is not None and _is_mixed_category(commission_records):
            commission_category = None

    # Which companies does this commission set actually speak for? Matched on
    # the brand stem so the merged file's canonical legal names
    # ('הראל פנסיה וגמל בע"מ') line up with production's own naming.
    covered_stems = {
        company_stem(r.get("receiving_company") or r.get("company_source") or "")
        for r in commission_records
    }
    covered_stems.discard("")

    filtered_production = []
    uncovered_counts: dict[str, int] = {}
    for r in production_records:
        cat = _classify_product_type(r.get("product_type"))
        if cat == _CATEGORY_PENSION:
            continue  # always exclude pension
        company = r.get("receiving_company")
        # No resolvable company on the commission side (some parsers leave it
        # empty) → compare everything, as before. Filtering on an empty set
        # would silently drop the entire production file.
        if covered_stems and company and company_stem(company) not in covered_stems:
            uncovered_counts[company] = uncovered_counts.get(company, 0) + 1
            continue
        filtered_production.append(r)

    uncovered_companies = [
        {"company": co, "records": n}
        for co, n in sorted(uncovered_counts.items(), key=lambda kv: -kv[1])
    ]

    # Extract unique short company names from filtered production
    company_names = set()
    for r in filtered_production:
        short = _extract_short_company(r.get("product"), r.get("receiving_company"))
        if short and short not in ("nan", "None"):
            company_names.add(short)
    available_companies = sorted(company_names)

    # Group by normalized id_number (strip leading zeros for consistent matching)
    prod_by_id = defaultdict(list)
    for r in filtered_production:
        if r.get("id_number"):
            prod_by_id[_normalize_id(r["id_number"])].append(r)

    comm_by_id = defaultdict(list)
    for r in commission_records:
        if r.get("id_number"):
            comm_by_id[_normalize_id(r["id_number"])].append(r)

    all_ids = set(prod_by_id.keys()) | set(comm_by_id.keys())
    matched_ids = set(prod_by_id.keys()) & set(comm_by_id.keys())
    only_prod_ids = set(prod_by_id.keys()) - set(comm_by_id.keys())
    only_comm_ids = set(comm_by_id.keys()) - set(prod_by_id.keys())

    customers = []

    for id_num in sorted(all_ids):
        prod_recs = prod_by_id.get(id_num, [])
        comm_recs = comm_by_id.get(id_num, [])

        # Customer name from whichever source has data
        name_source = prod_recs[0] if prod_recs else comm_recs[0]

        if id_num in matched_ids:
            status = "matched"
        elif id_num in only_prod_ids:
            status = "only_production"
        else:
            status = "only_commission"

        # Aggregate production data
        prod_premium = sum(r.get("total_premium") or 0 for r in prod_recs)
        prod_products = []
        for r in prod_recs:
            product_name = r.get("product") or ""
            sign_date_val = r.get("sign_date")
            prod_products.append({
                "product": product_name,
                "product_type": r.get("product_type"),
                "company": _extract_short_company(product_name, r.get("receiving_company")),
                "company_full": r.get("receiving_company"),
                "premium": r.get("total_premium"),
                "policy_number": r.get("fund_policy_number"),
                "status": r.get("product_status"),
                "accumulation": r.get("accumulation"),
                "sign_date": str(sign_date_val) if sign_date_val else None,
                "track": r.get("track"),
                "client_phone": r.get("client_phone"),
                "client_email": r.get("client_email"),
                "employer_name": r.get("employer_name"),
                "employer_id": r.get("employer_id"),
            })

        # Aggregate commission data
        comm_total = sum(_get_commission(r) or 0 for r in comm_recs)
        comm_products = [
            {
                "product": r.get("fund_type") or r.get("product"),
                "account": r.get("fund_policy_number"),
                "balance": _get_balance(r),
                "commission": _get_commission(r),
                "annual_pct": r.get("annual_commission_pct"),
                "monthly_pct": r.get("monthly_commission_pct"),
                # Same treatment as production products: `company` is the SHORT
                # brand used for grouping, `company_full` the raw name. This was
                # the raw value while production was stemmed, so one insurer
                # appeared under two names ('מגדל' and 'מגדל חברה לביטוח בע"מ')
                # on any view that groups the two sides together.
                "company": _extract_short_company(
                    r.get("fund_type") or r.get("product"), r.get("receiving_company")
                ),
                "company_full": r.get("receiving_company"),
                "fund_type": r.get("fund_type"),
                "management_fee": r.get("management_fee"),
                "management_fee_amount": r.get("management_fee_amount"),
            }
            for r in comm_recs
        ]

        # Product-level matching by account number
        product_matches = _match_products(prod_recs, comm_recs)
        paid_count = len(product_matches["matched"])
        unpaid_count = len(product_matches["unmatched_production"])

        has_paying = False
        if paying_company_names:
            # Check production products
            has_paying = any(
                _is_paying_company(
                    p.get("company_full") or p.get("company"),
                    paying_company_names,
                )
                for p in prod_products
            )
            # Also check commission records (for only_commission customers)
            if not has_paying and comm_recs:
                has_paying = any(
                    _is_paying_company(
                        r.get("receiving_company") or r.get("fund_type") or r.get("product"),
                        paying_company_names,
                    )
                    for r in comm_recs
                )

        # Aggregate client contact info from first production record
        contact_source = prod_recs[0] if prod_recs else {}
        customers.append({
            "id_number": id_num,
            "first_name": name_source.get("first_name"),
            "last_name": name_source.get("last_name"),
            "match_status": status,
            "client_phone": contact_source.get("client_phone"),
            "client_email": contact_source.get("client_email"),
            "employer_name": contact_source.get("employer_name"),
            "employer_id": contact_source.get("employer_id"),
            "production_count": len(prod_recs),
            "commission_count": len(comm_recs),
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
            "total_premium": prod_premium,
            "total_commission": comm_total,
            "has_paying_company": has_paying,
            "production_products": prod_products,
            "commission_products": comm_products,
            "product_matches": product_matches,
        })

    summary = {
        "total_customers": len(all_ids),
        "matched": len(matched_ids),
        "only_in_production": len(only_prod_ids),
        "only_in_commission": len(only_comm_ids),
        "total_premium": sum(c["total_premium"] for c in customers),
        "total_commission": sum(c["total_commission"] for c in customers),
    }

    return {
        "summary": summary,
        "customers": customers,
        "available_companies": available_companies,
        # Companies present in production that this commission set says nothing
        # about. Reported so they can be shown as "no נפרעים coverage" rather
        # than silently counted as unpaid.
        "uncovered_companies": uncovered_companies,
        # Passive labels — nothing branches on these any more.
        "commission_category": commission_category,
        "commission_category_label": _CATEGORY_LABELS.get(commission_category, ""),
    }


def _policy_matches(prod_policy: str, comm_policy: str) -> bool:
    """Check if production and commission policy numbers refer to the same account.

    Handles compound production format 'X-YYY-ZZZZZZ-N' where the 3rd segment
    is the core account number that commission files use directly.
    """
    p = str(prod_policy).strip()
    c = str(comm_policy).strip()
    # Direct match
    if p == c:
        return True
    # Extract core from compound production policy and compare
    p_core = _extract_policy_core(p)
    c_core = _extract_policy_core(c)
    if p_core and c_core and p_core == c_core:
        return True
    # Cross-compare: production core vs commission raw (and vice versa)
    if p_core and p_core == c:
        return True
    if c_core and c_core == p:
        return True
    return False


def _match_products(prod_recs: list[dict], comm_recs: list[dict]) -> dict:
    """Match products between production and commission by account/policy number."""
    matched = []
    unmatched_prod = list(prod_recs)
    unmatched_comm = list(comm_recs)

    for pr in list(unmatched_prod):
        pn = pr.get("fund_policy_number")
        if not pn:
            continue
        for cr in list(unmatched_comm):
            cn = cr.get("fund_policy_number")
            if cn and _policy_matches(pn, cn):
                product_name = pr.get("product") or ""
                matched.append({
                    "policy_number": pn,
                    "production_product": product_name,
                    "commission_product": cr.get("fund_type") or cr.get("product"),
                    "company": _extract_short_company(product_name, pr.get("receiving_company")),
                    "premium": pr.get("total_premium"),
                    "accumulation": pr.get("accumulation"),
                    "commission": _get_commission(cr),
                    "balance": _get_balance(cr),
                    "monthly_pct": cr.get("monthly_commission_pct"),
                    "annual_pct": cr.get("annual_commission_pct"),
                    "track": pr.get("track"),
                    "management_fee": cr.get("management_fee"),
                    "management_fee_amount": cr.get("management_fee_amount"),
                })
                unmatched_prod.remove(pr)
                unmatched_comm.remove(cr)
                break

    return {
        "matched": matched,
        "unmatched_production": [
            {"product": r.get("product"), "product_type": r.get("product_type"),
             "company": _extract_short_company(r.get("product"), r.get("receiving_company")),
             "company_full": r.get("receiving_company"),
             "premium": r.get("total_premium"),
             "policy_number": r.get("fund_policy_number"),
             "accumulation": r.get("accumulation"),
             "sign_date": str(r["sign_date"]) if r.get("sign_date") else None,
             "track": r.get("track"),
             "client_phone": r.get("client_phone"),
             "client_email": r.get("client_email"),
             "employer_name": r.get("employer_name"),
             "employer_id": r.get("employer_id")}
            for r in unmatched_prod
        ],
        "unmatched_commission": [
            {"product": r.get("fund_type") or r.get("product"),
             "account": r.get("fund_policy_number"),
             "commission": _get_commission(r),
             "balance": _get_balance(r),
             "company": _extract_short_company(r.get("fund_type") or r.get("product"), r.get("receiving_company")),
             "fund_type": r.get("fund_type")}
            for r in unmatched_comm
        ],
    }
