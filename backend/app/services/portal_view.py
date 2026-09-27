"""What a customer may see in their portal — the ONE place hidden data is removed.

The agent chooses per link (setup wizard, `customer_portal_links.settings`):
which sections appear, which products (savings / insurance / all) and whether
amounts (premium / accumulation) are shown. Every customer-facing path —
/dashboard, /history, the AI chat context, the changes banner, print — goes
through `apply_settings` / `apply_to_history`, so a hidden number can't leak
through a side door (e.g. the chat answering "what's my premium?", or the
trend chart plotting full snapshot totals).

`settings = NULL` (every link created before the wizard) means "show
everything" — identical to the behaviour before this module existed.
"""
from __future__ import annotations

import copy

from app.services.comparison_service import (
    _classify_product_type,
    _CATEGORY_GEMEL,
    _CATEGORY_INSURANCE,
    _CATEGORY_PENSION,
    _GEMEL_KEYWORDS,
    _INSURANCE_KEYWORDS,
)

SECTION_KEYS = (
    "summary",      # KPI strip
    "products",     # המוצרים שלי
    "companies",    # פיזור לפי חברות
    "trend",        # מגמה לאורך זמן
    "changes",      # מה השתנה
    "ai_chat",      # עוזר AI
    "print",        # הדפסת דוח
    "agent_card",   # כרטיס סוכן
)
PRODUCT_SCOPES = ("all", "savings", "insurance")

# The agent's offer catalogue (step 3). Keys are stable; titles are defaults the
# agent may override per offer.
OFFER_CATALOG = {
    "travel":   'ביטוח נסיעות לחו"ל',
    "savings":  "פוליסת חיסכון",
    "health":   "ביטוח בריאות",
    "mortgage": "ביטוח משכנתא",
    "car_home": "ביטוח רכב ודירה",
}

_SAVINGS = {_CATEGORY_GEMEL, _CATEGORY_PENSION}


def default_settings() -> dict:
    return {
        "sections": {k: True for k in SECTION_KEYS},
        "product_scope": "all",
        "show_amounts": {"premium": True, "accumulation": True},
        "offers": [],
    }


def normalize_settings(raw: dict | None) -> dict:
    """Merge stored/incoming settings onto the defaults; drop anything unknown."""
    s = default_settings()
    if not isinstance(raw, dict):
        return s
    sections = raw.get("sections")
    if isinstance(sections, dict):
        for k in SECTION_KEYS:
            if k in sections:
                s["sections"][k] = bool(sections[k])
    if raw.get("product_scope") in PRODUCT_SCOPES:
        s["product_scope"] = raw["product_scope"]
    amounts = raw.get("show_amounts")
    if isinstance(amounts, dict):
        for k in ("premium", "accumulation"):
            if k in amounts:
                s["show_amounts"][k] = bool(amounts[k])
    offers = raw.get("offers")
    if isinstance(offers, list):
        s["offers"] = [o for o in dict.fromkeys(offers) if o in OFFER_CATALOG]
    return s


def product_category(product_type: str | None) -> str | None:
    """The app's existing classifier: comparison_service's exact product_type
    map, then its keyword lists (the exact map alone misses real types such as
    "חיים" / "ר.ת.-מורחב בריאות ביטוחים" — measured on prod 2026-09-27: exact
    only left ~2,300 of 5,080 rows unknown, exact+keywords leaves 89)."""
    cat = _classify_product_type(product_type)
    if cat or not product_type:
        return cat
    if any(k in product_type for k in _GEMEL_KEYWORDS):
        return _CATEGORY_GEMEL
    if any(k in product_type for k in _INSURANCE_KEYWORDS):
        return _CATEGORY_INSURANCE
    return None


def product_in_scope(product_type: str | None, scope: str) -> bool:
    """Savings = גמל/השתלמות/פנסיה, insurance = ביטוח. A product the classifier
    doesn't know appears only under "all": never guess a category for data the
    agent chose to limit."""
    if scope == "all":
        return True
    cat = product_category(product_type)
    if cat is None:
        return False
    return (cat in _SAVINGS) if scope == "savings" else (cat == _CATEGORY_INSURANCE)


