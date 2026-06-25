"""Local headed recon for the Phoenix (הפניקס) legacy terminal.

Runs the real PhoenixPortal plugin against the live portal in a VISIBLE Chrome
window so you can watch each step and type the OTP yourself — no Twilio /
otp_inbox needed for a local check. After you complete the OTP in the browser,
the script auto-continues into the terminal-recon navigation, which dumps every
frame under data/portal_screenshots/<run_id>_recon_*.

Usage (from backend/, with the venv active):

    source venv/bin/activate
    python scripts/phoenix_recon.py 040336281 'Hruakho!2026'

The window stays open until you press Enter in the terminal, so you can inspect
the live terminal screen alongside the dumped artifacts.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make `app...` importable when run as scripts/phoenix_recon.py from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.companies.phoenix import PhoenixPortal  # noqa: E402
from app.services.portal_automation.runner import SCREENSHOT_ROOT, DOWNLOAD_ROOT  # noqa: E402

RUN_ID = "phoenix_local_recon"


async def main(username: str, password: str) -> None:
    from playwright.async_api import async_playwright

    plugin = PhoenixPortal()
    download_dir = DOWNLOAD_ROOT / RUN_ID
    download_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        # Same real-Chrome setup as the runner, but HEADED so you can watch and
        # enter the OTP. Falls back to bundled chromium if chrome is missing.
        try:
            browser = await pw.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
        except Exception:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="he-IL",
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-mobile": "?0",
            },
        )
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['he-IL', 'he', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """
        )
        page = await context.new_page()

        try:
            print(">> login: filling ID + password and submitting…")
            await plugin.login(page, username, password)

            print(">> OTP screen reached. ENTER THE OTP IN THE BROWSER WINDOW now.")
            print("   Waiting (up to 4 min) for login to complete — the post-login")
            print("   home with the 'my-systems' icon should appear…")
            # Poll for the logged-in home (systems icon) instead of otp_inbox.
            try:
                await page.wait_for_selector(
                    "img[src*='my-systems'], [style*='my-systems']",
                    state="visible",
                    timeout=240000,
                )
                print(">> login complete — systems icon visible.")
            except Exception:
                print("!! systems icon never appeared. Continuing recon anyway so we")
                print("   still capture whatever screen we're on.")

            print(">> running terminal recon navigation (icon → ביטוח חיים → icon)…")
            try:
                await plugin.download_reports(page, download_dir, username=username)
            except RuntimeError as e:
                # Stage A is DESIGNED to raise once it reaches the terminal.
                print(f">> recon raised (expected): {e}")
        finally:
            artifacts = sorted(SCREENSHOT_ROOT.glob(f"{RUN_ID}_recon_*"))
            print("\n==== RECON ARTIFACTS ====")
            for p in artifacts:
                print(f"  {p}")
            print(f"\nKey files to read: {RUN_ID}_recon_summary.txt and")
            print(f"  {RUN_ID}_recon_4_terminal__frame*.txt under {SCREENSHOT_ROOT}")
            # Brief hold for a glance at the terminal, then self-close.
            print("\n>> holding browser open 15s, then closing…")
            await asyncio.sleep(15)
            await context.close()
            await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python scripts/phoenix_recon.py <username> <password>")
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
