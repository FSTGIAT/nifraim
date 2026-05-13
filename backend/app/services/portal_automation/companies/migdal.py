"""Migdal (מגדל) agent portal — login, OTP, download commission report.

NOTE: Selectors below are first-pass placeholders. Migdal's agents area
ships behind a multi-step login that we have not yet recorded. Re-record
with `playwright codegen --target python-async <portal-url>` against the
live portal once we have agent credentials, and update the selectors here.
On every run a screenshot is saved to
`backend/data/portal_screenshots/<run_id>.png` so a failed step is
diagnosable without re-running.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://mfte.migdal.co.il/#/"


class MigdalPortal(BasePortalAutomation):
    portal_kind = "migdal"
    company_label = "מגדל"

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Migdal Safes System uses a 2-step email-first login (Google-style):
        # email page → Next → password page → Sign in → OTP page.
        await page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)

        # Step 1: username
        await self._wait_visible(page, "input#email")
        await page.fill("input#email", username)
        # The "Next" / "המשך" label depends on UI language; match either.
        await page.click("button:has-text('Next'), button:has-text('המשך')")

        # Step 2: password (note: input type=text + custom show/hide, not type=password)
        await self._wait_visible(page, "input#password", timeout=15000)
        await page.fill("input#password", password)
        await page.click("button:has-text('Sign in'), button:has-text('כניסה')")

        # Step 3: OTP page — input#otp, "Sign in" button (verified against live portal).
        await self._wait_visible(page, "input#otp", timeout=20000)

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill("input#otp", otp)
        await page.click("button:has-text('Sign in'), button:has-text('כניסה')")
        # Migdal Safes System is an SPA — `networkidle` settles before the
        # hash route flips off /tfa, so dumping/clicking here would still
        # see the OTP page DOM. Wait for the URL to actually leave /tfa.
        try:
            await page.wait_for_url(
                lambda u: "/tfa" not in u, timeout=20000
            )
        except Exception:
            # URL never changed — let download_reports dump current state
            # for diagnosis instead of hanging here.
            pass
        await page.wait_for_load_state("networkidle", timeout=10000)

    async def download_reports(self, page: "Page", download_dir: Path) -> list[Path]:
        # Migdal commission reports are typically not password-protected; leave None
        # so msoffcrypto isn't tried unnecessarily.
        self.report_password = None

        # Always dump the post-OTP landing page next to the run's screenshot so
        # we have evidence the next time selectors drift. `download_dir.name`
        # is the run_id (see runner.DOWNLOAD_ROOT / str(run.id)), so this
        # produces a unique debug stem per run.
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        debug_base = SCREENSHOT_ROOT / f"{run_id}_post_otp.png"
        await self._safe_screenshot(page, debug_base)
        await self._dump_page_state(page, debug_base)

        nav_target = await self._click_first_visible(
            page,
            [
                # Hebrew labels — common Migdal navigation
                "a:has-text('דוחות נפרעים')",
                "a:has-text('דוחות עמלות')",
                "a:has-text('עמלות ונפרעים')",
                "a:has-text('דוחות')",
                "a:has-text('עמלות')",
                "a:has-text('נפרעים')",
                # Buttons / styled menu items
                "button:has-text('דוחות')",
                "button:has-text('עמלות')",
                "[role='link']:has-text('דוחות')",
                "[role='button']:has-text('דוחות')",
                # English fallbacks
                "a:has-text('Reports')",
                "a:has-text('Commissions')",
            ],
            timeout=20000,
        )
        if not nav_target:
            raise RuntimeError(
                f"לא נמצא תפריט דוחות/עמלות בעמוד {page.url}. "
                f"בדוק את debug HTML ב-{debug_base.with_suffix('.html').name}"
            )
        await page.wait_for_load_state("networkidle", timeout=15000)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "migdal_commission.xlsx"

        async with page.expect_download() as dl_info:
            await page.click("button:has-text('הורד'), a:has-text('Excel'), a:has-text('יצוא')")
        download = await dl_info.value
        await download.save_as(str(target))
        return [target]

    async def change_contact_phone(self, page: "Page", new_phone: str) -> None:
        # Selectors are first-pass placeholders. Re-record with playwright codegen.
        await page.click("a:has-text('פרופיל'), a:has-text('פרטים אישיים'), a:has-text('הגדרות')")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await self._wait_visible(page, "input[name='phone'], input[name='mobile'], input[name='cellphone']")
        await page.fill("input[name='phone'], input[name='mobile'], input[name='cellphone']", new_phone)
        await page.click("button:has-text('שמור'), button:has-text('עדכן')")
        # Migdal verifies the change by texting the OLD phone — wait for the OTP entry to appear.
        await self._wait_visible(
            page,
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code']",
            timeout=20000,
        )

    async def confirm_contact_phone_change(self, page: "Page", otp: str) -> None:
        await page.fill(
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code']",
            otp,
        )
        await page.click("button[type='submit'], button:has-text('אישור'), button:has-text('המשך')")
        await page.wait_for_load_state("networkidle", timeout=15000)
