"""Manual-drive capture for the Phoenix terminal path.

The terminal is reached through a menu path we haven't pinned down, and it opens
in a NEW TAB (F5 VDI webtop). So instead of guessing selectors, this script:

  1. Does login + OTP (you type the OTP in the visible window).
  2. Then hands the browser to YOU — you click through to the green-screen
     terminal manually.
  3. Meanwhile it records EVERY open tab/page (including popups) every few
     seconds: screenshot + per-frame HTML/text, under
     data/portal_screenshots/phoenix_drive_*.

When you reach the terminal, its page gets captured automatically, so we can
see whether it's an iframe / HTML5 canvas (Ericom PowerTerm) / div-grid and
wire up Stage B.

Usage (from backend/, venv active):

    python scripts/phoenix_capture.py 040336281 'Hruakho!2026'
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.companies.phoenix import PhoenixPortal  # noqa: E402
from app.services.portal_automation.base import BasePortalAutomation  # noqa: E402
from app.services.portal_automation.runner import SCREENSHOT_ROOT  # noqa: E402

RUN_ID = "phoenix_drive"
CAPTURE_MINUTES = 5
TICK_SECONDS = 6


def _slug(url: str) -> str:
    """Short filesystem-safe tag from a URL (host + last path segment)."""
    import re
    u = re.sub(r"^https?://", "", url or "")
    u = u.split("?")[0].strip("/")
    parts = [p for p in u.split("/") if p]
    tag = "_".join(parts[:1] + parts[-1:]) if len(parts) > 1 else (parts[0] if parts else "blank")
    return re.sub(r"[^A-Za-z0-9._-]", "-", tag)[:40] or "blank"


async def main(username: str, password: str) -> None:
    from playwright.async_api import async_playwright

    plugin = PhoenixPortal()
    helper = BasePortalAutomation  # for _dump_all_frames via an instance
    dumper = plugin  # PhoenixPortal is a BasePortalAutomation

    # Clear old artifacts for a clean run.
    for p in SCREENSHOT_ROOT.glob(f"{RUN_ID}_*"):
        try:
            p.unlink()
        except Exception:
            pass

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(
                channel="chrome", headless=False,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
        context = await browser.new_context(
            accept_downloads=True, locale="he-IL",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"', "sec-ch-ua-mobile": "?0",
            },
        )
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )

        new_pages: list = []
        context.on("page", lambda pg: new_pages.append(pg))

        page = await context.new_page()
        try:
            print(">> login: filling ID + password…")
            await plugin.login(page, username, password)
            print(">> OTP screen reached — TYPE THE OTP IN THE WINDOW now.")
            try:
                await page.wait_for_selector(
                    "img[src*='my-systems'], [style*='my-systems']",
                    state="visible", timeout=240000,
                )
                print(">> login complete.")
            except Exception:
                print("!! systems icon not seen; capturing anyway.")

            print("\n" + "=" * 60)
            print(">> NOW NAVIGATE TO THE TERMINAL YOURSELF in the window.")
            print(f">> I'll record every tab every {TICK_SECONDS}s for "
                  f"{CAPTURE_MINUTES} min. Take your time.")
            print("=" * 60 + "\n")

            # Lightweight, change-driven capture: dump each unique page URL at
            # most twice (catches async content) so stable pages aren't re-dumped
            # — keeps the SPA responsive while you click around.
            ticks = int(CAPTURE_MINUTES * 60 / TICK_SECONDS)
            dump_count: dict = {}  # (page_index, url) -> times dumped
            for t in range(ticks):
                pages = list(context.pages)
                for pi, pg in enumerate(pages):
                    if pg.is_closed():
                        continue
                    try:
                        url = pg.url
                    except Exception:
                        continue
                    key = (pi, url)
                    n = dump_count.get(key, 0)
                    if n >= 2:
                        continue  # already captured this page state; stay idle
                    if n == 0:
                        print(f"[t{t:02d}] capturing tab {pi}: {url[:90]}")
                    stem = SCREENSHOT_ROOT / f"{RUN_ID}_p{pi}_{_slug(url)}_{n}.png"
                    try:
                        await dumper._dump_all_frames(pg, stem)
                        dump_count[key] = n + 1
                    except Exception:
                        pass
                await asyncio.sleep(TICK_SECONDS)
        finally:
            arts = sorted(SCREENSHOT_ROOT.glob(f"{RUN_ID}_*.txt"))
            print("\n==== CAPTURE DONE ====")
            print(f"{len(arts)} text dumps under {SCREENSHOT_ROOT}/{RUN_ID}_*")
            try:
                await context.close()
                await browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python scripts/phoenix_capture.py <username> <password>")
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