def _kpi_and_breakdown(products: list[dict]) -> tuple[dict, list[dict]]:
    total_premium = sum(float(p.get("total_premium") or 0) for p in products)
    total_accum = sum(float(p.get("accumulation") or 0) for p in products)
    companies: dict[str, dict] = {}
    for p in products:
        co = p.get("receiving_company") or "אחר"
        e = companies.setdefault(co, {"company": co, "premium": 0.0, "accumulation": 0.0, "count": 0})
        e["premium"] += float(p.get("total_premium") or 0)
        e["accumulation"] += float(p.get("accumulation") or 0)
        e["count"] += 1
    kpi = {
        "product_count": len(products),
        "total_premium": round(total_premium, 2),
        "total_accumulation": round(total_accum, 2),
        "company_count": len({p.get("receiving_company") for p in products if p.get("receiving_company")}),
    }
    return kpi, sorted(companies.values(), key=lambda x: x["accumulation"], reverse=True)


def _hide_amounts_kpi(kpi: dict, show: dict) -> dict:
    kpi = dict(kpi)
    if not show["premium"]:
        kpi["total_premium"] = None
    if not show["accumulation"]:
        kpi["total_accumulation"] = None
    return kpi


def _hide_amounts_rows(rows: list[dict], show: dict, premium_key="total_premium", accum_key="accumulation") -> list[dict]:
    out = []
    for r in rows:
        r = dict(r)
        if not show["premium"] and premium_key in r:
            r[premium_key] = None
        if not show["accumulation"] and accum_key in r:
            r[accum_key] = None
        out.append(r)
    return out


def _filter_changes(changes: dict | None, in_scope_keys: set, scope: str, show: dict) -> dict | None:
    if not changes:
        return None
    hidden_fields = {f for f, key in (("total_premium", "premium"), ("accumulation", "accumulation")) if not show[key]}

    def keep(entry: dict) -> bool:
        # Change entries carry no product_type — match them to the customer's
        # in-scope products. Unverifiable entries are hidden, not leaked.
        return scope == "all" or (entry.get("product"), entry.get("receiving_company")) in in_scope_keys

    added = _hide_amounts_rows([e for e in changes.get("added") or [] if keep(e)], show)
    removed = _hide_amounts_rows([e for e in changes.get("removed") or [] if keep(e)], show)
    changed = []
    for e in changes.get("changed") or []:
        if not keep(e):
            continue
        diffs = [d for d in e.get("changes") or [] if d.get("field") not in hidden_fields]
        if diffs:
            changed.append({**e, "changes": diffs})
    if not added and not removed and not changed:
        return None
    return {"added": added, "removed": removed, "changed": changed}


def apply_settings(raw_settings: dict | None, dashboard: dict) -> dict:
    """Return the dashboard exactly as this customer may see it."""
    if raw_settings is None:
        out = copy.deepcopy(dashboard)
        out["settings"] = default_settings()
        return out
    s = normalize_settings(raw_settings)
    scope, show = s["product_scope"], s["show_amounts"]

    products = [p for p in dashboard.get("products") or [] if product_in_scope(p.get("product_type"), scope)]
    kpi, breakdown = _kpi_and_breakdown(products)
    in_scope_keys = {(p.get("product"), p.get("receiving_company")) for p in products}

    out = dict(dashboard)
    out["products"] = _hide_amounts_rows(products, show)
    out["kpi"] = _hide_amounts_kpi(kpi, show)
    out["company_breakdown"] = _hide_amounts_rows(breakdown, show, premium_key="premium")
    out["recent_changes"] = (
        _filter_changes(dashboard.get("recent_changes"), in_scope_keys, scope, show)
        if s["sections"]["changes"] else None
    )
    if not s["sections"]["companies"]:
        out["company_breakdown"] = []
    if not s["sections"]["products"]:
        out["products"] = []
    out["settings"] = s
    return out


def apply_to_history(raw_settings: dict | None, snapshots: list[dict], products_by_snapshot: list[list[dict]]) -> list[dict]:
    """Trend points recomputed from each snapshot's own products, so a
    savings-only portal doesn't plot the full book's totals."""
    if raw_settings is None:
        return snapshots
    s = normalize_settings(raw_settings)
    if not s["sections"]["trend"]:
        return []
    out = []
    for snap, products in zip(snapshots, products_by_snapshot):
        scoped = [p for p in products or [] if product_in_scope(p.get("product_type"), s["product_scope"])]
        kpi, _ = _kpi_and_breakdown(scoped)
        out.append({
            **snap,
            "kpi": _hide_amounts_kpi(kpi, s["show_amounts"]),
            # Snapshot diffs are shown by the changes banner (already filtered);
            # don't ship the raw ones alongside the trend.
            "changes_json": None,
            "has_changes": bool(snap.get("has_changes")) and s["sections"]["changes"],
        })
    return out
