"""Nifra Agent × policies — live eval against the REAL model (costs a few cents per run).

    source backend/venv/bin/activate && python backend/tests/agent_eval_policies.py [--base http://localhost:8000]

Needs the local API running and test@test.com holding: the הר הביטוח example (203717186), and the
uploaded PDFs of רונית בכר (Phoenix life) and שרון/שאול גולן (Harel health + nursing).
Each case checks the facts the answer must carry, and EVERY answer is grounding-checked: any
number of 5+ digits (policy numbers, IDs, sums) must exist somewhere in the agent's own policy data.
"""
import asyncio
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import HarbRequest, InsurancePolicy, PolicyDocument, User, WorkerHeartbeat  # noqa: E402
from app.services.auth_service import create_access_token  # noqa: E402

BASE = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "http://localhost:8000"
FAILS: list[str] = []

# (question, must contain ALL of, must contain ANY of, expect a harb proposal)
CASES = [
    # content, not formatting: the 8 active policies span these companies (both Clal life policies named)
    # both Clal life policies must be there — named by number OR by their sums (75,000 / 35,000)
    ("אילו פוליסות בתוקף יש ללקוח 203717186?", ["8", "הראל", "הפניקס", "מנורה", "כלל"], ["6939773", "35,000"], False),
    ("יש לרונית בכר ביטוח חיים? מה סכום הביטוח?", [], ["1,000,000", "1000000", "מיליון"], False),
    ("מי המוטב בפוליסת הריסק של רונית בכר?", ["הפועלים"], [], False),
    ("כמה עולה לשאול גולן ביטוח הסיעוד שלו בהראל?", ["287.70"], [], False),
    ("יש החרגות רפואיות בפוליסה של שאול גולן?", [], ["לא נקבעו", "אין החרגות", "ללא החרגות", "אין תנאים מיוחדים"], False),
    ("למי מהלקוחות יש ביטוח מחלות קשות?", ["עמיקם"], ["שרון", "גולן"], False),
    ("תביא לי מהר הביטוח את 59034975 תאריך לידה 22/10/1964 הנפקה 01/02/1990", [], [], True),
    ("תביא לי מהר הביטוח את 59034975", [], ["תאריך"], False),          # missing dates → ask, no card
]


def ask(token: str, q: str) -> tuple[str, dict | None, list[str]]:
    req = urllib.request.Request(f"{BASE}/api/ai/agent", data=json.dumps({"question": q, "history": [], "surface": "panel"}).encode(),
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    text, prop, st = "", None, []
    for line in urllib.request.urlopen(req, timeout=240):
        line = line.decode().strip()
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:])
        except ValueError:
            continue
        text += ev.get("text") or ""
        prop = ev.get("proposal") or prop
        if ev.get("status"):
            st.append(ev["status"])
    return text.strip(), prop, list(dict.fromkeys(st))


async def known_numbers(uid) -> set[str]:
    async with async_session() as db:
        nums: set[str] = set()
        for r in (await db.execute(select(InsurancePolicy).where(InsurancePolicy.user_id == uid))).scalars():
            nums |= {r.policy_number or "", r.customer_id_number, str(r.premium or "")}
        for d in (await db.execute(select(PolicyDocument).where(PolicyDocument.user_id == uid))).scalars():
            nums |= {d.policy_number or "", d.customer_id_number or ""}
            nums |= {x.replace(",", "") for x in re.findall(r"\d[\d,]{4,}", d.markdown or "")}
        for q in (await db.execute(select(HarbRequest).where(HarbRequest.user_id == uid))).scalars():
            nums.add(q.customer_id_number)
        return {n.lstrip("0") for n in nums if n}


async def main():
    async with async_session() as db:
        u = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
        await db.execute(update(WorkerHeartbeat).where(WorkerHeartbeat.user_id == u.id).values(last_seen=datetime.utcnow()))
        await db.commit()
    token = create_access_token(str(u.id))
    known = await known_numbers(u.id)
    for q, all_of, any_of, wants_card in CASES:
        print(f"\n— {q}")
        text, prop, st = await asyncio.to_thread(ask, token, q)
        print("  tools:", " → ".join(st))
        print("  answer:", text.replace("\n", " ")[:420])
        missing = [x for x in all_of if x not in text]
        check = lambda c, m: (print(("  ok   " if c else "  FAIL ") + m), None if c else FAILS.append(f"{q}: {m}"))  # noqa: E731
        check(not missing, f"carries {all_of}" + (f" (missing {missing})" if missing else ""))
        if any_of:
            check(any(x in text for x in any_of), f"carries one of {any_of}")
        if wants_card:
            check(bool(prop and prop.get("kind") == "harb" and prop.get("birth_date") == "22/10/1964"
                       and prop.get("issue_date") == "01/02/1990"), f"proposes the fetch with the exact dates ({prop})")
        else:
            check(not (prop and prop.get("kind") == "harb"), "no fetch card drawn")
        nums = [n.strip(",") for n in re.findall(r"\d[\d,]{4,}", text)]
        stray = [n for n in nums if len(n.replace(",", "")) >= 5 and n.replace(",", "").lstrip("0") not in known
                 and not re.fullmatch(r"\d{2}/?\d{2}/?\d{4}", n)]
        stray = [n for n in stray if not re.fullmatch(r"(19|20)\d{2}", n.replace(",", ""))]
        check(not stray, "every 5+ digit number is in the agent's own data" + (f" (invented? {stray})" if stray else ""))
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    for f in FAILS:
        print("  -", f)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    asyncio.run(main())
