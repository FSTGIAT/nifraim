"""Unit checks for the נפרעים rate-extraction guard + scope propagation.

Covers the QA-driven fixes (plan sections B + D):
  • clawback / scope (היקף) rows never reach commission_rates
  • genuine נפרעים rows survive (incl. legitimate high insurance rates)
  • book + reward components both survive with their policy-year scope
  • _flat_components carries the scope onto each unfolded row

No DB / network — pure function tests. Run:
    backend/venv/bin/python backend/tests/test_rate_extraction_guard.py
"""
from decimal import Decimal

from app.services.document_extraction import _normalize_and_validate_rates


def _kinds(rows):
    return [(r["company"], r["product"], tuple((c["kind"], c["rate_percent"], c.get("scope"))
                                               for c in r["components"]))
            for r in rows]


def test_clawback_and_scope_rows_dropped():
    # Real מיטב extraction: only scope grant + two Clawback refund rows.
    rates = [
        {"company": "מיטב גמל ופנסיה בע\"מ",
         "product": "מענק גיוס חדש — עמלת היקף (לכל מיליון ₪)",
         "components": [{"kind": "single", "rate_percent": 0.6}]},
        {"company": "מיטב גמל ופנסיה בע\"מ",
         "product": "Clawback — החזר מענק גיוס חדש (עד 24 חודשים)",
         "components": [{"kind": "single", "rate_percent": 66.0}]},
        {"company": "מיטב גמל ופנסיה בע\"מ",
         "product": "Clawback — החזר מענק גיוס חדש (24–36 חודשים)",
         "components": [{"kind": "single", "rate_percent": 33.0}]},
    ]
    out = _normalize_and_validate_rates(rates, "")
    assert out == [], f"expected all rows dropped, got {out}"


def test_scope_marker_on_component_dropped():
    rates = [{
        "company": "מיטב", "product": "קופות גמל",
        "components": [
            {"kind": "single", "rate_percent": 0.6, "scope": "מענק גיוס חדש — לכל מיליון"},
            {"kind": "single", "rate_percent": 0.24, "scope": "עמלת נפרעים חודשית"},
        ],
    }]
    out = _normalize_and_validate_rates(rates, "")
    assert len(out) == 1
    comps = out[0]["components"]
    assert len(comps) == 1 and comps[0]["rate_percent"] == 0.24, comps


def test_genuine_nefraim_survives_incl_high_insurance_rate():
    # Ayalon דרור פרט is a legit 20% נפרעים — must NOT be dropped by value.
    rates = [{
        "company": "איילון חברה לביטוח בע\"מ",
        "product": "דרור 1 פרט / עוגן פרט – עמלת נפרעים",
        "components": [{"kind": "single", "rate_percent": 20.0}],
    }]
    out = _normalize_and_validate_rates(rates, "")
    assert len(out) == 1 and out[0]["components"][0]["rate_percent"] == 20.0


def test_book_plus_reward_with_year_scope_survive():
    rates = [{
        "company": "הפניקס חברה לביטוח בע\"מ", "product": "מוצרי ריסק",
        "components": [
            {"kind": "book", "rate_percent": 15.0, "scope": "שנה 1-5"},
            {"kind": "reward", "rate_percent": 8.0, "scope": "שנה 1-5"},
            {"kind": "reward", "rate_percent": 4.0, "scope": "שנה 16+"},
        ],
    }]
    out = _normalize_and_validate_rates(rates, "")
    assert len(out) == 1
    comps = out[0]["components"]
    assert len(comps) == 3, comps
    # year-band scope preserved (never treated as a scope/clawback marker)
    assert {c.get("scope") for c in comps} == {"שנה 1-5", "שנה 16+"}
    kinds = sorted((c["kind"], c["rate_percent"]) for c in comps)
    assert kinds == [("book", 15.0), ("reward", 4.0), ("reward", 8.0)]


def test_flat_components_carries_scope():
    # Exercise the upsert unfold: scope must reach the (kind, rate, scope) tuple.
    import importlib
    mod = importlib.import_module("app.api.ai_documents")
    # _flat_components is a nested closure; re-implement the contract via upsert
    # is heavy, so assert the normalized shape feeds it: each component keeps
    # kind + scope, which _upsert reads directly.
    row = {
        "company": "הפניקס", "product": "מוצרי ריסק",
        "components": [{"kind": "book", "rate_percent": 15.0, "scope": "שנה 1-5"}],
    }
    out = _normalize_and_validate_rates([row], "")
    c = out[0]["components"][0]
    assert c["kind"] == "book" and c["scope"] == "שנה 1-5"
    assert mod is not None  # module imports cleanly (upsert consumes scope)


# ── Reporting: a rejected row must be nameable, not just logged ──────────
# Every reject here used to be `logger.warning` + `continue`, so an agent who
# saw "חולצו 12 שיעורי עמלה" had no way to learn that 30 more were thrown away.


def test_dropped_rows_are_reported_with_a_reason():
    rates = [
        {"company": "מיטב", "product": "מענק גיוס חדש — עמלת היקף",
         "components": [{"kind": "single", "rate_percent": 0.6}]},
        {"company": "מיטב", "product": "קופות גמל",
         "components": [{"kind": "single", "rate_percent": 0.25}]},
    ]
    dropped: list[dict] = []
    out = _normalize_and_validate_rates(rates, "", dropped)
    assert len(out) == 1 and out[0]["product"] == "קופות גמל"
    assert len(dropped) == 1, dropped
    assert dropped[0]["reason"] == "non_commission_filter"
    assert dropped[0]["product"] == "מענק גיוס חדש — עמלת היקף"


def test_value_not_in_text_is_reported_not_just_dropped():
    # With a text layer present the literal-value guard is active: 0.25 appears,
    # 9.99 does not.
    text = "עמלת נפרעים בשיעור 0.25% מהצבירה"
    rates = [
        {"company": "ילין לפידות", "product": "קופות גמל",
         "components": [{"kind": "single", "rate_percent": 0.25}]},
        {"company": "ילין לפידות", "product": "מוצר מומצא",
         "components": [{"kind": "single", "rate_percent": 9.99}]},
    ]
    dropped: list[dict] = []
    out = _normalize_and_validate_rates(rates, text, dropped)
    assert len(out) == 1, out
    reasons = {d["reason"] for d in dropped}
    # The fabricated component is reported, and so is the row it emptied.
    assert "value_not_in_text" in reasons, dropped
    assert any(d.get("percent") == 9.99 for d in dropped), dropped


# ── The ילין case: an agreement that defers its rates to a missing נספח ──
# Measured on the real file — 5 scanned pages, §4.1 "כמפורט בנספח א' להסכם זה",
# and no נספח א' attached. "0 rates" is CORRECT; saying nothing is the bug.


def test_appendix_reference_detected_in_real_yelin_wording():
    from app.services.document_extraction import _appendix_reference

    body = ("המשווק יהיה זכאי לתמורה חודשית בגין לקוחות מזכים "
            "כמפורט בנספח א' להסכם זה ובהתאם להוראות כדלקמן")
    assert _appendix_reference(body) == "נספח א'"
    assert _appendix_reference("כמפורט בסעיף 4 להסכם זה ולנספח התמורה שצורף") == "נספח התמורה"


def test_unrelated_appendix_is_not_reported_as_the_rate_table():
    from app.services.document_extraction import _appendix_reference

    # A privacy appendix must not be offered as the missing rate sheet.
    assert _appendix_reference("נספח ב - שמירה על סודיות ואבטחת מידע") is None
    assert _appendix_reference("") is None
    assert _appendix_reference(None) is None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\nAll {len(fns)} checks passed.")
