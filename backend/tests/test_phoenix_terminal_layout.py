"""Phoenix terminal .MBT — the two files do NOT share a column layout.

`LIFE.MBT` has 133 cells per row and `LIFEHLTH.MBT` has 58, and one shared
index map was applied to both. On the 58-cell file that read cell [19], which
holds the same 14612.00 on every row — so a whole health book was published
with one identical "premium" per client, and the accumulation index (74) fell
off the end of the row and silently became None.

Measured on a real export before the fix: 80 records, premium uniq=3 with
14612.00 on 74 of them. After: premium uniq=68, median ₪83.88.
`api/production.py` documents the same number from the downstream side
("~76 clients each carrying exactly ₪14,612 of monthly health premium").

Synthetic rows here on purpose — the shape is the whole point and real
policies would put client PII in the repo.

Run:  PYTHONPATH=. venv/bin/python tests/test_phoenix_terminal_layout.py
"""
import tempfile
from pathlib import Path

from app.services.phoenix_terminal import parse_phoenix_mbt_set

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


def _row(n_cells: int, **cells) -> str:
    row = [""] * n_cells
    for i, v in cells.items():
        row[int(i)] = str(v)
    return "|".join(row)


def _write(folder: Path, name: str, rows: list[str]) -> None:
    (folder / name).write_text("\n".join(rows) + "\n", encoding="cp1255")


def _life_row(policy, idn, premium_19, accum_74):
    # 133 cells — the real LIFE.MBT width.
    return _row(133, **{"9": policy, "10": idn, "14": "ןהכ השמ", "15": "01062015",
                        "19": premium_19, "74": accum_74})


def _lifehlth_row(policy, idn, c19, annual_48, monthly_49):
    # 58 cells — the real LIFEHLTH.MBT width. Nothing at 74 to read.
    return _row(58, **{"9": policy, "10": idn, "14": "ןהכ השמ", "15": "01062015",
                       "19": c19, "43": "12", "48": annual_48, "49": monthly_49})


with tempfile.TemporaryDirectory() as td:
    folder = Path(td)
    _write(folder, "LIFE.MBT", [
        _life_row("01050417716", "014007738", "14612.00", "6853.51"),
        _life_row("01050417717", "014007739", "14612.00", "119298.76"),
    ])
    # Five rows so the constant-column guard has enough evidence to fire.
    _write(folder, "LIFEHLTH.MBT", [
        _lifehlth_row("01022389456", "018413268", "14612.00", "1287.85", "107.71"),
        _lifehlth_row("01022389457", "018413269", "14612.00", "2100.86", "175.70"),
        _lifehlth_row("01022389458", "018413270", "14612.00", "995.24", "83.24"),
        _lifehlth_row("01022389459", "018413271", "14612.00", "632.14", "52.87"),
        _lifehlth_row("01022389460", "018413272", "14612.00", "2225.03", "186.11"),
    ])

    recs = parse_phoenix_mbt_set(folder)["records"]
    prem = [r['סה"כ פרמיה'] for r in recs if r['סה"כ פרמיה'] is not None]
    acc = [r["צבירה"] for r in recs if r["צבירה"] is not None]

    print("\n[1] the 14612 constant never reaches a record")
    check("no record carries the constant", 14612.0 in prem, False)
    check("every emitted premium is distinct", len(prem), len(set(prem)))

    print("\n[2] LIFEHLTH premium comes from the per-payment column [49]")
    hl = [r for r in recs if r["סוג מוצר"] == "חיים ובריאות"]
    check("all five health rows priced", len(hl), 5)
    check("premium is the monthly figure",
          sorted(r['סה"כ פרמיה'] for r in hl),
          sorted([107.71, 175.70, 83.24, 52.87, 186.11]))
    check("health rows carry no accumulation (no such column)",
          [r["צבירה"] for r in hl], [None] * 5)

    print("\n[3] LIFE keeps its own map — accumulation read, premium NOT guessed")
    life = [r for r in recs if r["סוג מוצר"] == "חיים"]
    check("accumulation survives", sorted(acc), [6853.51, 119298.76])
    check("premium left None rather than guessed off 6 rows",
          [r['סה"כ פרמיה'] for r in life], [None, None])

    print("\n[4] a premium column that turns constant is refused, not published")
    # If Phoenix shifts columns so [49] becomes a fixed value, the guard must
    # emit None rather than stamp one number onto every client.
    folder2 = Path(td) / "shifted"
    folder2.mkdir()
    _write(folder2, "LIFEHLTH.MBT", [
        _lifehlth_row(f"0102238945{i}", f"01841326{i}", "14612.00", "1287.85", "9999.00")
        for i in range(5)
    ])
    shifted = parse_phoenix_mbt_set(folder2)["records"]
    check("constant column refused",
          {r['סה"כ פרמיה'] for r in shifted}, {None})

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    raise SystemExit(1)
print("all checks passed")
