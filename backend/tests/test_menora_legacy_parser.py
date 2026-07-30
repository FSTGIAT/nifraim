"""Menora legacy (כספות .ARJ) production parser — regression tests.

Pure unit tests: no DB, no network, no binary fixture. Every row is built in
memory from the reference line documented in `menora_legacy._parse_p_line`.

Run:  python backend/tests/test_menora_legacy_parser.py

Pins three hard-won corrections, each of which was a silent data bug in
production:

  1. policy number lives at [2:11] (9-wide, zero-padded), NOT [4:11]
     — QA 2026-07 "מספר הפוליסה מופיעה בלי שני המספרים הראשונים"
  2. ת"ז block is [38:48], NOT [38:47]  — QA 2026-07-23 "missing the last digit"
  3. first/last name are NOT inverted   — the whole-field reverse already undoes
     Menora's surname-first visual ordering
"""

from __future__ import annotations

import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.menora_legacy import (  # noqa: E402
    _parse_inner_bundle,
    _parse_p_line,
    _policy_from_p_line,
    is_menora_legacy_zip,
    parse_menora_legacy_zip,
)

failures: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  ok   {label}: {got!r}")
    else:
        print(f"  FAIL {label}: got {got!r}, want {want!r}")
        failures.append(label)


# ─────────────────────────────────────────────────────────────────────────────
# Row builders — mirror the documented P.TXT / G.TXT layouts
# ─────────────────────────────────────────────────────────────────────────────

# "סיגלית כוכבי מליחי" as CP862 stores it: visual (display) order, i.e. reversed.
NAME_VISUAL = "יחילמ יבכוכ תילגיס"


def p_line(
    *,
    policy_field: str = "361004450",   # [2:11] — 9 wide, zero-padded
    prefix: str = "06",                # [0:2]  — constant marker, NOT validated
    id_block: str = "0022389456",      # [38:48]
    dob: str = "19680121",             # [48:56]
    name_visual: str = NAME_VISUAL,    # [56:78]
) -> str:
    line = prefix + policy_field          # [0:11]
    line += "4" + "008"                   # [11] constant, [12:15]
    line = line.ljust(38, "0")            # filler through [37]
    line += id_block + dob
    line += name_visual.ljust(22)
    return line.ljust(80)                 # >60 so _parse_inner_bundle keeps it


def g_line(*, policy_field: str = "361004450", prefix: str = "06",
           annual: str = "0000002739.96") -> str:
    """G.TXT row: premium at [150:163]. `_parse_g_line` needs len >= 163."""
    line = (prefix + policy_field).ljust(150, "0")
    return line + annual


