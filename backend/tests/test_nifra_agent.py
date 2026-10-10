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
        # B's own policy numbers are B's data even when one equals an A-only ID number (local data has a
        # Migdal policy 20534274 at B and a record with ID 20534274 at A) — not a leak.
        b_pols = {str(x).lstrip("0") for x in (await db.execute(select(ClientRecord.fund_policy_number).where(
            ClientRecord.user_id == b.id))).scalars() if x}
        only_a = {i for i in a_ids - b_ids - b_pols if len(i) >= 6}
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


async def test_maslaka_file_companies():
    """'Which companies arrived?' must name the bodies in the newest מסלקה file — the
    same list as the tab's panel — never the ones whose request was merely accepted
    (2026-10-10 Nifra listed the 5 still-waiting bodies as the ones that arrived)."""
    print("maslaka: which companies arrived")
    from app.services.agent.tools_maslaka import STATUS_HE
    from app.services.maslaka.delta import file_coverage
    check("ממתין" in STATUS_HE["acknowledged"], "an accepted request reads as waiting, not as arrived")
    from app.models.pension_holding import PensionHolding
    async with async_session() as db:
        uid = (await db.execute(select(PensionHolding.user_id).limit(1))).scalar_one_or_none()
        user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none() if uid else None
        if not user:
            print("  skip  no local user with מסלקה holdings (run against a DB that has one)")
            return
        ctx = ToolContext(db=db, user=user)
        data = await registry.get("maslaka_status").fn(ctx)
        cov = await file_coverage(db, user.id)
        f = data.get("latest_production_file")
        if not cov.get("as_of"):
            check(f is None, "no production file → no file picture")
            return
        got = [c["company"] for c in f["companies_answered"]]
        check(got == [c["company"] for c in cov["by_company"]], f"answered = the tab's companies ({len(got)})")
        check(not set(got) & {w["company"] for w in cov["waiting"]}, "no body is both answered and waiting")
        text, _ = router.render(router.Route("maslaka_status", "maslaka_status", {}), data)
        check(all(c in text for c in got), "fast-lane sentence names every company that answered")
        # "מה השתנה" may only count companies that are in the file: a pension policy number
        # that equals the saver's ID made an unanswered Menora product "removed" (2026-10-10).
        from app.services.maslaka.delta import monthly_delta
        delta = await monthly_delta(db, user.id)
        stray = {c["company"] for c in delta["by_company"]} - set(got)
        check(not stray, f"מה השתנה counts only companies in the file (stray: {sorted(stray)})")
        await db.rollback()


def test_pensyanet_parse():
    """פנסיה-נט XML → rows: asset reports long (group + item), wide reports keep the row; the
    track id is the FUND_ID of fund_market_monthly. And data.gov.il's "S1;P" names are repaired."""
    print("pensyanet parse + S&P names")
    from app.services.fund_market import fix_name
    from app.services.fund_market.pensyanet import parse
    assets = ("<ROWSET><ROW><ID_KRN>1589</ID_KRN><SHM_KRN>מיטב עוקב</SHM_KRN><TKF_DIVUACH>202608</TKF_DIVUACH>"
              "<KVUTZAT_NECHASIM>חשיפות</KVUTZAT_NECHASIM><ID_SUG_NECHES>4751</ID_SUG_NECHES><SHM_SUG_NECHES>חשיפה למניות</SHM_SUG_NECHES>"
              "<SCHUM_SUG_NECHES>3975531.79</SCHUM_SUG_NECHES><ACHUZ_SUG_NECHES>69.73</ACHUZ_SUG_NECHES><ID_MASLUL_RISHUY>1589</ID_MASLUL_RISHUY></ROW></ROWSET>").encode()
    r = parse(assets, "assets_main", "track")[0]
    check((r["entity_id"], r["period"], r["grp"], r["item_id"], r["pct"]) == (1589, 202608, "חשיפות", 4751, 69.73), "asset row parsed long")
    wide = "<ROWSET><ROW><ID>162</ID><SHM_KRN>מגדל</SHM_KRN><AD_TKUFAT_DIVUACH>202608</AD_TKUFAT_DIVUACH><TZVIRA_NETO>18143.91</TZVIRA_NETO><TSUA_MEMUZAAT_LETKUFA></TSUA_MEMUZAAT_LETKUFA></ROW></ROWSET>".encode()
    w = parse(wide, "general", "fund")[0]
    check(w["data"] == {"ID": 162.0, "SHM_KRN": "מגדל", "AD_TKUFAT_DIVUACH": 202608.0, "TZVIRA_NETO": 18143.91}, "wide row kept, blanks dropped")
    check(fix_name("מור עוקב מדד s1;p 500") == "מור עוקב מדד s&p 500", "S1;P → S&P")


