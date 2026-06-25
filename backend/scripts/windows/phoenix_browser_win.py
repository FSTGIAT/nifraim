r"""Phoenix browser automation — WINDOWS side, opens PowerTerm end-to-end, HANDS-FREE OTP.

Runs on Windows Python with Playwright driving real Microsoft Edge (channel
"msedge"), because the native PowerTerm client only launches from a Windows
browser (the WSL/Linux browser just offers a download). Flow:

  URL -> F5 errorcode recovery -> fill ID + password
      -> [OTP pulled hands-free from the backend's phone-forward chain]
      -> my-systems -> ביטוח חיים -> התחבר  -> PowerTerm terminal opens.

The OTP is NOT typed by hand: after the creds are submitted (which triggers the
SMS), this polls the backend `next-otp` endpoint (token-authed) which returns the
forwarded code from `otp_inbox`. The terminal opens in its own window and stays
open; the elevated `phoenix_win_terminal.py export14` then drives option 14.

Run (Windows Python):
    /mnt/c/Python313/python.exe scripts/windows/phoenix_browser_win.py \
        <username> <password> <phone_forward_token> [backend_base]
backend_base defaults to http://127.0.0.1:8000
"""

import sys
import json
import time
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

URL = "https://agent.fnx.co.il/my.policy"


def fetch_otp(base, token, company, after_iso, timeout_s=300):
    """Poll the backend for a hands-free, company-routed OTP (consumed on return)."""
    deadline = time.time() + timeout_s
    qs = urllib.parse.urlencode({"company": company, "after": after_iso})
    url = f"{base}/api/portal-automation/phone-forward/{token}/next-otp?{qs}"
    print(f">> waiting for forwarded OTP (poll {url}) …")
    while time.time() < deadline:
        try:
            data = json.loads(urllib.request.urlopen(url, timeout=8).read())
            if data.get("otp"):
                print(f">> got OTP {data['otp']} (company={data.get('company')})")
                return data["otp"]
        except Exception:
            pass
        time.sleep(2)
    return None


async def main(username, password, token, base):
    from playwright.async_api import async_playwright
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print(">> [start] launching Edge…", flush=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge", headless=False,
                                            args=["--start-maximized"])
        print(">> [edge launched] creating context…", flush=True)
        ctx = await browser.new_context(no_viewport=True, locale="he-IL")
        page = await ctx.new_page()

        print(">> opening portal…", flush=True)
        await page.goto(URL, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(2000)

        for _ in range(4):
            if "errorcode" not in page.url and "logout" not in page.url:
                break
            for sel in ("a:has-text('התחבר מחדש')", "a:has-text('חזרה למסך הכניסה')",
                        "a:has-text('לחץ כאן')"):
                try:
                    await page.click(sel, timeout=4000); break
                except Exception:
                    continue
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

        print(">> filling ID + password…")
        await page.wait_for_selector("input[name='username']", state="visible", timeout=15000)
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        # Capture the timestamp BEFORE submit — submit triggers the SMS, so the
        # OTP row will have received_at >= this. BACKDATE by 120s to absorb clock
        # skew between this machine and the (Railway) server: the new app forwards
        # so fast the OTP can land a fraction of a second "before" our cutoff on a
        # differently-skewed clock and get wrongly excluded. 120s is safe because
        # we already clear stale OTPs before each run.
        after_iso = (datetime.utcnow() - timedelta(seconds=15)).isoformat()
        for sel in ("input[type='submit']", "button:has-text('כניסה')", "button:has-text('המשך')"):
            try:
                await page.click(sel, timeout=2500); break
            except Exception:
                continue

        await page.wait_for_selector("input[placeholder='קוד זיהוי'], input#input_2", timeout=20000)

        # ── hands-free OTP ──
        otp = await asyncio.get_event_loop().run_in_executor(
            None, fetch_otp, base, token, "phoenix", after_iso, 300
        )
        if not otp:
            print("!! no OTP forwarded within 180s — is the SMS Forwarder + tunnel up?")
            await ctx.close(); await browser.close()
            raise SystemExit(3)
        await page.fill("input[placeholder='קוד זיהוי'], input#input_2", str(otp))
        for sel in ("input[type='submit']", "button:has-text('כניסה')", "button:has-text('המשך')"):
            try:
                await page.click(sel, timeout=2500); break
            except Exception:
                continue

        try:
            await page.wait_for_selector("img[src*='my-systems'], [style*='my-systems']",
                                         state="visible", timeout=120000)
            print(">> logged in.")
        except Exception:
            print("!! systems icon not seen — continuing anyway.")

        print(">> navigating my-systems → ביטוח חיים → התחבר…")
        await page.wait_for_timeout(1500)
        # Post-login Angular overlays (welcome/notification dialogs) drop a
        # `cdk-overlay-backdrop` that intercepts clicks on the my-systems icon.
        # Dismiss any open overlay (close button → Escape → click backdrop).
        for _ in range(5):
            backdrop = page.locator(".cdk-overlay-backdrop-showing")
            if await backdrop.count() == 0:
                break
            print(">> dismissing post-login overlay…")
            closed = False
            for sel in ("button[aria-label*='סגור']", "button.close",
                        "[mat-dialog-close]", "button:has-text('סגור')",
                        "button:has-text('אישור')", "button:has-text('הבנתי')"):
                loc = page.locator(sel)
                try:
                    if await loc.count() and await loc.first.is_visible():
                        await loc.first.click(timeout=2000); closed = True; break
                except Exception:
                    continue
            if not closed:
                try:
                    await page.keyboard.press("Escape"); await page.wait_for_timeout(300)
                    await backdrop.first.click(timeout=2000, force=True)
                except Exception:
                    pass
            await page.wait_for_timeout(800)
        await page.locator("img[src*='my-systems.svg']").first.click()
        await page.wait_for_timeout(1500)
        life = page.locator("button[role='menuitem']:has-text('ביטוח חיים')").first
        await life.hover(); await page.wait_for_timeout(600); await life.click()
        await page.wait_for_timeout(1200)
        await page.locator(
            "button.btn-primary-sm:has-text('התחבר'), "
            "button:has-text('התחבר'):not(:has-text('מחדש'))"
        ).first.click()
        print(">> clicked התחבר — PowerTerm terminal should now open (own window).")

        # The terminal is a separate native window and PERSISTS after the browser
        # closes. Keep the browser briefly so the client finishes launching.
        await page.wait_for_timeout(20000)
        await ctx.close(); await browser.close()
        print(">> browser closed; terminal stays open for the export driver.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python phoenix_browser_win.py <username> <password> <token> [backend_base]")
        raise SystemExit(2)
    base = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8000"
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], base))
