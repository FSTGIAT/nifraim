"""CONSLT (טרום ייעוץ) holdings parsing — against REAL clearinghouse wire files.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_conslt_parse.py

The fixtures in `fixtures/maslaka/swiftness_samples/` are Swiftness's own publicly
published sample pack (swiftness.co.il, "דוגמאות קבצים ללקוחות"). They are the only
genuine מסלקה wire data we have — everything else under `fixtures/maslaka/` is a stub
we invented. Filenames are left verbatim because the נספח ו' grammar is itself under
test: direction(3) + sender ת.ז/ח.פ(12) + service(6) + product family(3) + version(3)
+ YYYYMMDDHHMMSS + sequence(4).

The claim being locked down: **a מסלקה holdings response is Mimshak, so it parses with
`services/mimshak` — the parser already proven against Migdal and Clal — and
`services/maslaka/adapter.py`'s invented `<Holdings>` schema is not needed.**

Three defects this file exists to prevent regressing, all found on 2026-09-10 by running
these files for the first time:

  1. Every product came back `ביטוח חיים`. `SUG-MUTZAR` lives on `NetuneiMutzar`, one
     level ABOVE the policy, and the leaf collector only walked downward — so the lookup
     missed and the caller fell back to code "1". On top of that `SUG_MUTZAR_LABELS` had
     2 and 3 as ביטוח בריאות/סיעוד when they are really קרן פנסיה and קופת גמל — the
     exact products מור/מיטב/ילין/אנליסט deliver.
  2. The PNN file produced rows with NO id_number. `YeshutLakoach` hangs off
     `NetuneiMutzar`, a SIBLING of the policies — reachable neither downward from the
     policy nor upward from it. Compounded by `_strip_leading_zeros("") == "0"`, which
     made an EMPTY `<MISPAR-ZIHUY/>` look like a real customer "0".
  3. The ING file emitted the same policy twice — the source genuinely repeats the
     product block, identical across all 355 leaves. Emitting both double-counts צבירה.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "maslaka" / "swiftness_samples"
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


# (filename glob, expected rows, expected product_type)
EXPECTED = [
    ("*CONSLTING*.DAT", 1, "ביטוח חיים"),   # SUG-MUTZAR=1, and the duplicate block collapses 2→1
    ("*CONSLTKGM*.DAT", 5, "קופת גמל"),      # SUG-MUTZAR=3 — was mislabelled ביטוח סיעוד
    ("*CONSLTPNN*.DAT", 1, "קרן פנסיה"),     # SUG-MUTZAR=2 — was mislabelled ביטוח בריאות
    ("*CONSLTPNO*.DAT", 6, "קרן פנסיה"),     # ותיקה (PENSIA-VATIKA-O-HADASHA=1)
]


def main() -> None:
    from app.services.mimshak import is_mimshak_dat, parse_mimshak_dat

    print("CONSLT holdings — real Swiftness wire files")
    if not FIXTURES.is_dir():
        print(f"  SKIP — fixtures missing at {FIXTURES}")
        return

    total = 0
    for pattern, want_rows, want_type in EXPECTED:
        matches = sorted(FIXTURES.glob(pattern))
        if not matches:
            check(f"{pattern} present", False, "no fixture")
            continue
        path = matches[0]
        raw = path.read_bytes()

        check(f"{pattern[1:-5]}: recognised as Mimshak", is_mimshak_dat(raw))

        rows = parse_mimshak_dat(raw, path.name).get("records", [])
        total += len(rows)
        check(f"{pattern[1:-5]}: row count", len(rows) == want_rows,
              f"{len(rows)} != {want_rows}")
        check(f"{pattern[1:-5]}: every row has an id_number",
              all(r.get("id_number") for r in rows),
              f"{sum(1 for r in rows if not r.get('id_number'))} missing")
        check(f"{pattern[1:-5]}: no row claims customer '0'",
              not any(str(r.get("id_number")) == "0" for r in rows))
        types = {r.get("product_type") for r in rows}
        check(f"{pattern[1:-5]}: product_type is {want_type}", types == {want_type}, str(types))
        check(f"{pattern[1:-5]}: policy numbers present",
              all(r.get("fund_policy_number") for r in rows))
        check(f"{pattern[1:-5]}: accumulation present",
              all((r.get("accumulation") or 0) > 0 for r in rows))

        # Duplicate product blocks must not double-count money.
        seen = [(r.get("id_number"), r.get("fund_policy_number")) for r in rows]
        check(f"{pattern[1:-5]}: no duplicate (customer, policy)",
              len(seen) == len(set(seen)), str(seen))

    check("all four product families parsed", total == 13, f"total rows {total}")

    # The product-type table itself — the values are from *כללי מערכת ממשק אחזקות 9.0*.
    from app.services.mimshak.column_maps import SUG_MUTZAR_LABELS
    check("SUG_MUTZAR 2 = קרן פנסיה", SUG_MUTZAR_LABELS.get("2") == "קרן פנסיה")
    check("SUG_MUTZAR 3 = קופת גמל", SUG_MUTZAR_LABELS.get("3") == "קופת גמל")
    check("SUG_MUTZAR 4 = קרן השתלמות", SUG_MUTZAR_LABELS.get("4") == "קרן השתלמות")
    check("SUG_MUTZAR 9 = קופת גמל להשקעה", SUG_MUTZAR_LABELS.get("9") == "קופת גמל להשקעה")
    # Deliberately NOT renamed: this exact string is a key in
    # xlsx_writer._PRODUCT_CATEGORY_BY_SUG and flows into stored product labels.
    check("SUG_MUTZAR 1 label unchanged (downstream key)",
          SUG_MUTZAR_LABELS.get("1") == "ביטוח חיים")

    # REGRESSION (2026-09-10): accumulation came from the FLATTENED policy dict,
    # which is first-value-wins. Migdal splits a policy's balance into one
    # PerutYitrot per KOD-SUG-HAFRASHA (פיצויים / מעסיק / עובד), each carrying its
    # own TOTAL-CHISACHON-MTZBR — so policy 23282652 reported 7,172 instead of
    # 27,731 (74% low) and 0604502013 reported 459,782 instead of 1,238,482.
    # Where the file also carries per-track SCHUM-TZVIRA-BAMASLUL, the SUM matches
    # it exactly and the first value does not; that independent figure is the
    # assertion here, which is what makes this verifiable rather than plausible.
    import xml.etree.ElementTree as ET
    from app.services.mimshak.xlsx_writer import policy_accumulation_from_element

    def _lt(t: str) -> str:
        return t.rsplit("}", 1)[-1] if "}" in t else t

    print("\nAccumulation sums ALL component blocks, not just the first:")
    for f in sorted(FIXTURES.glob("*CONSLT*")):
        root = ET.parse(f).getroot()
        seen: set[str] = set()
        for pol in [e for e in root.iter() if _lt(e.tag) == "HeshbonOPolisa"]:
            pid = next((e.text for e in pol.iter()
                        if _lt(e.tag) == "MISPAR-POLISA-O-HESHBON"), None)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            tracks = [float(e.text) for e in pol.iter()
                      if _lt(e.tag) == "SCHUM-TZVIRA-BAMASLUL" and (e.text or "").strip()]
            if not tracks:
                continue            # no independent figure to check against
            got = policy_accumulation_from_element(pol)
            check(f"policy {pid} accumulation matches its track total",
                  abs(got - sum(tracks)) < 2, f"{got:,.0f} vs {sum(tracks):,.0f}")

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
