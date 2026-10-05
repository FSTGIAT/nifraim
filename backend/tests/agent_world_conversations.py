"""Nifra Agent — CONVERSATIONS: follow-ups, typos, names that are also company names, negation,
"the first one", "send HIM", thanks. The class of bug the user hit 2026-10-05: "מי חייב במנורה?"
then "על מה לא שולם עומר עמר" answered with the all-companies total (the fast lane ignored the
name AND the thread). Live, real model, local DB, user test@test.com.

    cd backend && python tests/agent_world_conversations.py [--only N,N]
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_world_calls as W  # noqa: E402  (harness: ask / snapshot / NOT_FOUND)
from app.database import engine  # noqa: E402
from app.services.agent import cache, loop  # noqa: E402

TOTAL = "24,136"           # all companies' unpaid — the WRONG answer to any person/company follow-up
PHOENIX = "19,625"


def a(r):
    return r["answer"]


CONVERSATIONS = [
    # ── follow-ups that drop the subject ──────────────────────────────────
    ("pronoun-less name follow-up", ["מי חייב במנורה?", "ומה עם נטע?"],
     lambda r, x: "נטע" in a(r) and TOTAL not in a(r)),
    ("elliptical company switch", ["כמה לא שולם בהפניקס?", "ובהראל?"],
     lambda r, x: "הראל" in a(r) and PHOENIX not in a(r)),
    ("'the first one on the list'", ["מי הלקוחות הכי גדולים שלי?", "מה יש לראשון ברשימה?"],
     lambda r, x: re.search(r"צבירה|פוליס|קרן|מוצר|ביטוח", a(r)) and "?" not in a(r)[:60]),
    ("his policy there", ["על מה לא שולם עומר מור?", "ומה מספר הפוליסה שלו שם?"],
     lambda r, x: re.search(r"\d{5,}", a(r))),
    ("who of them did I talk to", ["מי חייב במנורה?", "ומי מהם דיבר איתי בשיחה?"],
     lambda r, x: re.search(W.NOT_FOUND + r"|אף (אחד|לקוח)|לא היו|לא דיברת", a(r)) and TOTAL not in a(r)),
    ("then: a reminder (context = Menora)", ["מי חייב במנורה?", "תכין תזכורת"],
     lambda r, x: any(p.get("kind") == "collection" and "מנורה" in str(p.get("company")) for p in r["proposals"])
     or re.search(r"מנורה", a(r)) and re.search(r"מייל|איש קשר|כתובת", a(r))),
    ("'send HIM an email' after a list", ["מי חייב במנורה?", "תשלח לו מייל"],
     lambda r, x: x["after"]["sent"] == x["before"]["sent"] and (
         any(p.get("kind") == "email" for p in r["proposals"]) or "?" in a(r))),
    ("thanks is not a question", ["מי חייב במנורה?", "תודה"],
     lambda r, x: "₪" not in a(r) and len(a(r)) < 220),
    ("ID, then 'what did SHE say'", ["מה עם ת.ז 36148096?", "ומה היא אמרה בשיחה?"],
     lambda r, x: re.search(r"ניתוח|תביעה|ברך|הראל", a(r))),
    ("list, then tick the first", ["מה הבטחתי ללקוחות?", "תסמן את הראשונה כבוצעה"],
     lambda r, x: any(p.get("kind") == "call_task" for p in r["proposals"]) and x["after"]["ticked"] == x["before"]["ticked"]),
    # ── names that are company names ──────────────────────────────────────
    ("surname הראל (customer at Menora)", ["מה המצב של יניב הראל?"],
     lambda r, x: "יניב" in a(r) and not re.search(r"עמלות שלא שולמו (מ|ב)הראל|הראל:? ₪", a(r))),
    ("surname מור — a person, not the insurer", ["מה לא שולם לברוך מור?"],
     lambda r, x: "ברוך" in a(r) and TOTAL not in a(r)),
    ("another מור", ["מה המצב של מתן מור?"],
     lambda r, x: "מתן" in a(r)),
    ("first name only, many matches", ["מה עם עומר?"],
     lambda r, x: "?" in a(r) or len(re.findall(r"עומר \S+", a(r))) >= 2),
    # ── typos, negation, comparison, language ─────────────────────────────
    ("typos in the question", ["מי חיב במנורא?"],
     lambda r, x: re.search(r"עומר מור|1,441|מנורה", a(r)) and TOTAL not in a(r)),
    ("company without ה", ["כמה לא שולם בפניקס"],
     lambda r, x: PHOENIX in a(r) or "הפניקס" in a(r)),
    ("negation", ["מי לא חייב כלום במנורה?"],
     lambda r, x: not re.match(r"\s*במנורה 4 לקוחות לא שולמו", a(r))),
    ("comparison of two companies", ["איפה יש יותר חוב — מנורה או הראל?"],
     lambda r, x: "מנורה" in a(r) and "הראל" in a(r)),
    ("English, company in Hebrew data", ["unpaid commissions at Menora?"],
     lambda r, x: re.search(r"1,441|עומר|Omer|Menora|מנורה", a(r))),
    ("'why' follow-up", ["כמה עמלות קיבלתי בחודש האחרון?", "ולמה זה פחות מקודם?"],
     lambda r, x: len(a(r)) > 60 and r["lane"] == "agent"),
]


async def main(only: set[int] | None) -> None:
    async def _no():
        return False
    loop._rate_limited = lambda db, uid: _no()
    cache.get = lambda *a, **k: None
    await W.unplant()
    await W.plant()
    results = []
    try:
        for i, (name, turns, check) in enumerate(CONVERSATIONS, 1):
            if only and i not in only:
                continue
            before = await W.snapshot()
            hist, lanes = [], []
            for q in turns:
                r = await W.ask(q, hist)
                lanes.append(r["lane"])
                hist += [{"role": "user", "text": q}, {"role": "agent", "text": r["answer"]}]
            after = await W.snapshot()
            try:
                ok = bool(check(r, {"before": before, "after": after}))
            except Exception as e:  # noqa: BLE001
                ok, r["answer"] = False, r["answer"] + f"  [check error {e}]"
            results.append(ok)
            print(f"{i:2}. {'PASS' if ok else 'FAIL'}  {name}  (lanes {'→'.join(lanes)} · {', '.join(dict.fromkeys(r['tools'])) or '-'}"
                  + (f" · proposed {[p.get('kind') for p in r['proposals']]}" if r["proposals"] else "") + ")", flush=True)
            for j, q in enumerate(turns):
                print(f"      ש{j + 1}: {q}")
            print(f"      ת: {a(r)[:240].replace(chr(10), ' ')}", flush=True)
    finally:
        await W.unplant()
        await engine.dispose()
    print(f"\n{sum(results)}/{len(results)} passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a_ = ap.parse_args()
    asyncio.run(main({int(x) for x in a_.only.split(",")} if a_.only else None))
