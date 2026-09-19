"""Golden regression over the real per-insurer download corpus + the parser
invariants that hold with no corpus at all.

    source backend/venv/bin/activate && python backend/tests/test_parser_corpus_golden.py

No DB, no network. Two halves, and the second always runs:

  PART 1 — GOLDEN NUMBERS. Drives `upload_ingest.parse_any` (the same front door
  `ingest_file_bytes` uses) over the real files under `data/portal_downloads/`,
  `/mnt/c/Users/roygi/Desktop/KIKO/` and `/mnt/c/fnxbox/`, and freezes what each
  one must yield: records, non-null ת"ז, Σpremium, Σaccumulation, Σcommission.
  Skipped (not failed) on a machine without the corpus, e.g. CI or Railway.

  PART 2 — INVARIANTS. Cases reproduced in-memory, so they guard the fixes
  everywhere.

WHY NUMBERS AND NOT "it didn't raise". Every parser bug this repo has shipped was
silent: `fix(mimshak): accumulation dropped every balance component after the
first` changed a sum, not an exit code. A test that only asserts "parses" would
have passed through all of them. Two of the goldens below are deliberately
`None`-vs-`0.0` assertions for the same reason — a parser that fabricates 0.0
where the file has no such column at all is indistinguishable in a sum.
"""

import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from app.services.parser_service import detect_period_month  # noqa: E402
from app.services.upload_ingest import parse_any             # noqa: E402
from app.services import harel_vault_prod as hv              # noqa: E402


# ── PART 1 · golden numbers ──────────────────────────────────────────────────
# name → (format, records, with_id, premium, accumulation, commission)
# Measured 2026-09-13 against the corpus on royg's box. A diff here is either a
# real regression or a genuinely newer download — check which before editing.
GOLDEN: dict[str, tuple] = {
    # production
    "MU_NK_HAYV_MOSHE_2026_06":                          ("production", 261, 261, 0, 1_094_213, 0),
    "הפניקס גמל - פרודוקציה (יוני 2026).xlsx":            ("production", 575, 575, 0, 68_861_103, 0),
    "הפניקס - חיים ובריאות פרודוקציה (יוני 2026).xlsx":   ("production", 141, 141, 2_034_040, 49_073_553, 0),
    "מנורה - חיים פרודוקציה.zip":                         ("production", 80, 80, 286_008, 0, 0),
    "הראל גמל - פרודוקציה (מאי 2026).xlsx":               ("production", 17, 17, 0, 406_028, 0),
    "הראל מגוון - פרודוקציה (מאי 2026).xlsx":             ("production", 7, 7, 0, 6_070_060, 0),
    "migdal_פעילות במעקב.zip":                            ("production", 109, 109, 16_240, 1_705_423, 0),
    # נפרעים
    "הכשרה נפרעים.xlsx":                                  ("hachshara_nifraim", 350, 350, 0, 0, 43_763),
    "מגדל נפרעים מאי 2026.xlsx":                          ("migdal_nifraim", 209, 209, 39_606, 0, 3_235),
    "הראל נפרעים חיים ובריאות.xls":                       ("harel_nifraim", 139, 139, 106_417, 0, 4_723),
    'הפניקס נפרעים חא"ט ובריאות.xlsx':                    ("phoenix_insurance_nifraim", 141, 141, 2_034_040, 0, 6_557),
    "אלטשולר נפרעים גמל.xlsx":                            ("altshuler", 134, 134, 0, 0, 2_094),
    "מיטב דש עמלות לסוכן.xlsx":                           ("meitav_nifraim", 9, 9, 0, 0, 592),
    "ילין לפידות עמלות.xlsx":                             ("yelin_nifraim", 3, 3, 0, 0, 215),
    "כלל עמלות חיים.xlsx":                                ("clal_life_nifraim", 18, 18, 18_433, 0, 1_005),
    "כלל עמלות בריאות.xlsx":                              ("clal_health_nifraim", 24, 24, 5_470, 0, 831),
    "12_2025_נפרעים מור.xlsx":                            ("nifraim", 455, 455, 0, 0, 16_659),
    "דוח עמלות הפניקס ינואר 26 926304.xlsx":              ("company_report", 548, 548, 0, 0, 13_275),
    "קובץ אקסלנס לרועי (1).xlsx":                         ("agent_tracking", 735, 735, 0, 0, 0),
}

