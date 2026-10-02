"""Prefetch — run the obvious tools BEFORE the model, so it answers in ONE call.

A model round trip costs ~1.5–2.5s just to decide "call get_unpaid(הפניקס)". When the
question names a company, a customer (name or ת.ז) or a fund category, we already know
which tools it needs: run them here (same registry, same ToolContext → same privacy and
same numbers) and put their output in the first user message. The model can still call
more tools if something is missing.
"""
from __future__ import annotations

import re

from app.services.agent import registry
from app.services.agent.router import COMPANIES, ID_RE

FUND_CATS = [  # (pattern, tool)
    (r"חיסכון לכל ילד|חסכון לכל ילד|לילד", "compare_child_savings"),
    (r"גמל להשקעה", "compare_gemel_invest"),
    (r"השתלמות", "compare_hishtalmut"),
    (r"פנסי", "compare_pension"),
    (r"פוליס[הות] חיסכון|פוליסות חסכון", "compare_savings_policy"),
    (r"קופ(?:ת|ות) גמל|\bגמל\b", "compare_gemel"),
]
FUND_Q = re.compile(r"קרן|קרנות|קופ|מסלול|תשוא|הכי טוב|דמי ניהול|להשוות|השווא|מומלץ")
TRACKS = ["מניות", "כללי", "S&P", "אג\"ח", "אגח", "לבני 50", "עד 60", "ומעלה", "ומטה", "הלכה", "כספי", "שקלי"]
NAME_RE = re.compile(r"(?:^|\s)(?:ל|ה|של )?לקוח(?:ה)?\s+([א-ת][א-ת'\"\- ]{2,30}?)(?=\s*(?:\?|$|,|\.| ב[א-ת]| מ[א-ת]| עם| יש| של))")
MAX_CHARS = 9000


def plan(question: str) -> list[tuple[str, dict]]:
    q = " ".join((question or "").split())
    calls: list[tuple[str, dict]] = []
    m = ID_RE.search(q)
    if m:
        calls.append(("get_customer", {"id_number": m.group(1)}))
    else:
        n = NAME_RE.search(q)
        if n and not re.search(r"\b(?:הכי|שלי|כולם|בכלל|חדשים)\b", n.group(1)):
            calls.append(("find_customer", {"query": n.group(1).strip()}))
    explain = re.search(r"מה ההבדל|מה זה|תסביר|הסבר|איך עובד", q)
    if FUND_Q.search(q) and not explain:
        for pat, tool_name in FUND_CATS:
            if re.search(pat, q):
                track = next((t for t in TRACKS if t in q), "")
                calls.append((tool_name, {"track": track} if track else {}))
                break
    co = next((c for c in COMPANIES if c in q), "")
    if co and not any(t.startswith("compare_") for t, _ in calls):
        calls.append(("get_unpaid", {"company": co}))
        if re.search(r"הסכם|שיעור|אחוז|עמלה|למה|מתעכב|לא שיל", q):
            calls.append(("get_rate", {"company": co}))
        if re.search(r"למה|מתעכב|מגמה|חודש|עיכוב", q):
            calls.append(("get_commission_trend", {"company": co}))
    return calls[:3]


async def run_prefetch(ctx, question: str):
    """Yields status events; returns (via ctx.prefetched) the text block for the prompt."""
    blocks = []
    for name, args in plan(question):
        t = registry.get(name)
        if not t:
            continue
        yield {"status": t.status_he}
        out = await registry.dispatch(ctx, name, args)
        blocks.append(f"### {name}({', '.join(f'{k}={v}' for k, v in args.items())})\n{out[:4000]}")
    text = "\n\n".join(blocks)
    ctx.prefetched = text[:MAX_CHARS]