async def test_market_changes():
    """market_changes == the delta function, and a change is only ever measured on funds that
    reported in BOTH months (a missing fund is 'לא דווח החודש', never 'נסגר')."""
    print("market changes (fund_market delta)")
    from sqlalchemy import func
    from app.models.fund_market import FundMarketMonthly as F
    from app.services.agent.tools_market import CATEGORIES, is_open
    from app.services.fund_market.delta import market_delta
    async with async_session() as db:
        a = (await db.execute(select(User).where(User.email == A_EMAIL))).scalar_one()
        ctx = ToolContext(db=db, user=a)
        ps = (await db.execute(select(F.report_period).where(F.source == "pension").distinct()
                               .order_by(F.report_period.desc()).limit(2))).scalars().all()
        if len(ps) < 2:
            print("  skip  fewer than two months of fund data locally")
            return
        tool_out = await registry.get("market_changes").fn(ctx, "pension")
        src, cls, _ = CATEGORIES["pension"]
        direct = await market_delta(db, src, cls, open_only=is_open)
        check(tool_out["summary"] == direct["summary"], "tool summary == delta function")
        ids = lambda p: select(F.fund_id).where(F.source == "pension", F.report_period == p, F.classification.in_(cls))
        both = (await db.execute(select(func.count()).select_from(ids(ps[0]).intersect(ids(ps[1])).subquery()))).scalar_one()
        check(direct["summary"]["funds_compared"] == both, f"compared only funds in both months ({both})")
        text = json.dumps(direct, ensure_ascii=False)
        check("נסגר" not in text.replace("לא 'נסגרה'", ""), "never calls a missing fund closed")
        check(all(r["group_size"] >= 5 for r in direct["rank_climbers"] + direct["rank_fallers"]), "rank moves only in peer groups of 5+")
        await db.rollback()


def test_market_prefetch():
    """'מה השתנה בקרנות ההשתלמות' must prefetch market_changes — "השתל" (השתלה, a policy word) used to
    match השתלמות, so a customer's policies were fetched instead (2026-10-10, 20s+ and a wrong lead)."""
    print("prefetch: market questions")
    from app.services.agent.prefetch import plan
    cases = {
        "מה השתנה בקרנות ההשתלמות לעומת החודש שעבר?": [("market_changes", {"category": "hishtalmut"})],
        "מה השתנה בשוק הפנסיה החודש?": [("market_changes", {"category": "pension"})],
        "לאן נכנס הכי הרבה כסף בגמל להשקעה?": [("market_changes", {"category": "gemel_invest"})],
        "מה התשואה בקרנות השתלמות מניות?": [("compare_hishtalmut", {"track": "מניות"})],
        "מה השתנה במסלקה בקרנות הפנסיה?": [],
        "אילו לקוחות שלי נמצאים במסלולים שירדו בדירוג החודש?": [("customers_in_market_moves", {"direction": "down"})],
        "תשווה בין הפניקס לכלל בגמל": [("compare_gemel", {"company": "הפניקס"}), ("compare_gemel", {"company": "כלל"})],
        "מה השתנה בפילוח של כלל פנסיה כללי מהחודש שעבר?": [("fund_allocation", {"fund": "מה השתנה בפילוח של כלל פנסיה כללי מהחודש שעבר?"})],
        "אילו מסלולי פנסיה הגדילו חשיפה למניות החודש?": [("market_changes", {"category": "pension"})],
        "מה קרן הפנסיה עם דמי הניהול הנמוכים ביותר?": [("compare_pension", {"sort_by": "fee"})],
        "באיזה מסלול רוב הלקוחות שלי?": [("tracks_in_book", {"company": ""})],
        "מה ההבדל בין קרן פנסיה מקיפה לכללית?": [],   # "כללית" is not the company כלל
        "איך הפנסיה של מגדל השתנתה מתחילת השנה?": [("compare_pension", {"company": "מגדל"})],
        "מה השתנה אצל הלקוח 22931885 מהחודש שעבר?": [("get_customer", {"id_number": "22931885"}),
                                                   ("customer_changes", {"id_number": "22931885"})],
        "מה כדאי להציע ללקוח 42251967 לפי התיק שלו?": [("get_customer", {"id_number": "42251967"}),
                                                        ("get_customer_fund_fit", {"id_number": "42251967"})],
        # a customer + fund words → that customer's money vs the market, never a generic market table
        "הלקוח 310203633 — המסלול שלו בפנסיה, איך הוא ביחס לשוק?": [("get_customer", {"id_number": "310203633"}),
                                                                   ("get_customer_fund_fit", {"id_number": "310203633"})],
    }
    for q, want in cases.items():
        check(plan(q) == want, f"{q} → {want}")
    check(any(n == "search_policies" for n, _ in plan("יש כיסוי להשתלת כליה בפוליסה של לקוח 310203633?")),
          "השתלה is still a policy question")
    from app.services.agent import router
    check(router.route("מה כדאי להציע ללקוח 42251967 לפי התיק שלו?") is None, "advice for a customer is not the instant card / task list")
    check(router.route("האם כדאי לנייד את הלקוח 35673813?") is None, "'לנייד?' is not the instant card")
    check(getattr(router.route("מה יש ללקוח 310203633?"), "intent", None) == "customer", "plain 'מה יש ללקוח' stays instant")
    check(getattr(router.route("מה כדאי לי לעשות השבוע?"), "intent", None) == "tasks", "the agent's own task list stays instant")