# The Harel כספת is a SET, not a file: ת"ז and names exist only on the SP/RP
# masters and are joined onto SB/RB/RM. One vault file parsed alone legitimately
# has zero ת"ז, so the golden is over the joined set.
VAULT_GOLDEN = {"records": 1766, "with_id": 1766}

failures = 0


def _check(label, got, want) -> bool:
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}"
          + ("" if ok else f"  (expected {want!r})"))
    return ok


def _sums(recs):
    def s(col):
        return round(sum(float(r.get(col) or 0) for r in recs))
    return (len(recs), sum(1 for r in recs if r.get("id_number")),
            s("total_premium"), s("accumulation"), s("commission_paid"))


def part1_golden() -> int:
    global failures
    from parse_corpus import build_units, collect_files, parse_unit

    print("PART 1 — golden numbers over the real corpus\n")
    units = build_units(collect_files())
    if not units:
        print("  [SKIP] no corpus on this machine (data/portal_downloads is empty)")
        return 0

    by_name: dict[str, dict] = {}
    for u in units:
        by_name.setdefault(u["name"], u)

    missing = [n for n in GOLDEN if n not in by_name]
    if len(missing) == len(GOLDEN):
        print("  [SKIP] corpus present but holds none of the golden files")
        return 0

    for name, want in GOLDEN.items():
        u = by_name.get(name)
        if u is None:
            print(f"  [SKIP] {name} — not on this machine")
            continue
        # `parse_unit` is the harness's router: `parse_any` for anything with a
        # real extension, plus the two doors ingest does not own — the Phoenix MU
        # book and the Harel vault, which arrive with NO extension at all and
        # emit Hebrew production ROWS that the pipeline writes to an xlsx and
        # re-parses. Measuring the intermediate would measure a shape the DB
        # never sees.
        r = parse_unit(u)
        failures += not _check(name, (r["format"], r["records"], r["with_id"],
                                      round(r["premium"]), round(r["accumulation"]),
                                      round(r["commission"])), want)

    # Vault set — parse together, join identity from the masters, then measure.
    vault_units = [u for u in units if u["kind"] == "harel_vault_set"]
    if vault_units:
        newest = max(vault_units, key=lambda u: u["mtime"])
        parsed = [hv.parse_vault_file(i["path"]) for i in newest["items"]]
        parsed = [x for x in parsed if x is not None]
        hv.fill_identity_from_masters(parsed)
        rows = [r for _cs, _lb, rr in parsed for r in rr]
        failures += not _check("כספת הראל — rows", len(rows), VAULT_GOLDEN["records"])
        failures += not _check("כספת הראל — rows with ת\"ז",
                               sum(1 for r in rows if r["מספר ת.ז"]),
                               VAULT_GOLDEN["with_id"])
        # The vault deliberately ships PRODUCT PRESENCE only: the agents-portal
        # savings leg owns the money and summing both double-counts. `None`, not
        # 0.0 — a fabricated zero is invisible in every sum.
        failures += not _check("כספת הראל — every row's צבירה is None",
                               {r["צבירה"] for r in rows}, {None})
        failures += not _check('כספת הראל — every row\'s פרמיה is None',
                               {r['סה"כ פרמיה'] for r in rows}, {None})

    # The Phoenix MU book and the xlsx the Windows driver derives FROM it must
    # agree. They are the same data down two code paths, so a drift means one of
    # them changed silently.
    mu = by_name.get("MU_NK_HAYV_MOSHE_2026_06")
    derived = by_name.get("הפניקס פרודוקציה 06-2026.xlsx")
    if mu and derived:
        from app.services.phoenix_mu import parse_phoenix_mu, PRODUCTION_COLUMNS
        import pandas as pd
        rows = parse_phoenix_mu(mu["items"][0]["path"].read_bytes())["records"]
        buf = io.BytesIO()
        pd.DataFrame(rows, columns=PRODUCTION_COLUMNS).to_excel(buf, index=False)
        a = _sums(parse_any(buf.getvalue(), "הפניקס MU.xlsx")["records"])
        b = _sums(parse_any(derived["items"][0]["path"].read_bytes(),
                            "הפניקס פרודוקציה 06-2026.xlsx")["records"])
        failures += not _check("MU book == the xlsx derived from it", a, b)
        # phoenix_mu refuses to fabricate a premium — the MU file has no such
        # column. A 0.0 here would mean someone started inventing one.
        failures += not _check("MU premium is absent, not zero",
                               {r['סה"כ פרמיה'] for r in rows}, {None})
    return failures


