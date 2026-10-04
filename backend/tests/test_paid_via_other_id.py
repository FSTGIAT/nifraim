"""Rule B: a policy paid under its owner's ID counts as paid for the insured member — once."""
from app.services.comparison_service import compute_comparison

CO = 'הראל חברה לביטוח בע"מ'


def _prod(idn, pol, product="הראל בריאות", acc=0):
    return {"id_number": idn, "fund_policy_number": pol, "receiving_company": CO,
            "product": product, "product_type": "בריאות", "accumulation": acc, "total_premium": 100}


def _comm(idn, pol, amount):
    return {"id_number": idn, "fund_policy_number": pol, "receiving_company": CO,
            "product": "בריאות", "commission_paid": amount}


def _by_id(res):
    return {c["id_number"]: c for c in res["customers"]}


def test_member_paid_via_owner_counted_once():
    prod = [_prod("27854579", "899704258"), _prod("206270985", "899704258")]
    comm = [_comm("27854579", "899704258", 62.34)]
    res = compute_comparison(prod, comm)
    member = _by_id(res)["206270985"]
    assert member["match_status"] == "matched"
    assert member["unpaid_count"] == 0 and member["paid_count"] == 1
    via = member["paid_via"][0]
    assert via["paid_via_id"] == "27854579" and via["commission"] == 0 and via["owner_commission"] == 62.34
    # the money is still counted once — on the owner
    total = sum(c.get("total_commission") or 0 for c in res["customers"])
    assert round(float(total), 2) == 62.34


def test_other_company_or_policy_does_not_count():
    prod = [_prod("206270985", "899704258")]
    comm = [_comm("27854579", "899704259", 10.0),                                   # different policy
            {**_comm("27854579", "899704258", 10.0), "receiving_company": "מגדל חברה לביטוח בע\"מ"}]  # other company
    member = _by_id(compute_comparison(prod, comm))["206270985"]
    assert member["match_status"] == "only_production" and member["paid_via"] == []


def test_partly_paid_via_owner_stays_unpaid_for_the_rest():
    prod = [_prod("206270985", "899704258"), _prod("206270985", "111111111", "הראל חיים")]
    comm = [_comm("27854579", "899704258", 5.0)]
    member = _by_id(compute_comparison(prod, comm))["206270985"]
    assert member["match_status"] == "only_production" and member.get("partially_paid")
    assert [p["policy_number"] for p in member["production_products"]] == ["111111111"]
    assert [p["policy_number"] for p in member["paid_production_products"]] == ["899704258"]
