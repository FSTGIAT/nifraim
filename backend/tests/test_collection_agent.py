"""collection_agent.unpaid_by_company — who didn't pay, per insurer (pure)."""
from datetime import datetime, timedelta

from app.models.collection_case import CollectionCase
from app.services.collection_agent import suggestion, unpaid_by_company


def _cust(idn, status, products, name=("דנה", "כהן")):
    return {"id_number": idn, "first_name": name[0], "last_name": name[1],
            "match_status": status, "production_products": products}


def _prod(company, policy, expected=100.0, status="פעיל", product="גמל"):
    return {"company": company, "policy_number": policy, "expected_commission": expected,
            "status": status, "product": product}


RESULT = {
    "commission_company_sources": ["מנורה", "הפניקס"],
    "customers": [
        _cust("1", "only_production", [_prod("מנורה", "A1", 50, product="עדיף"),           # two coverages, one policy
                                       _prod("מנורה", "A1", 25, product="נכות תאונתית")]),
        _cust("2", "only_production", [_prod("מנורה", "A2", 10, status="מבוטל")]),          # cancelled → skip
        _cust("6", "only_production", [_prod("הפניקס", "P3", 10, status="לא פעיל")]),       # inactive → still claimed (QA 2026-10-08)
        _cust("3", "only_production", [_prod("הראל", "H1", 99)]),                           # no נפרעים from הראל → no data
        _cust("4", "matched", [_prod("הפניקס", "P1", 70)]),                                   # paid → skip
        _cust("5", "only_production", [_prod("הפניקס", "P2", 30)]),
    ],
}


def test_groups_only_unpaid_from_reporting_insurers():
    g = unpaid_by_company(RESULT)
    assert set(g) == {"מנורה", "הפניקס"}  # company_stem keys; הראל excluded (no נפרעים at all)


def test_one_line_per_customer_policy_and_expected_summed():
    g = unpaid_by_company(RESULT)["מנורה"]
    assert g["customers"] == 1 and len(g["items"]) == 1
    assert g["items"][0]["expected"] == 75 and g["expected"] == 75


def test_same_coverage_reported_twice_counts_once():
    """Live מנורה (2026-10-02): one policy in two snapshots, premiums ×1.0116 apart —
    the case total was double the dashboard gap (₪56,281 vs ₪28,252)."""
    res = {"commission_company_sources": ["מנורה"], "customers": [
        _cust("1", "only_production", [_prod("מנורה", "A1", 1835.54, product="חיים"),
                                       _prod("מנורה", "A1", 1814.56, product="חיים")])]}
    g = unpaid_by_company(res)["מנורה"]
    assert len(g["items"]) == 1 and g["expected"] == 1814.56 and g["items"][0]["expected"] == 1814.56


def test_cancelled_not_claimed_but_inactive_is():
    g = unpaid_by_company(RESULT)
    assert "2" not in {it["id_number"] for it in g["מנורה"]["items"]}
    assert "6" in {it["id_number"] for it in g["הפניקס"]["items"]}


def test_suggestion_ladder():
    now = datetime(2026, 9, 29)
    c = CollectionCase(company_name="מנורה", status="draft", to_email=None, reminder_count=0)
    assert suggestion(c, now)["kind"] == "contact"
    c.to_email = "a@b.co"
    assert suggestion(c, now)["kind"] == "approve"
    c.status, c.sent_at = "sent", now - timedelta(days=2)
    assert suggestion(c, now)["kind"] == "wait"
    c.sent_at = now - timedelta(days=8)
    assert suggestion(c, now)["kind"] == "remind"
    c.status, c.reply_summary = "replied", "ישולם עד סוף החודש"
    assert suggestion(c, now) == {"kind": "read", "text": "ישולם עד סוף החודש"}