# ── PART 2 · invariants, no corpus needed ────────────────────────────────────

def _xlsx_bytes() -> bytes:
    import pandas as pd
    buf = io.BytesIO()
    pd.DataFrame({"a": [1]}).to_excel(buf, index=False)
    return buf.getvalue()


def part2_invariants() -> int:
    global failures
    print("\nPART 2 — invariants (no corpus needed)")

    print("\ndetect_period_month — numeric dates in the filename:")
    up = datetime(2026, 7, 1)
    cases = [
        # Menora's נפרעים zip carries a DD-MM-YYYY stamp. `_RE_NUM_MONTH` read
        # the `10-06` prefix as month=10 / year=06 and dated 799 live commission
        # rows to OCTOBER 2006 on every run.
        ("דוח ניפרעים לסוכן__AmalotLife_613_10-06-2026_17-46-01_NS0850.zip", (2026, 6)),
        ("phoenix_production_202606.xlsx", (2026, 6)),      # standalone YYYYMM
        ("Ild_prod_1_09344_30042026.zip", (2026, 4)),       # DDMMYYYY tail
        ("הפניקס גמל מרץ 26.xlsx", (2026, 3)),               # Hebrew month + year
        ("03-26.xlsx", (2026, 3)),                          # MM-YY
        ("12_2025.xlsx", (2025, 12)),                       # MM-YYYY
    ]
    for fn, (y, m) in cases:
        got = detect_period_month(fn, None, uploaded_at=up)
        failures += not _check(fn[:46], (got.year, got.month) if got else None, (y, m))
    # A policy/agency code must never be mistaken for a period.
    for fn in ("הראל נפרעים מגוון 9345.xlsx", "עמלות כלל חיים.xlsx"):
        got = detect_period_month(fn, None, uploaded_at=up)
        failures += not _check(f"{fn} falls back to uploaded_at",
                               (got.year, got.month), (2026, 6))

    print("\nis_vault_file must not claim a REAL spreadsheet:")
    # `_classify` matches on the FILENAME because the Harel vault serves CP862
    # under an .xlsx name. The converse also happens: the agents-portal savings
    # leg writes a genuine xlsx called "הראל מגוון - …", which matches the RM
    # keyword. Sent to the vault parser it CP862-decodes a zip, yields 0 rows,
    # and harel_savings reports "כספת מגוון: 0 שורות" while dropping the file.
    tmp = Path(__file__).parent / "_tmp_מגוון - פרודוקציה (מאי 2026).xlsx"
    try:
        tmp.write_bytes(_xlsx_bytes())
        failures += not _check("real xlsx named מגוון", hv.is_vault_file(tmp), False)
        failures += not _check("  and parse_vault_file declines it",
                               hv.parse_vault_file(tmp), None)
        cp862 = tmp.with_name("הראל מגוון - פרודוקציה.xlsx")
        cp862.write_bytes(("X" * 120 + "\n").encode("cp862"))
        failures += not _check("CP862 content under the same name is still a vault file",
                               hv.is_vault_file(cp862), True)
        cp862.unlink()
    finally:
        tmp.unlink(missing_ok=True)

    print("\nparse_any routes on CONTENT, not the extension:")
    # A Mimshak bundle saved as .xlsx by a portal plugin must still reach the
    # ZIP door, and a non-bundle zip must not pretend to be one.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("nothing.txt", "x" * 600)
    try:
        parse_any(buf.getvalue(), "whatever.zip")
        failures += not _check("unknown ZIP bundle rejected", "no error", "ValueError")
    except ValueError as e:
        failures += not _check("unknown ZIP bundle rejected",
                               "Unsupported ZIP bundle" in str(e), True)
    try:
        parse_any(b"\x00" * 600, "mystery.bin")
        failures += not _check("unknown extension rejected", "no error", "ValueError")
    except ValueError as e:
        failures += not _check("unknown extension rejected",
                               "Unsupported file extension" in str(e), True)
    return failures


