"""Standalone live test for the ילין לפידות (Yelin Lapidot) portal.

Drives the YelinPortal plugin directly with the same browser setup as the runner.
You read the SMS OTP off your phone; paste it into /tmp/yelin_otp.txt (or let the
operator inject it). No DB needed — this only validates login → OTP → download.

Run:   backend/venv/bin/python backend/test_yelin_live.py
Watch: the log prints WAITING_FOR_OTP, then:  echo 123456 > /tmp/yelin_otp.txt
Result: downloaded file lands under data/portal_downloads/yelin_test/, and the
        script prints a parse_excel() summary (format / company_source / records).
"""
import os, sys, asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # backend/
_env = {}
for _l in (Path(__file__).resolve().parent.parent / ".env").read_text().splitlines():
    s = _l.strip()
    if s and not s.startswith("#") and "=" in s:
        k, v = s.split("=", 1); _env[k.strip()] = v.strip().strip('"').strip("'")
os.environ.setdefault("DATABASE_URL", _env.get("DATABASE_URL", "postgresql+asyncpg://x/y"))
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://x/y")
os.environ.setdefault("JWT_SECRET", "x")
os.environ.setdefault("PORTAL_CRED_FERNET_KEY", _env.get("PORTAL_CRED_FERNET_KEY", ""))

from playwright.async_api import async_playwright
from app.services.portal_automation.companies.yelin import YelinPortal

ID = sys.argv[1] if len(sys.argv) > 1 else "40336281"      # ת"ז
PHONE = sys.argv[2] if len(sys.argv) > 2 else "504302306"  # פלאפון
OTP_FILE = "/tmp/yelin_otp.txt"
DL = Path("/home/roygi/test/data/portal_downloads/yelin_test")
DL.mkdir(parents=True, exist_ok=True)

INIT = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
Object.defineProperty(navigator,'languages',{get:()=>['he-IL','he','en']});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
"""


async def main():
    if os.path.exists(OTP_FILE):
        os.remove(OTP_FILE)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            channel="chrome", headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}, locale="he-IL",
            accept_downloads=True,
            extra_http_headers={"Accept-Language": "he-IL,he;q=0.9,en;q=0.8"},
        )
        await ctx.add_init_script(INIT)
        page = await ctx.new_page()
        plugin = YelinPortal()
        try:
            print("LOGIN…", flush=True)
            await plugin.login(page, ID, PHONE)
            print("WAITING_FOR_OTP — paste the SMS code:  echo 123456 > " + OTP_FILE, flush=True)
            otp = None
            for _ in range(300):  # up to 5 min
                if os.path.exists(OTP_FILE):
                    otp = "".join(ch for ch in open(OTP_FILE).read() if ch.isdigit())
                    if len(otp) >= 4:
                        break
                await asyncio.sleep(1)
            if not otp:
                raise RuntimeError("no OTP pasted within 5 min")
            print("SUBMIT_OTP", otp, flush=True)
            await plugin.submit_otp(page, otp)
            print("DOWNLOAD…", flush=True)
            files = await plugin.download_reports(page, DL, username=ID)
            print("DONE files:", [str(f) for f in files], flush=True)

            # Verify it parses.
            from app.services.parser_service import parse_excel
            for f in files:
                try:
                    res = parse_excel(open(f, "rb").read(), Path(f).name, None)
                    recs = res.get("records") or res.get("clients") or []
                    print(f"PARSE {Path(f).name}: format={res.get('format')} "
                          f"company={res.get('company_source')} records={len(recs)}", flush=True)
                except Exception as pe:
                    print(f"PARSE {Path(f).name}: FAILED {pe!r}", flush=True)
        except Exception as e:
            print("FAILED:", repr(e), flush=True)
            try:
                await page.screenshot(path=str(DL / "FAIL.png"))
            except Exception:
                pass
            sys.exit(1)
        finally:
            await browser.close()


asyncio.run(main())
