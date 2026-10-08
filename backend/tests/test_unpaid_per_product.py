"""'לא שולמו' is judged PER PRODUCT and never by status (QA 2026-10-08).

Anything that received no commission is unpaid — even ₪1, even an inactive fund,
even when the same company paid the customer's other products. Only value
excludes a product (an empty fund), plus Mor pension: Mor pays no pension נפרעים.
"""
from types import SimpleNamespace

from app.services.comparison_service import compute_comparison
from app.services.rate_select import select_rate

HAREL_GEMEL = 'הראל פנסיה וגמל בע"מ'
HAREL_INS = 'הראל חברה לביטוח בע"מ'
MOR = 'מור גמל ופנסיה בע"מ'


def _prod(idn, pol, co, product, ptype, acc=0, prem=None, status="פעיל"):
    return {"id_number": idn, "fund_policy_number": pol, "receiving_company": co, "product": product,
            "product_type": ptype, "accumulation": acc, "total_premium": prem, "product_status": status}


def _comm(idn, pol, co, product, amount):
    return {"id_number": idn, "fund_policy_number": pol, "receiving_company": co,
            "product": product, "commission_paid": amount}


def _cust(res, idn):
    return next(c for c in res["customers"] if c["id_number"] == idn)


def _unpaid_policies(c):
    return sorted(p["policy_number"] for p in c["production_products"]) if c["match_status"] == "only_production" else []


def test_zero_paid_line_is_unpaid():
    # שרה אשר: a matching נפרעים line that paid ₪0 is not "paid".
    prod = [_prod("69315737", "102647604", HAREL_INS, "הראל - מנהלים", "ביטוח מנהלים", acc=33208)]
    comm = [_comm("69315737", "102647604", HAREL_GEMEL, "מגוון", 0)]
    assert _unpaid_policies(_cust(compute_comparison(prod, comm), "69315737")) == ["102647604"]


def test_paid_product_at_same_company_does_not_hide_an_unpaid_one():
    # רונן חיראק: Harel paid his מנהלים; his inactive Harel gemel got nothing.
    prod = [_prod("22297535", "222975301", HAREL_INS, "הראל - מנהלים", "ביטוח מנהלים", acc=1385678),
            _prod("22297535", "38559091", HAREL_GEMEL, "הראל קופת גמל", "קופת גמל לתגמולים ופיצויים",
                  acc=210047, status="לא פעיל")]
    comm = [_comm("22297535", "222975301", HAREL_GEMEL, "מנהלים", 123.06)]
    c = _cust(compute_comparison(prod, comm), "22297535")
    assert _unpaid_policies(c) == ["38559091"]
    assert c["partially_paid"] and [p["policy_number"] for p in c["paid_production_products"]] == ["222975301"]


def test_paid_line_stays_paid():
    prod = [_prod("1", "5", HAREL_GEMEL, "הראל גמל להשקעה", "קופת גמל להשקעה", acc=1000)]
    comm = [_comm("1", "5", HAREL_GEMEL, "גמל להשקעה", 0.5)]
    assert _cust(compute_comparison(prod, comm), "1")["match_status"] == "matched"


def test_empty_fund_is_not_unpaid():
    prod = [_prod("2", "6", HAREL_GEMEL, "הראל השתלמות", "קרן השתלמות", acc=0),
            _prod("2", "7", HAREL_GEMEL, "הראל השתלמות", "קרן השתלמות", acc=500)]
    comm = [_comm("2", "7", HAREL_GEMEL, "קרן השתלמות", 1.0), _comm("9", "8", HAREL_GEMEL, "x", 1.0)]
    assert _cust(compute_comparison(prod, comm), "2")["match_status"] == "matched"


def test_inactive_pension_with_balance_is_unpaid_but_mor_pension_is_not():
    # Pension policy = the member's ID; paid when the company sent money on a pension line.
    prod = [_prod("3", "3", HAREL_GEMEL, "הראל פנסיה מקיפה", "קרן פנסיה חדשה מקיפה", acc=90000, status="לא פעיל"),
            _prod("3", "3", MOR, "מור פנסיה מקיפה", "קרן פנסיה חדשה מקיפה", acc=300000),
            _prod("3", "11", MOR, "מור השתלמות", "קרן השתלמות", acc=5000)]
    comm = [_comm("3", "11", MOR, "מור השתלמות", 2.0),
            _comm("9", "9", HAREL_GEMEL, "פנסיה", 4.0)]
    c = _cust(compute_comparison(prod, comm), "3")
    assert c["match_status"] == "only_production"
    assert [p["product"] for p in c["production_products"]] == ["הראל פנסיה מקיפה"]


def test_pension_paid_by_family_line():
    prod = [_prod("4", "4", HAREL_GEMEL, "הראל פנסיה מקיפה", "קרן פנסיה חדשה מקיפה", acc=90000)]
    comm = [_comm("4", "34601815", HAREL_GEMEL, "פנסיה", 12.0)]
    assert _cust(compute_comparison(prod, comm), "4")["match_status"] == "matched"


def _rate(co, product, rate, doc):
    return SimpleNamespace(company_name=co, product=product, rate=rate, rate_kind="single",
                           effective_from=None, effective_to=None, source_document_id=doc)


def test_orphan_pension_line_does_not_price_pension():
    rates = [_rate(MOR, "קופות גמל (לחיסכון, להשקעה, קרן השתלמות)", 0.0024, "doc"),
             _rate(MOR, "קופות גמל / פנסיה — עמלת נפרעים (שוטפת)", 0.0024, None)]
    rate, route = select_rate(rates, MOR, "מור פנסיה מקיפה", "קרן פנסיה חדשה מקיפה", False)
    assert rate == 0 and route.endswith(":no_pension_line")
    # an agreement-backed pension line still prices it
    rates.append(_rate("מנורה מבטחים", "פנסיה מקיפה, פנסית חובה ופנסיה משלימה", 0.004, "doc"))
    rate, _ = select_rate(rates, "מנורה מבטחים", "מבטחים החדשה", "קרן פנסיה חדשה מקיפה", False)
    assert rate == 0.004


def test_hand_built_shelf_still_prices_pension():
    rates = [_rate("אלטשולר", "פנסיה", 0.003, None), _rate("אלטשולר", "גמל", 0.0025, None)]
    rate, _ = select_rate(rates, "אלטשולר", "אלטשולר שחם פנסיה מקיפה", "קרן פנסיה חדשה מקיפה", False)
    assert rate == 0.003


if __name__ == "__main__":
    import sys
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
