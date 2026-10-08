"""הר הביטוח portfolio parser + Markdown + chunking — on the real example export.

    source backend/venv/bin/activate && python backend/tests/test_harb_parser.py [path.xlsx]

Default file: the example the agent provided (עמיקם עינב הר הביטוח.xlsx). No DB, no model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.policies.harb_parser import parse_harb_xlsx  # noqa: E402
from app.services.policies.markdown import portfolio_md  # noqa: E402
from app.services.policies.embeddings import chunk  # noqa: E402
from app.services.policies.harb_jobs import parse_user_date  # noqa: E402

DEFAULT = "/mnt/c/Users/roygi/Downloads/REPORT/police_example/עמיקם עינב הר הביטוח.xlsx"
FAILS: list[str] = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
    if not path.exists():
        print(f"skip — {path} not found")
        return
    d = parse_harb_xlsx(path.read_bytes())
    rows = d["rows"]
    print("parser")
    check(str(d["produced_at"]) == "2020-05-03", f"produced_at from the title row ({d['produced_at']})")
    check(len(rows) == 50, f"50 coverage rows (got {len(rows)})")
    doms = {r["domain"] for r in rows}
    check(doms == {"כללי", "בריאות ותאונות אישיות", "חיים ואבדן כושר עבודה"}, f"3 domains ({doms})")
    check(sum(r["renewing"] for r in rows) == 5, "5 'מתחדש' rows → renewing, no dates")
    check(all(isinstance(r["policy_number"], (str, type(None))) for r in rows), "policy numbers are strings")
    check(any(r["policy_number"] == "190495401291554" for r in rows), "a 15-digit policy number survives intact")
    check(not any(r["policy_number"] and r["policy_number"].endswith(".0") for r in rows), "no float '.0' tails")
    check(len(d["notes"]) == 2, "free text below the table kept as notes, never as policies")
    print("markdown + chunks")
    md = portfolio_md("203717186", "עמיקם עינב", rows, d["produced_at"], d["notes"])
    check("ביטוח רכב — רכב חובה + ביטוח מקיף · שומרה · פוליסה 730223517219" in md, "one policy heading carries all its branches")
    import re
    check(not re.search(r"₪0(?![.\d])", md), "no bare ₪0 amounts (₪0.1 is a real premium)")
    cs = chunk(md, "תיק ביטוחי")
    check(len(cs) > 40 and all(c["heading"] for c in cs), f"{len(cs)} passages, each with a heading path")
    check(any("301611265" in c["heading"] and "סיעודי" in c["text"] for c in cs), "a table row passage knows its policy")
    print("dates as agents type them")
    for s, want in (("22/05/1986", "1986-05-22"), ("22.5.86", "1986-05-22"), ("22051986", "1986-05-22"),
                    ("1986-05-22", "1986-05-22"), ("31/02/1990", "None"), ("01/01/2999", "None"), ("", "None")):
        check(str(parse_user_date(s)) == want, f"«{s}» → {want}")
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
