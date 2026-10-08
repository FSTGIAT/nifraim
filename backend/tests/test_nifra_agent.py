"""Nifra AI v2 tests — privacy, routing, dashboard parity, cache invalidation, fund matching.

    source backend/venv/bin/activate && python backend/tests/test_nifra_agent.py

No model calls (the agent loop's LLM lane isn't exercised here — see the latency
script in docs/ARCHITECTURE.md §17). Runs against the local dev DB: test@test.com
(user A, the data account) and cycle-ui@test.com (user B). Writes are rolled back.

The assertions that carry real weight:
  * no tool schema can take a user id, and dispatch() strips one if the model sends it;
  * user B's tool output never contains any of user A's customer IDs;
  * the fast-lane numbers EQUAL the dashboard endpoints' numbers (one source per number);
  * an AI-relevant write bumps users.ai_data_version (stale answers can't survive);
  * the fund matcher never maps a customer's track to another insurer's fund.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.agent import registry, router  # noqa: E402
from app.services.agent.context import ToolContext  # noqa: E402

A_EMAIL, B_EMAIL = "test@test.com", "cycle-ui@test.com"
FAILS: list[str] = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def test_registry():
    print("registry")
    tools = registry.all_tools()
    check(len(tools) >= 25, f"{len(tools)} tools registered")
    for t in tools:
        check(not (set(t.schema["properties"]) & registry.FORBIDDEN_ARGS), f"{t.name}: no user-id argument")
    strict = [d for d in registry.anthropic_tools() if d.get("strict")]
    check(len(strict) <= 20, f"{len(strict)} strict tools (API max 20)")
    names = [t.name for t in tools]
    check(names == sorted(names), "tool list sorted (stable prompt-cache prefix)")


def test_router():
    print("router (fast lane)")
    cases = {
        "כמה עמלות לא שולמו לי?": "unpaid", "מי לא שילם לי בהפניקס?": "unpaid",
        "כמה עמלה קיבלתי החודש?": "trend", "כמה צבירה יש לי לפי חברה?": "portfolio",
        "מי הלקוחות הגדולים שלי?": "top", "מי עזב החודש?": "changes",
        "מה שיעור העמלה בהפניקס?": "rate", "מה מצב המסלקה?": "maslaka_status",
        "מה כדאי לי לעשות השבוע?": "tasks", "תמונת מצב": "overview",
        "מה יש ללקוח 50417716": "customer",
    }
    for q, intent in cases.items():
        r = router.route(q)
        check(r is not None and r.intent == intent, f"«{q}» → {intent} (got {r.intent if r else None})")
    check(router.route("מה יש ללקוח אברהם משה?").intent == "customer_name", "«מה יש ללקוח <שם>» → customer_name (fast only on a single match)")
    for q in ("תשלח מייל להפניקס על מה שלא שולם", "למה לא שילמו לי בהפניקס?", "תבקש מהמסלקה 9100 ללקוח 50417716",
              "כמה לא שולם ללקוח אברהם משה?"):
        check(router.route(q) is None, f"«{q}» → agent lane (action / why)")
    check(router.route("אילו מוצרים יש ללקוחות המובילים שלי") is None,
          "«אילו מוצרים יש ללקוחות המובילים» → agent lane (not the ranking alone)")
    r = router.route("מי לא שילם לי בהפניקס?")
    check(r.args.get("company") == "הפניקס", "company extracted")


async def _user(db, email):
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def test_privacy_and_parity():
    async with async_session() as db:
        a, b = await _user(db, A_EMAIL), await _user(db, B_EMAIL)
        if not a or not b:
            print("privacy: SKIP (local test users missing)")
            return
        print("privacy (user B never sees user A)")
        from app.models.record import ClientRecord
        a_ids = {str(x).lstrip("0") for x in (await db.execute(select(ClientRecord.id_number).where(ClientRecord.user_id == a.id))).scalars() if x}
        b_ids = {str(x).lstrip("0") for x in (await db.execute(select(ClientRecord.id_number).where(ClientRecord.user_id == b.id))).scalars() if x}
        only_a = {i for i in a_ids - b_ids if len(i) >= 6}
        ctx_b = ToolContext(db=db, user=b)
        calls = [("get_overview", {}), ("get_unpaid", {}), ("get_unpaid", {"company": "הפניקס"}), ("top_customers", {"n": 30}),
                 ("get_portfolio", {}), ("get_commission_trend", {}), ("get_production_changes", {}),
                 ("get_insights", {"kind": "tasks"}), ("get_insights", {"kind": "retention"}), ("list_mail", {}),
                 ("find_customer", {"query": "גיא גורן"}), ("maslaka_status", {}), ("fund_opportunities", {}),
                 ("get_unpaid", {"company": "הפניקס", "user_id": str(a.id)})]   # a forged user id is ignored
        for name, args in calls:
            out = await registry.dispatch(ctx_b, name, args)
            leaked = {i for i in re.findall(r"\d{6,9}", out) if i.lstrip("0") in only_a}
            check(not leaked, f"B:{name}{'(+forged user_id)' if 'user_id' in args else ''} leaks none of A's IDs" + (f" — LEAK {sorted(leaked)[:3]}" if leaked else ""))

        # asking B's agent directly for one of A's customers: "not found", nothing about them
        probe = next(iter(only_a), "0")
        out = await registry.dispatch(ctx_b, "get_customer", {"id_number": probe})
        check(out.startswith("# לא נמצא") and "₪" not in out and "פוליסה" not in out,
              "B:get_customer(A's ID) → not found, no data (echoes only the asked ID)")

        print("a question naming ONE customer never gets an all-book instant answer")
        from app.services.agent.prefetch import named_customer
        from app.models.record import ClientRecord as _CR
        r0 = (await db.execute(select(_CR.first_name, _CR.last_name).where(_CR.user_id == a.id,
              _CR.first_name.isnot(None), _CR.last_name.isnot(None)).limit(1))).first()
        if r0:
            nm = f"{r0[0].split()[0]} {r0[1].split()[0]}" if " " not in r0[0] and " " not in r0[1] else None
            if nm:
                ctx_n = ToolContext(db=db, user=a)
                check(await named_customer(ctx_n, f"כמה לא שולם ל{nm}?") == nm, f"«כמה לא שולם ל{nm}?» detects the customer")
                check(await named_customer(ctx_n, "כמה עמלות לא שולמו לי?") is None, "a general question names no customer")

        print("parity (AI numbers == dashboard numbers), user A")
        from app.api import comparison, production
        ctx_a = ToolContext(db=db, user=a)
        cs = await comparison.company_summary(db=db, user=a)
        un = json.loads(await registry.dispatch(ctx_a, "get_unpaid", {}))
        check(abs(un["total_gap"] - round(cs["totals"]["gap"], 2)) < 0.01, f"unpaid total {un['total_gap']} == company-summary gap {round(cs['totals']['gap'], 2)}")
        ov = json.loads(await registry.dispatch(ctx_a, "get_overview", {}))
        check(abs(ov["received_total"] - round(cs["totals"]["received"], 2)) < 0.01, "overview received == company-summary received")
        tr = await production.get_commission_trend(db=db, user=a)
        t = json.loads(await registry.dispatch(ctx_a, "get_commission_trend", {}))
        if tr:
            check(abs(t["last"]["value"] - round(tr[-1]["total_commission"], 2)) < 0.01, "trend last month == /production/trend")
        r = router.route("כמה עמלות לא שולמו לי?")
        ans = await router.answer(ctx_a, r)
        check(f"₪{round(cs['totals']['gap']):,}" in ans["text"], "fast-lane text quotes the dashboard gap")

        print("cache invalidation")
        aid = a.id
        from app.models.company_contact import CompanyContact
        from app.services.agent.versioning import current
        v0 = await current(db, aid)
        c = CompanyContact(user_id=aid, company_name="__nifra_test__", email="t@example.com")
        db.add(c)
        await db.flush()
        await db.rollback()
        await asyncio.sleep(0.3)
        check(await current(db, aid) == v0, "rolled-back write bumps nothing")
        c = CompanyContact(user_id=aid, company_name="__nifra_test__", email="t@example.com")
        db.add(c)
        await db.commit()
        await asyncio.sleep(0.4)          # bumped after commit, in its own short transaction
        v1 = await current(db, aid)
        check(v1 == v0 + 1, f"committed AI-relevant write bumps ai_data_version ({v0}→{v1})")
        c.email = "t@example.com"         # no-op set: must NOT count as a change
        await db.commit()
        await asyncio.sleep(0.4)
        check(await current(db, aid) == v1, "a no-op attribute set does not bump")
        await db.delete(c)
        await db.commit()
        await asyncio.sleep(0.4)

        print("opening the Nifra Agent panel does not empty the cache")
        from app.services import office_agent
        v2 = await current(db, aid)
        await office_agent.brief(db, await _user(db, A_EMAIL))
        await db.commit()
        await asyncio.sleep(0.4)
        await office_agent.brief(db, await _user(db, A_EMAIL))
        await db.commit()
        await asyncio.sleep(0.4)
        v3 = await current(db, aid)
        check(v3 <= v2 + 1, f"two panel opens bump at most once ({v2}→{v3})")


def test_calls_routing():
    print("calls (record / stop / summaries)")
    from app.services.agent.prefetch import plan
    check(router.route("תקליט את השיחה עם משה כהן").intent == "record_call", "«תקליט את השיחה…» → record (instant)")
    check(router.route("עצור").intent == "stop_call", "«עצור» → stop (instant)")
    check(router.route("מה היה בשיחה האחרונה?") is None, "call question → agent lane")
    check(plan("מה סיכמתי עם הלקוח על דמי הניהול?") == [("get_call_summaries", {"which": "last", "n": 3})],
          "«…הלקוח על דמי הניהול» is a call topic, not a customer name")
    check(plan("מה יש ללקוח אברהם משה?")[0] == ("find_customer", {"query": "אברהם משה"}), "a name starting with מ is not cut")
    check(plan("למה הלקוח משה כהן לא שולם ממגדל")[0] == ("find_customer", {"query": "משה כהן"}), "name ends at «לא» / «ממגדל»")


def test_fund_matcher():
    print("fund matcher")
    from types import SimpleNamespace as N
    from app.services.agent.tools_market import category_for_product, match_fund
    funds = [N(fund_id=1, fund_name="מיטב השתלמות כללי", managing_corporation='מיטב גמל ופנסיה בע"מ'),
             N(fund_id=2, fund_name="מור קרן השתלמות לשכירים ולעצמאים - כללי", managing_corporation='מור גמל ופנסיה בע"מ'),
             N(fund_id=3, fund_name="מור קרן השתלמות לשכירים ולעצמאים - מניות", managing_corporation='מור גמל ופנסיה בע"מ'),
             N(fund_id=4, fund_name="הראל מסלול לבני 50 עד 60", managing_corporation='הראל פנסיה וגמל בע"מ')]
    f, _ = match_fund("מור השתלמות - כללי", 'מור גמל ופנסיה בע"מ', funds)
    check(f is not None and f.fund_id == 2, "מור כללי → מור כללי (never מיטב)")
    f, _ = match_fund("אלפא מור תגמולים - לבני 50 עד 60", 'מור גמל ופנסיה בע"מ', funds)
    check(f is None, "no same-insurer candidate → no match (never הראל)")
    f, _ = match_fund("מור השתלמות - מניות", 'מור גמל ופנסיה בע"מ', funds)
    check(f is not None and f.fund_id == 3, "track tokens pick מניות, not כללי")
    from app.services.agent.tools_market import is_open
    check(not is_open(N(target_population="עובדי סקטור מסויים", classification="קרנות השתלמות")), "sector-only fund is never a switch target")
    check(not is_open(N(target_population=None, classification="קרנות כלליות")), "closed veteran pension fund is never a switch target")
    check(is_open(N(target_population="כלל האוכלוסיה", classification="קרנות השתלמות")), "public fund is open")
    check(category_for_product("קרן השתלמות") == "hishtalmut", "category: השתלמות")
    check(category_for_product("קופת גמל להשקעה") == "gemel_invest", "category: גמל להשקעה")
    check(category_for_product("קופת גמל לתגמולים ופיצויים") == "gemel", "category: גמל")


def test_policies_routing():
    """הר הביטוח / policies: the fetch verb is an action ONLY toward הר הביטוח, and policy
    questions never take the customer-card fast lane (the card has no policies)."""
    from app.services.office_agent import wants_action
    print("policies routing")
    for q in ("תביא לי מהר הביטוח 203717186 22/05/1986 10/03/2004", "תבדוק בהר הביטוח את 32489387"):
        check(wants_action(q, []), f"«{q}» allows actions")
    for q in ("תביא לי את הלקוחות הגדולים", "מה יש לו בהר הביטוח"):
        check(not wants_action(q, []), f"«{q}» is a question, not an action")
    check(wants_action("22/05/1986 10/03/2004", [{"role": "user", "text": "תביא לי מהר הביטוח 203717186"}]),
          "dates answering the agent's question keep the action alive")
    for q in ("אילו פוליסות בתוקף יש ללקוח 203717186?", "האם 32489387 מכוסה בסיעוד", "תביא לי מהר הביטוח 203717186"):
        check(router.route(q) is None, f"«{q}» → agent lane")
    check(router.route("מי הלקוחות עם הכי הרבה פוליסות").intent == "top", "«הכי הרבה פוליסות» stays fast (top)")
    names = {t["name"] for t in registry.anthropic_tools()}
    check({"propose_harb_fetch", "customer_policies", "search_policies", "get_policy_document"} <= names,
          "the four policy tools are registered")


async def test_policies_privacy():
    """User B never sees user A's policies, and a proposal is never drawn without its gates."""
    print("policies privacy")
    async with async_session() as db:
        b = await _user(db, B_EMAIL)
        if not b:
            print("  skip — no user B")
            return
        ctx = ToolContext(db=db, user=b)
        out = str(await registry.dispatch(ctx, "customer_policies", {"id_number": "203717186"}))
        check('"found": false' in out and "עמיקם" not in out, "B's customer_policies on A's customer → nothing")
        out = str(await registry.dispatch(ctx, "search_policies", {"query": "ביטוח סיעודי הראל"}))
        check("301611265" not in out and "עמיקם" not in out, "B's search_policies never returns A's passages")
        await registry.dispatch(ctx, "propose_harb_fetch", {"id_number": "203717186", "birth_date": "22/05/1986",
                                                            "issue_date": "10/03/2004"})
        check(not ctx.proposals, "no credential/worker for B → no הר הביטוח proposal")


def main():
    test_registry()
    test_policies_routing()
    test_router()
    test_fund_matcher()
    test_calls_routing()
    async def _db_tests():   # one event loop — the async engine's pool is bound to it
        await test_privacy_and_parity()
        await test_policies_privacy()
    asyncio.run(_db_tests())
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