def inner_zip(p_rows: list[str], g_rows: list[str]) -> bytes:
    """One Menora bundle: a ZIP holding the fixed-width P/G .TXT members."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("061301P.TXT", "\r\n".join(p_rows).encode("cp862"))
        z.writestr("061301G.TXT", "\r\n".join(g_rows).encode("cp862"))
    return buf.getvalue()


def bundle_zip(p_rows: list[str], g_rows: list[str]) -> bytes:
    """Outer ZIP → inner ZIP named .ARJ (Menora misnames them) → P/G .TXT."""
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as z:
        z.writestr("חיים פרודוקציה ישן פרט-MP00000061301-10_06_2026-07_41_51.ARJ",
                   inner_zip(p_rows, g_rows))
    return outer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────

print("\n1. The anchor row (the reference line in _parse_p_line's docstring)")
rec = _parse_p_line(p_line())
check("fund_policy_number", rec["fund_policy_number"], "361004450")  # pre-fix: "1004450"
check("id_number", rec["id_number"], "22389456")                     # pins the [38:48] fix
check("first_name", rec["first_name"], "סיגלית")                     # pins the swap fix
check("last_name", rec["last_name"], "כוכבי מליחי")                  # two-word surname kept whole
check("receiving_company", rec["receiving_company"], "מנורה")

print("\n2. lstrip is load-bearing — a shorter policy in the same 9-wide field")
# Real row from a live bundle: [2:11] == '011738333'; the נפרעים report says 11738333.
check("zero-padded policy", _policy_from_p_line(p_line(policy_field="011738333")), "11738333")
check("all-zero field falls back", _policy_from_p_line(p_line(policy_field="000000000")), "000000000")

print("\n3. [0:2] is NOT validated — a different marker must still parse")
# Guarding on '06' would silently null a VALID policy on any bundle that differs.
check("non-06 prefix still yields the policy",
      _parse_p_line(p_line(prefix="07"))["fund_policy_number"], "361004450")

print("\n4. Guard: reject rather than truncate")
bad = _parse_p_line(p_line(policy_field="36100445X"))
check("non-digit field → policy None", bad["fund_policy_number"], None)
check("...but the row survives with its ת\"ז", bad["id_number"], "22389456")
check("short line → no record", _parse_p_line("0636100"), None)
# The whole point: the guard must never hand back the old 7-char slice.
for case in ("36100445X", "011738333", "361004450"):
    got = _policy_from_p_line(p_line(policy_field=case))
    if got is not None and len(got) == 7 and got == p_line(policy_field=case)[4:11]:
        failures.append(f"guard returned the legacy [4:11] slice for {case}")
print("  ok   guard never returns the legacy [4:11] slice")

print("\n5. Premium join — wide key (G shares P's layout)")
recs = _parse_inner_bundle(
    zipfile.ZipFile(io.BytesIO(inner_zip([p_line()], [g_line()]))), source_name="wide")
check("rows", len(recs), 1)
check("total_premium via wide key", recs[0]["total_premium"], 2739.96)

print("\n6. Premium join — narrow fallback (G's layout differs)")
# [2:11] is non-digit so the wide key can't form; only [4:11] agrees. This is the
# no-regression path — deleting it would silently drop every premium on a bundle
# whose G.TXT is laid out differently from P.TXT.
narrow_g = g_line(prefix="06", policy_field="AB1004450")
recs = _parse_inner_bundle(
    zipfile.ZipFile(io.BytesIO(inner_zip([p_line()], [narrow_g]))), source_name="narrow")
check("total_premium via narrow fallback", recs[0]["total_premium"], 2739.96)

print("\n7. Two policies sharing a 7-digit suffix both survive dedup")
# Under the old 7-char key these collapsed to one row (and could cross-attach
# premiums, since the G index is last-write-wins).
zb = bundle_zip(
    [p_line(policy_field="361004450"), p_line(policy_field="351004450")],
    [g_line(policy_field="361004450", annual="0000002739.96"),
     g_line(policy_field="351004450", annual="0000001111.11")],
)
res = parse_menora_legacy_zip(zb)
check("is_menora_legacy_zip", is_menora_legacy_zip(zb), True)
check("both policies kept", sorted(r["fund_policy_number"] for r in res["records"]),
      ["351004450", "361004450"])
by_pol = {r["fund_policy_number"]: r["total_premium"] for r in res["records"]}
check("premium not cross-attached (36…)", by_pol["361004450"], 2739.96)
check("premium not cross-attached (35…)", by_pol["351004450"], 1111.11)

print("\n8. מבוטלות (cancelled) bundles are still excluded")
inner = io.BytesIO()
with zipfile.ZipFile(inner, "w") as z:
    z.writestr("061301P.TXT", p_line().encode("cp862"))
outer = io.BytesIO()
with zipfile.ZipFile(outer, "w") as z:
    z.writestr("חיים פרודוקציה ישן מבוטלות-MM00000061301-09_06_2026-07_37_47.ARJ", inner.getvalue())
    z.writestr("חיים פרודוקציה ישן פרט-MP00000061301-10_06_2026-07_41_51.ARJ", inner.getvalue())
check("only the active bundle parsed", len(parse_menora_legacy_zip(outer.getvalue())["records"]), 1)

print()
if failures:
    print(f"FAILED ({len(failures)}): " + ", ".join(failures))
    sys.exit(1)
print("All Menora legacy parser checks passed.")
