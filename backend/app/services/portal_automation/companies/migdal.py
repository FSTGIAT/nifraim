"""Migdal (מגדל) agent portal — login, OTP, download commission report.

The Migdal Safes System uses a Google-style email-first login (email page
→ password page → SMS OTP page) and an SPA dashboard whose left-nav often
hides the reports section behind a hamburger toggle.

When a run fails, the runner saves three artifacts under
`data/portal_screenshots/<run_id>.{png,html,txt}`. The `.txt` lists every
visible link/button — use it to extend the candidate-selector lists below
without re-running the live portal.
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

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
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

        # The "Migdal Safes System" landing page is a file-vault — files for
        # the agent are listed by name like `{USERNAME}_FROMMIGDAL_<index>`.
        # Build the precise file selector when we know the username; fall back
        # to a generic _FROMMIGDAL match otherwise.
        user_upper = (username or "").strip().upper()
        file_candidates: list[str] = []
        if user_upper:
            file_candidates.extend([
                f"a:has-text('{user_upper}_FROMMIGDAL')",
                f"button:has-text('{user_upper}_FROMMIGDAL')",
                f"[role='link']:has-text('{user_upper}_FROMMIGDAL')",
            ])
        file_candidates.extend([
            "a:has-text('_FROMMIGDAL')",
            "button:has-text('_FROMMIGDAL')",
            "[role='link']:has-text('_FROMMIGDAL')",
            "a:has-text('FROMMIGDAL')",
        ])

        # Click the file row to open / select it.
        clicked_file = await self._click_first_visible(page, file_candidates, timeout=15000)
        if not clicked_file:
            raise RuntimeError(
                f"לא נמצא קובץ של הסוכן בפורטל {page.url}. "
                f"בדוק את debug HTML ב-{debug_base.with_suffix('.html').name}"
            )
        await page.wait_for_load_state("networkidle", timeout=10000)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "migdal_commission.xlsx"

        # Trigger download via a resilient click. Migdal's Safes UI shows a
        # toolbar after selection; on some accounts the file row click itself
        # already triggers the download (in which case `expect_download` will
        # already have fired before we click anything).
        download_candidates = [
            "button:has-text('Download')",
            "button:has-text('הורד')",
            "button:has-text('הורדה')",
            "a:has-text('Download')",
            "a:has-text('הורד')",
            "[aria-label='Download']",
            "[aria-label='הורדה']",
            "button:has-text('יצוא')",
            "a:has-text('Excel')",
            "a:has-text('XLSX')",
            "[role='button']:has-text('Download')",
        ]

        try:
            async with page.expect_download(timeout=45000) as dl_info:
                # Try the toolbar; if download already fired from the row
                # click, this no-op is harmless.
                await self._click_first_visible(page, download_candidates, timeout=8000)
            download = await dl_info.value
        except Exception as e:
            raise RuntimeError(
                f"לא הצלחנו להוריד קובץ מ-{page.url}. "
                f"בדוק את debug HTML ב-{debug_base.with_suffix('.html').name}: {e}"
            )
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