def part3_union_is_lossless() -> int:
    """The merged workbook must not lose money on the way in OR out.

    A row carrying BOTH a premium and an accumulation goes onto ONE of the two
    sheets, and the insurer reference layout gives each sheet only one of the two
    money columns — so the other silently became ₪0. ₪1,774,008 of accumulation
    was lost that way in the 06-2026 merge, with nothing raised anywhere; the
    trailing `צבירה` column on מוצרי ביטוח is what recovers it.

    The mirror case is NOT fixed and this test says so out loud: מוצרי חיסכון
    still has no `סה"כ פרמיה`, so a savings-family row's premium is still
    dropped. That is an open money decision (see COLUMNS_SAVINGS_PRODUCTS), not
    an oversight, and the assertion below records the current, lossy truth. When
    the decision is made, this expectation changes WITH it.
    """
    global failures
    from app.services.portal_automation.aggregate import build_unified_workbook_bytes
    print("\nPART 3 — the merged production workbook is lossless")

    recs = [
        # savings-family type WITH a premium — files onto מוצרי חיסכון, whose
        # schema has no premium column, so this row's ₪1,000 is dropped ON
        # PURPOSE until the pension expected-commission question is settled.
        {"id_number": "111111118", "first_name": "א", "last_name": "ב",
         "receiving_company": "הפניקס", "product_type": "פנסיה", "product": "פנסיה מקיפה",
         "fund_policy_number": "5001", "total_premium": 1000.0, "accumulation": 250000.0},
        # pure-risk type carrying a VALUE — files onto מוצרי ביטוח
        {"id_number": "222222226", "first_name": "ג", "last_name": "ד",
         "receiving_company": "הפניקס", "product_type": "חיים", "product": "ריסק",
         "fund_policy_number": "5002", "total_premium": 300.0, "accumulation": 40000.0},
        # plain insurance row
        {"id_number": "333333334", "first_name": "ה", "last_name": "ו",
         "receiving_company": "מנורה", "product_type": "ביטוח בריאות", "product": "בריאות",
         "fund_policy_number": "5003", "total_premium": 55.5, "accumulation": None},
        # plain savings row
        {"id_number": "444444442", "first_name": "ז", "last_name": "ח",
         "receiving_company": "הראל", "product_type": "גמל", "product": "גמל",
         "fund_policy_number": "5004", "total_premium": None, "accumulation": 7000.0},
    ]
    want_a = round(sum(float(r.get("accumulation") or 0) for r in recs), 2)
    # Everything except the פנסיה row, whose premium the savings sheet cannot hold.
    want_p = round(sum(float(r.get("total_premium") or 0) for r in recs
                       if r["product_type"] != "פנסיה"), 2)

    out = parse_any(build_unified_workbook_bytes(recs), "פרודוקציה מאוחד בדיקה.xlsx")
    got = out["records"]
    failures += not _check("re-parses as production", out["format"], "production")
    failures += not _check("every row survives", len(got), len(recs))
    failures += not _check("Σpremium survives, except the documented פנסיה gap",
                           round(sum(float(r.get("total_premium") or 0) for r in got), 2),
                           want_p)
    failures += not _check("Σaccumulation survives the merge",
                           round(sum(float(r.get("accumulation") or 0) for r in got), 2),
                           want_a)
    return failures


def main() -> int:
    part1_golden()
    part2_invariants()
    part3_union_is_lossless()
    print(f"\n{'ALL PASS' if not failures else str(failures) + ' FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