def test_track_score():
    """Risk level comes from holdings (not the name); index/abroad tracks are their own group; a track
    without 3 years of history is never ranked (it led on one +31% year); ₪ only when the leader is
    really better over 3 years."""
    print("track score (risk by holdings)")
    from types import SimpleNamespace as N
    from app.services.fund_market.track_score import rank_groups, risk_level, verdict
    mk = lambda i, stock, abroad=40, y3=10.0, y5=8.0, sh=1.0, fee=0.5, assets=1000: N(
        fund_id=i, fund_name=f"t{i}", total_assets=assets, stock_exposure=assets * stock / 100,
        foreign_exposure=assets * abroad / 100, fx_exposure=assets * 0.2, avg_yield_3y=y3, avg_yield_5y=y5,
        sharpe=sh, mgmt_fee=fee, classification="x", target_population=None)
    check(risk_level(mk(1, 10))["level"] == 1 and risk_level(mk(2, 60))["level"] == 4 and risk_level(mk(3, 99))["level"] == 5,
          "5 levels from stock exposure")
    check(risk_level(mk(4, 99, abroad=113))["style"] != risk_level(mk(5, 99))["style"], "S&P-type track is its own group")
    ann = mk(6, 30); ann.fund_name = "מיטב פנסיה הלכה למקבלי קצבה"
    check(risk_level(ann)["style"] != risk_level(mk(7, 30))["style"], "annuitant tracks are their own group")
    rows = [mk(10, 99, y3=20), mk(11, 99, y3=22), mk(12, 99, y3=18), mk(13, 99, y3=None), mk(14, 99, y3=15, assets=50)]
    r = rank_groups(rows, {10: 21.0, 11: 23.0, 12: 19.0, 13: 31.0, 14: 16.0}, lambda f: True)
    check(r[13]["rank"] is None and r[14]["rank"] is None, "no 3-year history / under ₪100M → not ranked")
    check(r[11]["rank"] == 1 and r[12]["rank"] == 3, "ranked by the combined score")
    v = verdict(rows[2], r[12], 100_000, 19.0)
    check(v.get("annual_gain_ils") == round(100_000 * (22 - 18) / 100), "₪ = balance × 3-year gap to the leader")


async def test_holdings_in_fit():
    """get_customer_fund_fit carries the holdings view, and best_tracks_by_risk agrees with it."""
    print("holdings view in fund fit")
    async with async_session() as db:
        a = (await db.execute(select(User).where(User.email == A_EMAIL))).scalar_one()
        ctx = ToolContext(db=db, user=a)
        out = await registry.get("best_tracks_by_risk").fn(ctx, "pension", 4)
        if out.get("error"):
            print("  skip  no market data locally")
            return
        ranks = [t["rank"] for t in out["top"]]
        check(ranks == sorted(ranks) and (not ranks or ranks[0] == 1), "best_tracks_by_risk lists #1 first")
        await db.rollback()


async def test_customer_history():
    """Every production upload lands in customer_product_snapshots by month; a second sweep does nothing;
    a customer's timeline and the book's month-over-month changes read from it (per user)."""
    print("customer history (monthly snapshots)")
    from app.services import customer_history as H
    from app.models.customer_snapshot import CustomerProductSnapshot as S
    async with async_session() as db:
        await H.sweep(db)
        again = await H.sweep(db)
        check(again["uploads"] == 0, "sweep is idempotent (nothing re-captured)")
        a = (await db.execute(select(User).where(User.email == A_EMAIL))).scalar_one()
        b = (await db.execute(select(User).where(User.email == B_EMAIL))).scalar_one()
        idn = (await db.execute(select(S.customer_id_number).where(S.user_id == a.id).limit(1))).scalar_one_or_none()
        if not idn:
            print("  skip  no production uploads locally")
            return
        check(len(await H.customer_timeline(db, a.id, idn)) >= 1, "A's customer has a timeline")
        b_ids = set((await db.execute(select(S.customer_id_number).where(S.user_id == b.id))).scalars())
        if idn not in b_ids:
            check(await H.customer_timeline(db, b.id, idn) == [], "B gets no timeline for A's customer")
        bc = await H.book_changes(db, b.id)
        leaked = {n for c in bc.get("companies") or [] for n in c.get("left_names", []) + c.get("new_names", [])
                  if n in {idn} and idn not in b_ids}
        check(not leaked, "B's book changes never show A's customers")


def main():
    test_registry()
    test_policies_routing()
    test_router()
    test_fund_matcher()
    test_calls_routing()
    test_pensyanet_parse()
    test_market_prefetch()
    test_track_score()
    async def _db_tests():   # one event loop — the async engine's pool is bound to it
        await test_privacy_and_parity()
        await test_policies_privacy()
        await test_maslaka_file_companies()
        await test_market_changes()
        await test_holdings_in_fit()
        await test_customer_history()
    asyncio.run(_db_tests())
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
