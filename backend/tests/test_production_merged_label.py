"""A production file spanning several insurers is labelled "מאוחד" (parser_service._parse_production).

    source backend/venv/bin/activate && python backend/tests/test_production_merged_label.py

Before 2026-10-02 a manually uploaded merged production file was labelled by its BIGGEST
insurer (הראל), so the upload replaced only הראל's active file and left the previous merged
file active — every other insurer counted twice (test user: מנורה 285 + 80 rows).
Uses the real merged file in downloaded_unified/ (skips if absent).
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app.services.parser_service import parse_excel  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "downloaded_unified" / "פרודוקציה מאוחד יוני 2026.xlsx"
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def only(company_word: str) -> bytes:
    """The same workbook, every sheet filtered to one insurer's rows."""
    xl = pd.ExcelFile(SRC)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for sh in xl.sheet_names:
            df = pd.read_excel(SRC, sheet_name=sh, dtype=str)
            if "יצרן" in df.columns:
                df = df[df["יצרן"].astype(str).str.contains(company_word, na=False)]
            df.to_excel(w, sheet_name=sh, index=False)
    return buf.getvalue()


def main():
    if not SRC.exists():
        print(f"SKIP — {SRC} not found")
        return
    r = parse_excel(SRC.read_bytes(), SRC.name)
    check(r["company_source"] == "מאוחד", f"multi-insurer production → מאוחד (got {r['company_source']})")
    r = parse_excel(only("מנורה"), "מנורה פרודוקציה יוני 2026.xlsx")
    check(r["company_source"] and "מנורה" in r["company_source"], f"one insurer keeps its name (got {r['company_source']})")
    r = parse_excel(only("הפניקס"), "הפניקס פרודוקציה יוני 2026.xlsx")
    check(r["company_source"] and "הפניקס" in r["company_source"],
          f"two legal entities of ONE insurer (חברה לביטוח + אקסלנס) stay that insurer (got {r['company_source']})")
    print("\nALL PASS" if not FAILS else f"\n{len(FAILS)} FAILED")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
