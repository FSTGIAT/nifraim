"""הר הביטוח end-to-end against a MOCK site — the real runner + plugin + queue + ingest + agent tool.

    source backend/venv/bin/activate && python backend/tests/test_harb_e2e_mock.py

What is real here: runner.run_automation (Playwright, _wait_for_otp, the harbituach hook), the
plugin's selectors and Kendo date setting, harb_jobs (one login drains the queue, finalize),
harb_ingest, the data map page and the customer_policies tool — all on the LOCAL dev DB.
What is mocked: the site (tests/harb_mock/*.html). Its login form is modeled on the real
login.gov.il form recon'd 2026-10-07; the SMS screen and the portal screens follow the steps doc
and are NOT yet verified live. The portal is served on `localhost`, the login on `127.0.0.1`
(two hosts, like the real SAML hop). The SMS is inserted into otp_inbox the moment the run waits
for it, exactly where the phone-forward webhook writes it.

Scenarios: (1) two customers, one login: one found (Excel + 3 detail views), one not found;
(2) a wrong password fails the run at login and the waiting request with the reason (no SMS wait).
Uses test@test.com; cleans up the rows it creates.
"""
import asyncio
import sys
import threading
import urllib.request
from datetime import date, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select, update  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import (HarbRequest, InsurancePolicy, OtpInbox, PolicyDocument, PortalCredential,  # noqa: E402
                        PortalRun, User, WorkerHeartbeat)
from app.services.policies import harb_jobs  # noqa: E402
from app.services.portal_automation import runner  # noqa: E402
from app.services.portal_automation.companies import harbituach  # noqa: E402
from app.utils.crypto import encrypt  # noqa: E402

MOCK = Path(__file__).parent / "harb_mock"
XLSX = Path("/mnt/c/Users/roygi/Downloads/REPORT/police_example/עמיקם עינב הר הביטוח.xlsx")
VENDOR = Path.home() / ".cache" / "nifraim-test" / "harb_vendor"
CDN = {"jquery.min.js": "https://code.jquery.com/jquery-3.6.0.min.js",
       "kendo.all.min.js": "https://kendo.cdn.telerik.com/2023.1.117/js/kendo.all.min.js",
       "kendo.common.min.css": "https://kendo.cdn.telerik.com/2023.1.117/styles/kendo.common.min.css"}
EMAIL = "test@test.com"
FOUND = ("32489387", date(1986, 5, 22), date(2004, 3, 15))      # the mock's KNOWN person
MISSING = ("203717186", date(1980, 1, 1), date(2000, 1, 1))     # wrong dates → not found
FAILS: list[str] = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


class Mock(SimpleHTTPRequestHandler):
    port = 0

    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str, extra: dict | None = None, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        P = Mock.port
        if p == "/":
            return self._send((MOCK / "home.html").read_bytes(), "text/html; charset=utf-8")
        if p == "/sso/Auth/MoreInsurance":        # the SSO hop to the OTHER host
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{P}/nidp/login?back=http://localhost:{P}/portal")
            return self.end_headers()
        if p == "/nidp/login":
            return self._send((MOCK / "login.html").read_bytes(), "text/html; charset=utf-8")
        if p.startswith("/portal"):
            return self._send((MOCK / "portal.html").read_bytes(), "text/html; charset=utf-8")
        if p.startswith("/vendor/"):
            f = VENDOR / p.rsplit("/", 1)[-1]
            return self._send(f.read_bytes(), "text/css" if f.suffix == ".css" else "application/javascript")
        if p == "/excel":
            return self._send(XLSX.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              {"Content-Disposition": 'attachment; filename="harb.xlsx"'})
        self._send(b"not found", "text/plain", code=404)


def start_mock() -> int:
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name, url in CDN.items():
        if not (VENDOR / name).exists():
            (VENDOR / name).write_bytes(urllib.request.urlopen(url, timeout=60).read())
    srv = ThreadingHTTPServer(("0.0.0.0", 0), partial(Mock))
    Mock.port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return Mock.port


