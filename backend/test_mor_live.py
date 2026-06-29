"""Standalone live test for the Mor (מור) portal — run it directly, paste the
OTP from your phone into /tmp/mor_otp.txt. Mirrors the runner's browser setup.

Steps (per the live DOM):
  1. fill formcontrolname=licenseId / identity + the k-input phone (placeholder הקלד טלפון)
  2. submit → modal "סיסמה חד-פעמית נשלח לטלפון" with #otpInput (formcontrolname=otpCode, 6)
  3. paste the SMS code → חישוב עמלות → download Excel

Run:  backend/venv/bin/python backend/test_mor_live.py
Then: echo 123456 > /tmp/mor_otp.txt
"""
import os, sys, asyncio, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # backend/
# minimal env so `app` imports (we don't touch the DB here)
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
from app.services.portal_automation.companies.mor import MorPortal

LICENSE_ID = sys.argv[1] if len(sys.argv) > 1 else "040336281|040336281"
PHONE = sys.argv[2] if len(sys.argv) > 2 else "0504302306"
OTP_FILE = "/tmp/mor_otp.txt"
DL = Path("/home/roygi/test/data/portal_downloads/mor_test")
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
        plugin = MorPortal()
        try:
            print("LOGIN…", flush=True)
            await plugin.login(page, LICENSE_ID, PHONE)
            print("OTP_MODAL_OPEN — paste the 6-digit SMS code:  echo 123456 > " + OTP_FILE, flush=True)
            otp = None
            for _ in range(300):  # up to 5 min
                if os.path.exists(OTP_FILE):
                    otp = "".join(ch for ch in open(OTP_FILE).read() if ch.isdigit())
                    if len(otp) >= 6:
                        break
                await asyncio.sleep(1)
            if not otp:
                raise RuntimeError("no OTP pasted within 5 min")
            print("SUBMIT_OTP", otp, flush=True)
            await plugin.submit_otp(page, otp)
            print("DOWNLOAD…", flush=True)
            files = await plugin.download_reports(page, DL, username=LICENSE_ID)
            print("DONE files:", [str(f) for f in files], flush=True)
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
