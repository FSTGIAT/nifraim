"""Nifra Agent — COMMISSIONS & PRODUCTION conversations, Menora-style: follow-ups, company switches,
companies with nothing owed, months with no data, name-order traps, rates, typos, percentages.
Live, real model, local DB, user test@test.com. Expected numbers are the user's real data
(get_overview / get_unpaid / get_commission_trend / top_customers, read 2026-10-05).

    cd backend && python tests/agent_world_money.py [--only N,N]
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_world_calls as W  # noqa: E402
from app.database import engine  # noqa: E402
from app.services.agent import cache, loop  # noqa: E402

TOTAL = r"24[,.]?13[56]|24\.1 ?אלף"
NONE = r"אין|לא נמצא|אפס|₪0\b|0 ₪|לא (מופיע|קיים|חייב|רשום)|הכול שולם|הכל שולם|שולם במלואו|לא שולם.{0,6}כלום|אין חוב"


def a(r):
    return r["answer"]


def has(r, *pats):
    return all(re.search(p, a(r)) for p in pats)


CASES = [
    # ── commissions: follow-ups ───────────────────────────────────────────
    ("received → 'and expected?'", ["כמה עמלות קיבלתי?", "ומכמה ציפיתי?"],
     lambda r: has(r, r"62[,.]?98|63 ?אלף")),
    ("Harel list → 'and Guy?'", ["מי חייב בהראל?", "ומה עם גיא?"],
     lambda r: has(r, r"גיא", r"510")),
    ("Harel → as % of expected", ["מי חייב בהראל?", "כמה זה באחוזים מהצפי שם?"],
     lambda r: has(r, r"39|40 ?%")),
    ("all unpaid → 'and of them at Phoenix?'", ["כמה לקוחות לא שולמו בכלל?", "ומתוכם בהפניקס?"],
     lambda r: has(r, r"188")),
    ("compare two companies' commissions", ["תשווה לי בין הפניקס להראל בעמלות שלא שולמו"],
     lambda r: has(r, r"19[,.]?6", r"3[,.]?07")),
    ("received from one company", ["כמה עמלות התקבלו מהראל?"],
     lambda r: has(r, r"4[,.]?72[23]|4[,.]?7 ?אלף")),
    ("gap expected vs received", ["מה הפער בין מה שציפיתי למה שקיבלתי?"],
     lambda r: has(r, TOTAL)),
    # ── companies with NOTHING owed (no total dumped) ─────────────────────
    ("nothing unpaid at Migdal", ["כמה לא שולם במגדל?"],
     lambda r: has(r, NONE) and not re.search(TOTAL, a(r))),
    ("nothing unpaid at Mor", ["מי חייב במור?"],
     lambda r: has(r, NONE) and not re.search(TOTAL, a(r))),
    # ── months: real vs missing ───────────────────────────────────────────
    ("a month with data", ["כמה קיבלתי ביוני?"],
     lambda r: has(r, r"17[,.]?47")),
    ("a month with NO data (no invention)", ["כמה עמלות קיבלתי במרץ?"],
     lambda r: has(r, NONE + r"|לא התקבל|אין נתונים|רק (מ|ב)") and not re.search(r"במרץ.{0,20}17[,.]?47", a(r))),
    ("why the trend looks odd", ["למה אין לי עמלות בין דצמבר ליוני?"],
     lambda r: len(a(r)) > 50 and not re.search(r"התקבלו .{0,10}בפברואר", a(r))),
    # ── agreements / rates ────────────────────────────────────────────────
    ("rate, then 'and Phoenix?'", ["מה ההסכם שלי עם מגדל?", "ועם הפניקס?"],
     lambda r: has(r, r"0[.,]45|0[.,]34|0[.,]32")),
    ("rate for one product", ["מה שיעור העמלה בהפניקס על פוליסות?"],
     lambda r: has(r, r"0[.,]34")),
    # ── one customer's money ──────────────────────────────────────────────
    ("was X's commission paid?", ["העמלה של אורי פלד שולמה?"],
     lambda r: has(r, r"1[,.]?111|לא שולמ")),
    ("name-order trap (גורן גורן = גיא גורן)", ["על מה לא שולם לגורן גורן?"],
     lambda r: has(r, r"510|הראל|מסלול מניות") or ("גיא גורן" in a(r) and "?" in a(r))),
    ("by ID, then 'how much do I earn on her?'", ["מה יש ל-13902283?", "וכמה עמלה אני מקבל עליה?"],
     lambda r: has(r, r"\d") and not re.search(TOTAL, a(r))),
    # ── production ────────────────────────────────────────────────────────
    ("biggest customer → 'and by premium?'", ["מי הלקוח הכי גדול שלי?", "ובפרמיה?"],
     lambda r: has(r, r"חיים חיים|שושנה מני|19[,.]?26")),
    ("accumulation at one company", ["כמה צבירה יש לי בהפניקס?"],
     lambda r: has(r, r"168")),
    ("customers → 'and at Harel?'", ["כמה לקוחות יש לי?", "ובהראל?"],
     lambda r: has(r, r"הראל") and not re.match(r"\s*2[,.]?969", a(r))),
    ("who left — no earlier file (no invention)", ["מי עזב אותי החודש?"],
     lambda r: has(r, r"אין (קובץ|השוואה|נתונ)|קובץ (קודם|פרודוקציה קודם)|לא ניתן|אי אפשר|אין לי (קובץ|נתונ)")),
    ("premium in one product line", ["כמה פרמיה יש לי בבריאות?"],
     lambda r: has(r, r"בריאות", r"\d")),
    # ── typos & language ──────────────────────────────────────────────────
    ("typo in the company", ["כמה עמלות קיבלתי מהפנקס?"],
     lambda r: has(r, r"6[,.]?55[67]|6[,.]?6 ?אלף")),
    ("English", ["How much commission did Harel not pay me?"],
     lambda r: has(r, r"3[,.]?07|3,070")),
    ("calls × unpaid (one tool)", ["למי מהלקוחות שדיברתי איתם בשיחות יש עמלות שלא שולמו?"],
     lambda r: has(r, r"שרית", r"חיים") and "calls_with_unpaid" in r["tools"] and not re.search(r"כלי", a(r))),
    ("commission by PRODUCT (prod report)", ["על איזה מוצר יש לי עמלה הכי גבוהה?"],
     lambda r: "commission_by_product" in r["tools"] and has(r, r"\d")),
    ("'כן' delivers what was offered (prod report)", ["על איזה מוצר יש לי עמלה הכי גבוהה?", "רוצה גרף?", "כן"],
     lambda r: not re.search(r"המסך .{0,30}(לא|אין)", a(r)) and len(a(r)) > 20),
    ("a correction is not 'top customers' (prod report)",
     ["על איזה מוצר יש לי עמלה הכי גבוהה?", "אקסלנס גמל הוא לא המוצר הגדול ביותר"],
     lambda r: "top_customers" not in r["tools"] and not re.search(r"הלקוחות הגדולים", a(r))),
    ("most problematic company", ["איזו חברה הכי בעייתית אצלי בתשלומים?"],
     lambda r: has(r, r"הפניקס")),
]


async def main(only: set[int] | None) -> None:
    async def _no():
        return False
    loop._rate_limited = lambda db, uid: _no()
    cache.get = lambda *a, **k: None
    ok_n = 0
    run = 0
    try:
        for i, (name, turns, check) in enumerate(CASES, 1):
            if only and i not in only:
                continue
            hist, lanes = [], []
            for q in turns:
                r = await W.ask(q, hist)
                lanes.append(r["lane"])
                hist += [{"role": "user", "text": q}, {"role": "agent", "text": r["answer"]}]
            try:
                ok = bool(check(r))
            except Exception as e:  # noqa: BLE001
                ok, r["answer"] = False, r["answer"] + f"  [check error {e}]"
            run += 1
            ok_n += ok
            print(f"{i:2}. {'PASS' if ok else 'FAIL'}  {name}  (lanes {'→'.join(lanes)} · {', '.join(dict.fromkeys(r['tools'])) or '-'})", flush=True)
            print("      " + " → ".join(turns))
            print(f"      ת: {a(r)[:260].replace(chr(10), ' ')}", flush=True)
    finally:
        await engine.dispose()
    print(f"\n{ok_n}/{run} passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a_ = ap.parse_args()
    asyncio.run(main({int(x) for x in a_.only.split(",")} if a_.only else None))