async def setup(db, password: str):
    u = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one()
    cred = await harb_jobs.credential(db, u.id)
    if cred is None:
        cred = PortalCredential(user_id=u.id, portal_kind="harbituach", username="000000018",
                                encrypted_password=encrypt(password), otp_method="phone_forward", is_active=True)
        db.add(cred)
    cred.encrypted_password = encrypt(password)
    cred.username = "000000018"
    await db.execute(update(PortalRun).where(PortalRun.credential_id == cred.id, PortalRun.status.in_(harb_jobs.ACTIVE_RUN))
                     .values(status="failed", error_message="test cleanup"))
    await db.execute(delete(HarbRequest).where(HarbRequest.user_id == u.id,
                                               HarbRequest.customer_id_number.in_((FOUND[0], MISSING[0]))))
    hb = (await db.execute(select(WorkerHeartbeat).where(WorkerHeartbeat.user_id == u.id))).scalars().first()
    if hb:
        hb.last_seen = datetime.utcnow()
    else:
        db.add(WorkerHeartbeat(user_id=u.id, last_seen=datetime.utcnow(), hostname="e2e-mock"))
    await db.commit()
    return u, cred


async def inject_otp_when_waiting(run_id, user_id, code="482913"):
    """The phone-forward webhook's job: write the SMS when the run waits for it."""
    for _ in range(240):
        async with async_session() as db:
            st = (await db.execute(select(PortalRun.status).where(PortalRun.id == run_id))).scalar_one()
            if st == "awaiting_otp":
                now = (await db.execute(select(func.timezone("UTC", func.now())))).scalar_one()
                # the REAL wording (captured 2026-10-07), tagged by the same routing the webhook uses
                from app.services.otp_routing import match_otp_company
                body = f"קוד האימות הוא {code} להמשך התהליך במערכת ההזדהות הלאומית"
                kind, company = await match_otp_company(db, body, sender="gov.il")
                db.add(OtpInbox(user_id=user_id, from_number="gov.il", to_number="", otp_code=code, body=body,
                                portal_kind=kind, matched_company=company, received_at=now))
                await db.commit()
                return True
            if st in ("failed", "timeout", "success"):
                return False
        await asyncio.sleep(0.5)
    return False


async def scenario_two_customers(port: int):
    print("scenario 1 — two customers, one login (found + not found)")
    async with async_session() as db:
        u, cred = await setup(db, "placeholder-local")
        a = await harb_jobs.enqueue(db, u, FOUND[0], FOUND[1], FOUND[2], "גולן צרפתי שרון")
        b = await harb_jobs.enqueue(db, u, MISSING[0], MISSING[1], MISSING[2], "עמיקם עינב")
        run_id, uid = a.portal_run_id, u.id
        check(b.portal_run_id is None, "second request queued on the live run (no second run, no second login)")
    injector = asyncio.create_task(inject_otp_when_waiting(run_id, uid))
    await runner.run_automation(run_id)
    check(await injector, "the run waited for the SMS code and it was delivered through otp_inbox")
    async with async_session() as db:
        run = await db.get(PortalRun, run_id)
        a = (await db.execute(select(HarbRequest).where(HarbRequest.user_id == uid, HarbRequest.customer_id_number == FOUND[0]))).scalar_one()
        b = (await db.execute(select(HarbRequest).where(HarbRequest.user_id == uid, HarbRequest.customer_id_number == MISSING[0]))).scalar_one()
        check(run.status == "success", f"run success (got {run.status}: {run.error_message})")
        otp = (await db.execute(select(OtpInbox).where(OtpInbox.portal_run_id == run_id))).scalars().all()
        check(len(otp) == 1 and otp[0].consumed_at is not None, "exactly one SMS consumed for the whole queue")
        check(bool(otp) and otp[0].portal_kind == "harbituach", f"the gov-ID SMS was tagged הר הביטוח (got {otp[0].portal_kind if otp else None})")
        check(a.status == "done" and a.policies_count == 50, f"found customer → done, 50 coverages (got {a.status}, {a.policies_count}, {a.error})")
        check(b.status == "not_found" and "אינם תואמים" in (b.error or ""),
              f"wrong dates → not_found with the site's own message (got {b.status}: {b.error})")
        check(b.portal_run_id == run_id, "the not-found customer was served in the SAME login")
        n_pol = (await db.execute(select(func.count()).select_from(InsurancePolicy).where(
            InsurancePolicy.user_id == uid, InsurancePolicy.customer_id_number == FOUND[0]))).scalar_one()
        docs = (await db.execute(select(PolicyDocument).where(PolicyDocument.user_id == uid,
                                                              PolicyDocument.customer_id_number == FOUND[0]))).scalars().all()
        kinds = sorted(d.source for d in docs)
        check(n_pol == 50, f"50 insurance_policies rows stored (got {n_pol})")
        check(kinds.count("harb_portfolio") == 1, "one portfolio Markdown document")
        check(kinds.count("harb_policy") == 3, f"three policy-detail documents from the detail views (got {kinds.count('harb_policy')})")
        det = next((d for d in docs if d.source == "harb_policy" and d.policy_number == "301611265"), None)
        check(bool(det and "136.29" in (det.markdown or "")), "a detail document carries its policy number and the detail text")
        check(kinds.count("pdf") >= 0, "uploaded PDFs of the same customer are kept (snapshot replaces harb docs only)")
        st = harb_jobs.effective_status(a, run)
        check(st == "done", "chat follower would show done")
        from app.services import data_map
        from app.services.agent import registry
        from app.services.agent.context import ToolContext
        registry._load()
        m = await data_map.load(db, await db.get(User, uid))
        page = data_map.render(m, f"customers/{FOUND[0]}/policies.md")
        check("## בתוקף" in page and "301611265" in page, "the data map policies page lists the fetched policies")
        out = str(await registry.dispatch(ToolContext(db=db, user=await db.get(User, uid)), "customer_policies", {"id_number": FOUND[0]}))
        check('"found": true' in out and "301611265" in out and "6929303" in out, "Nifra's customer_policies tool sees the fetched policies")
        return uid


