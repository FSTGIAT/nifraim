"""Harel safe-vault production parser regression test.

    source backend/venv/bin/activate && python backend/tests/test_harel_vault_parser.py

No DB, no network. Runs against `tests/fixtures/harel_vault/` — a SYNTHETIC
bundle built at the real byte layout, so it contains no customer data.

⚠️  DO NOT re-derive the field offsets from this fixture. It was written FROM the
offsets, so it can only ever agree with them. The offsets come from kiko's real
July-2026 vault files (QA 2026-09-06), where the Israeli check digit separates
the ת"ז field from the policy field beyond doubt:

    file                     lines  policy   ת"ז       ת"ז valid    policy-as-ת"ז
    SP  חיים פוליסות            65   [6:15]   [25:34]    64/65        2/65
    RP  בריאות פוליסות         229   [6:15]   [25:34]   228/229      19/229
    SB  חיים ביטוחים           107   [6:15]   — none —   (SP by policy, 107/107)
    RB  בריאות ביטוחים        1354   [6:15]   [70:79]  1353/1354    146/1354
    RM  פוליסות מגוון           28   [0:9]    — none —   (SP by policy,  26/28)

That exact confusion is the bug this file guards: the parser used to reuse
`hachshara_prod._SP_ID = slice(6, 15)`, so every row's `מספר ת.ז` held a POLICY
number and `מס' חשבון/פוליסה` was hardcoded empty. Live symptom: 1,240 הראל rows
in `פרודוקציה מאוחד` with a 0/1,240 policy column, and "גלעד בארי" filed under
103340379 (his policy) instead of 031400617 (his ת"ז).

The three checks that matter, because each fails *silently* with plausible data:

  1. ת"ז and policy land in the right columns, per family.
  2. SB/RM carry NO ת"ז of their own — theirs is joined from SP BY POLICY. A
     naive slice swap leaves those rows with no id and no name.
     RB does carry its own ת"ז; reading [70:79] on SB instead returns junk that
     even passes the check digit 16/106 of the time, so a shape test is not enough.
  3. No row carries accumulation — the agents-portal savings leg owns the money,
     and shipping both double-counts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import harel_vault_prod as hv  # noqa: E402

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "harel_vault"
FILES = ["SP0000001", "RP0000001", "SB0000001", "RB0000001", "RM00000.07R"]

# Offsets the parser must be using. Asserted directly so a drift is named, not
# just felt through a row count.
EXPECTED_OFFSETS = {
    "_H_POLICY": (6, 15),
    "_H_RM_POLICY": (0, 9),
    "_H_TZ_MASTER": (25, 34),
    "_H_TZ_RB": (70, 79),
}

TZ = "מספר ת.ז"
POLICY = "מס' חשבון/פוליסה"
FIRST = "שם פרטי לקוח"
LAST = "שם משפחה לקוח"


def _check(label, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f" (want {want!r})"))
    return ok


def main() -> int:
    failures = 0

    print("field offsets:")
    for name, (start, stop) in EXPECTED_OFFSETS.items():
        sl = getattr(hv, name)
        failures += not _check(name, (sl.start, sl.stop), (start, stop))

    # `harel_savings`'s vault fold still calls the old name. If a tidy-up ever
    # drops the alias, every SB/RM row ships with no ת"ז and no name — silently.
    failures += not _check("legacy alias fill_names_from_masters intact",
                           hv.fill_names_from_masters is hv.fill_identity_from_masters,
                           True)

    parsed = [hv.parse_vault_file(FIXTURE_DIR / f) for f in FILES]
    if any(p is None for p in parsed):
        print("  [FAIL] a fixture file was not classified")
        return 1

    print("\nbefore the identity join — SB/RM must have NO ת\"ז of their own:")
    by_prefix = dict(zip(["SP", "RP", "SB", "RB", "RM"], parsed))
    for prefix in ("SB", "RM"):
        rows = by_prefix[prefix][2]
        failures += not _check(f"{prefix} rows with ת\"ז", sum(1 for r in rows if r[TZ]), 0)
    failures += not _check("RB rows with their own ת\"ז",
                           sum(1 for r in by_prefix["RB"][2] if r[TZ]), 3)

    hv.fill_identity_from_masters(parsed)
    rows = [r for _cs, _lbl, rs in parsed for r in rs]

    print("\nafter the identity join:")
    failures += not _check("total rows", len(rows), 14)
    failures += not _check("rows with a policy", sum(1 for r in rows if r[POLICY]), 14)
    # One RM row points at a policy the SP master does not list — kept, id-less.
    failures += not _check("rows with a ת\"ז", sum(1 for r in rows if r[TZ]), 13)
    failures += not _check("named rows", sum(1 for r in rows if r[FIRST] or r[LAST]), 13)
    failures += not _check("rows carrying accumulation",
                           sum(1 for r in rows if r["צבירה"]), 0)

    print("\nSB joins its identity from the SP master BY POLICY:")
    sp_first = by_prefix["SP"][2][0]
    sb_same_policy = [r for r in by_prefix["SB"][2] if r[POLICY] == sp_first[POLICY]]
    failures += not _check("SB rows on that policy", len(sb_same_policy), 2)
    for r in sb_same_policy:
        failures += not _check("  ת\"ז stamped from SP", r[TZ], sp_first[TZ])
        failures += not _check("  name stamped from SP", (r[FIRST], r[LAST]),
                               (sp_first[FIRST], sp_first[LAST]))

    print("\nRB keeps its OWN ת\"ז and takes only the name from RP:")
    rp_rows = {r[TZ]: r for r in by_prefix["RP"][2]}
    for r in by_prefix["RB"][2]:
        want = rp_rows.get(r[TZ])
        failures += not _check(f"  RB ת\"ז {r[TZ]} exists in RP", want is not None, True)
        if want:
            failures += not _check("  name from RP", (r[FIRST], r[LAST]),
                                   (want[FIRST], want[LAST]))
    # Two insureds share one RB policy — they must stay two rows, not collapse.
    shared = [r for r in by_prefix["RB"][2] if r[POLICY] == by_prefix["RB"][2][0][POLICY]]
    failures += not _check("two insureds on one policy stay distinct",
                           len({r[TZ] for r in shared}), 2)

    print("\nRM row whose policy is absent from SP:")
    orphan = [r for r in by_prefix["RM"][2] if not r[TZ]]
    failures += not _check("orphan kept, id-less", len(orphan), 1)
    failures += not _check("orphan keeps its policy", bool(orphan and orphan[0][POLICY]), True)

    print(f"\n{'ALL PASS' if not failures else str(failures) + ' FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