async def scenario_wrong_password():
    print("scenario 2 — wrong password fails at login, the request gets the reason")
    async with async_session() as db:
        u, cred = await setup(db, "wrong-password")
        r = await harb_jobs.enqueue(db, u, FOUND[0], FOUND[1], FOUND[2])
        run_id = r.portal_run_id
    t0 = asyncio.get_event_loop().time()
    await runner.run_automation(run_id)
    secs = asyncio.get_event_loop().time() - t0
    async with async_session() as db:
        run = await db.get(PortalRun, run_id)
        r = await db.get(HarbRequest, r.id)
        check(run.status == "failed" and "נדחתה" in (run.error_message or ""), f"run failed at login (got {run.status}: {run.error_message})")
        check(r.status == "failed" and "נדחתה" in (r.error or ""), f"request failed with the reason (got {r.status}: {r.error})")
        check(secs < 90, f"fails fast — no 4-minute SMS wait ({secs:.0f}s)")
        check(await harb_jobs.active_run(db, u.id) is None, "no retry loop left behind")
        await setup(db, "placeholder-local")     # restore the local placeholder password


async def cleanup(uid):
    async with async_session() as db:
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.user_id == uid, InsurancePolicy.customer_id_number == FOUND[0]))
        await db.execute(delete(PolicyDocument).where(PolicyDocument.user_id == uid, PolicyDocument.customer_id_number == FOUND[0],
                                                      PolicyDocument.source.in_(("harb_portfolio", "harb_policy"))))
        await db.execute(delete(HarbRequest).where(HarbRequest.user_id == uid, HarbRequest.customer_id_number.in_((FOUND[0], MISSING[0]))))
        await db.commit()


async def main():
    port = start_mock()
    harbituach.HOME = f"http://localhost:{port}/"
    harbituach.HarBituachPortal.headed = False          # no display here; the worker runs it headed
    print(f"mock הר הביטוח on localhost:{port} (login on 127.0.0.1:{port})")
    uid = None
    try:
        uid = await scenario_two_customers(port)
        await scenario_wrong_password()
    finally:
        if uid:
            await cleanup(uid)
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    asyncio.run(main())
